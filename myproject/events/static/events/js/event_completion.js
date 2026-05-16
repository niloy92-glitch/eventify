(function () {
  class EventCompletionModalPolyfill {
    constructor() {
      this.modal = document.getElementById('event-completion-modal');
      this.form = document.getElementById('event-completion-form');
      this.eventIdInput = document.getElementById('event-id');
      this.servicesList = document.getElementById('services-rating-list');
      this.template = document.getElementById('service-rating-template');

      if (!this.modal || !this.form || !this.template) return;

      this.setupListeners();
    }

    setupListeners() {
      this.form.addEventListener('submit', (e) => this.handleSubmit(e));

      // Close buttons handled by modal_helper; ensure form is reset when hidden
      this.modal.addEventListener('animationend', () => {
        // noop
      });
    }

    open(eventId, title, date, services) {
      if (!this.modal) return;
      this.eventId = Number(eventId);
      this.eventIdInput.value = String(this.eventId);
      const titleEl = document.getElementById('completion-event-title');
      const dateEl = document.getElementById('completion-event-date');
      if (titleEl) titleEl.textContent = title || '';
      if (dateEl) dateEl.textContent = date ? `Event Date: ${date}` : '';

      this.populateServices(services || []);

      // delegate to modal_helper if present
      if (typeof window.openModal === 'function') {
        try { window.openModal(this.modal); } catch (e) { this.modal.removeAttribute('hidden'); }
      } else {
        this.modal.removeAttribute('hidden');
      }
    }

    populateServices(services) {
      if (!this.servicesList) return;
      this.servicesList.innerHTML = '';
      if (!Array.isArray(services) || services.length === 0) {
        this.servicesList.innerHTML = '<p class="muted">No services booked for this event.</p>';
        return;
      }

      services.forEach((svc) => {
        const clone = this.template.content.cloneNode(true);
        const fieldset = clone.querySelector('.star-rating');
        if (fieldset) fieldset.dataset.serviceId = String(svc.id);
        const name = clone.querySelector('.service-rating-name');
        if (name) name.textContent = svc.name || 'Service';
        const type = clone.querySelector('.service-rating-type');
        if (type) type.textContent = svc.type || '';

        // wire star change display
        clone.querySelectorAll('input[type=radio]').forEach((input) => {
          input.name = `rating-${svc.id}`;
          input.addEventListener('change', function () {
            const display = this.closest('.event-rating-card').querySelector('.star-display');
            if (display) display.textContent = `${this.value} star${this.value !== '1' ? 's' : ''} selected`;
          });
        });

        this.servicesList.appendChild(clone);
      });
    }

    collectRatings() {
      const out = {};
      this.servicesList.querySelectorAll('.star-rating').forEach((fs) => {
        const sid = fs.dataset.serviceId;
        const checked = fs.querySelector('input[type=radio]:checked');
        if (sid && checked) out[sid] = Number(checked.value);
      });
      return out;
    }

    async handleSubmit(e) {
      e.preventDefault();
      const eventId = this.eventId || Number(this.eventIdInput.value);
      if (!eventId) {
        alert('Missing event id');
        return;
      }

      const ratings = this.collectRatings();

      try {
        const resp = await fetch(`/events/${eventId}/complete/`, {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '',
          },
          body: JSON.stringify({}),
        });

        if (!resp.ok) throw new Error('Failed to complete event');

        // submit ratings sequentially
        for (const [serviceId, stars] of Object.entries(ratings)) {
          await fetch(`/services/${serviceId}/rate/`, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
              'X-Requested-With': 'XMLHttpRequest',
              'Content-Type': 'application/json',
              'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '',
            },
            body: JSON.stringify({ event_id: eventId, stars: stars }),
          });
        }

        // close modal and reload
        if (typeof window.closeModal === 'function') window.closeModal('event-completion-modal');
        else document.getElementById('event-completion-modal')?.setAttribute('hidden', '');

        if (window.EventifyToast) {
          EventifyToast.show('Event completed — ratings submitted', 'success');
        }
        setTimeout(() => window.location.reload(), 900);
      } catch (err) {
        console.error(err);
        alert('Failed to complete event. See console for details.');
      }
    }
  }

  // instantiate and expose
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      window.eventCompletionModal = new EventCompletionModalPolyfill();
    });
  } else {
    window.eventCompletionModal = new EventCompletionModalPolyfill();
  }

})();
/**
 * Event Completion Modal - Handles event completion and service rating
 */

class EventCompletionModal {
  constructor() {
    this.modal = document.getElementById('event-completion-modal');
    this.form = document.getElementById('event-completion-form');
    this.eventIdInput = document.getElementById('event-id');
    this.closeBtn = this.modal?.querySelector('.modal-close');
    this.closeBtnFooter = this.modal?.querySelector('.modal-close-btn');
    this.overlay = this.modal?.querySelector('.modal-overlay');
    
    if (this.modal) {
      this.setupEventListeners();
    }
  }

  setupEventListeners() {
    if (!this.modal) return;
    
    // Close button handlers
    this.closeBtn?.addEventListener('click', (e) => {
      e.preventDefault();
      this.close();
    });
    this.closeBtnFooter?.addEventListener('click', (e) => {
      e.preventDefault();
      this.close();
    });
    
    // Close on overlay click
    this.overlay?.addEventListener('click', (e) => {
      e.preventDefault();
      this.close();
    });

    // Close modal when clicking on the modal background
    this.modal.addEventListener('click', (e) => {
      if (e.target === this.modal) {
        this.close();
      }
    });
    
    // Form submission
    this.form?.addEventListener('submit', (e) => this.handleSubmit(e));
    
    // Close on Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !this.modal.hasAttribute('hidden')) {
        e.preventDefault();
        this.close();
      }
    });
  }

  open(eventId, eventTitle, eventDate, services = []) {
    if (!this.modal || !this.eventIdInput) {
      console.error('Event completion modal not properly initialized');
      return;
    }
    
    this.eventIdInput.value = eventId;
    const titleEl = document.getElementById('completion-event-title');
    const dateEl = document.getElementById('completion-event-date');
    
    if (titleEl) titleEl.textContent = eventTitle;
    if (dateEl) dateEl.textContent = `Event Date: ${eventDate}`;
    
    this.populateServices(services);
    
    // Show modal
    this.modal.removeAttribute('hidden');
    this.modal.classList.add('open');
    this.modal.setAttribute('aria-hidden', 'false');
    this.modal.removeAttribute('inert');
  }

  close() {
    if (!this.modal) return;
    
    this.modal.setAttribute('hidden', '');
    this.modal.classList.remove('open');
    this.modal.setAttribute('aria-hidden', 'true');
    this.modal.setAttribute('inert', 'inert');
    
    if (this.form) {
      this.form.reset();
    }
  }

  populateServices(services) {
    const servicesList = document.getElementById('services-rating-list');
    const template = document.getElementById('service-rating-template');
    
    servicesList.innerHTML = '';
    
    if (services.length === 0) {
      servicesList.innerHTML = '<p class="muted">No services booked for this event.</p>';
      return;
    }
    
    services.forEach((service, index) => {
      const clone = template.content.cloneNode(true);
      
      // Update IDs to be unique
      const radioInputs = clone.querySelectorAll('input[type="radio"]');
      const labels = clone.querySelectorAll('.star-label');
      const fieldset = clone.querySelector('.star-rating');
      
      radioInputs.forEach(input => {
        const originalId = input.id;
        input.id = `${originalId}-${service.id}`;
        input.name = `rating-${service.id}`;
      });
      
      labels.forEach((label, idx) => {
        label.setAttribute('for', `star-${5-idx}-${service.id}`);
      });
      
      fieldset.dataset.serviceId = service.id;
      
      // Update service info
      clone.querySelector('.service-rating-name').textContent = service.name;
      clone.querySelector('.service-rating-type').textContent = service.type;
      
      // Setup star rating display
      const starInputs = clone.querySelectorAll('input[type="radio"]');
      const starDisplay = clone.querySelector('.star-display');
      
      starInputs.forEach(input => {
        input.addEventListener('change', () => {
          starDisplay.textContent = `${input.value} star${input.value !== '1' ? 's' : ''} selected`;
        });
      });
      
      servicesList.appendChild(clone);
    });
  }

  getRatings() {
    const ratings = {};
    const fieldsets = this.modal.querySelectorAll('.star-rating');
    
    fieldsets.forEach(fieldset => {
      const serviceId = fieldset.dataset.serviceId;
      const checked = fieldset.querySelector('input[type="radio"]:checked');
      
      if (checked) {
        ratings[serviceId] = parseInt(checked.value);
      }
    });
    
    return ratings;
  }

  async handleSubmit(e) {
    e.preventDefault();
    
    const eventId = this.eventIdInput.value;
    const ratings = this.getRatings();
    
    try {
      // Complete the event
      const completeResponse = await fetch(`/events/${eventId}/complete/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCsrfToken(),
        },
        body: JSON.stringify({}),
      });
      
      if (!completeResponse.ok) {
        throw new Error('Failed to complete event');
      }
      
      // Submit ratings
      for (const [serviceId, stars] of Object.entries(ratings)) {
        await fetch(`/services/${serviceId}/rate/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.getCsrfToken(),
          },
          body: JSON.stringify({
            event_id: eventId,
            stars: stars,
          }),
        });
      }
      
      this.close();
      
      // Show success message
      this.showSuccessMessage('Event completed successfully!');
      
      // Reload the page after a short delay
      setTimeout(() => {
        window.location.reload();
      }, 2000);
      
    } catch (error) {
      console.error('Error:', error);
      alert('Failed to complete event. Please try again.');
    }
  }

  getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
           document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1] || '';
  }

  showSuccessMessage(message) {
    // Use existing toast system if available, otherwise show alert
    if (typeof showToast === 'function') {
      showToast(message, 'success');
    } else {
      console.log(message);
    }
  }
}

function openRequestedEventCompletionModal() {
  const request = window.__openEventCompletionModal;
  if (!request) {
    return false;
  }
  
  if (!window.eventCompletionModal) {
    console.warn('Event completion modal not initialized');
    return false;
  }

  console.log('Opening event completion modal with:', request);
  window.eventCompletionModal.open(
    request.eventId,
    request.eventTitle,
    request.eventDate,
    request.services || []
  );
  window.__openEventCompletionModal = null;
  return true;
}

// Initialize modal on page load
let eventCompletionModal;
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    eventCompletionModal = new EventCompletionModal();
    window.eventCompletionModal = eventCompletionModal;
    openRequestedEventCompletionModal();
  });
} else {
  eventCompletionModal = new EventCompletionModal();
  window.eventCompletionModal = eventCompletionModal;
  openRequestedEventCompletionModal();
}

// Export for use in other scripts
if (typeof window !== 'undefined') {
  window.EventCompletionModal = EventCompletionModal;
}
