document.addEventListener('DOMContentLoaded', function () {
  const iconMap = {
    catering: '🍽',
    photography: '📷',
    decoration: '🎀',
    music: '🎵',
    venue: '🏛',
    other: '★',
  };
  const monthNames = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December',
  ];

  function readJsonScript(id) {
    const node = document.getElementById(id);
    if (!node) return [];
    try {
      return JSON.parse(node.textContent || '[]');
    } catch (error) {
      return [];
    }
  }

  const servicesData = readJsonScript('services-data');
  const upcomingEvents = readJsonScript('client-events-data');
  const serviceMap = new Map(servicesData.map(function (item) { return [String(item.id), item]; }));
  const upcomingEventMap = new Map(upcomingEvents.map(function (item) { return [String(item.id), item]; }));

  const modal = document.getElementById('service-detail-modal');
  const icon = document.getElementById('service-detail-icon');
  const titleEl = document.getElementById('service-detail-title');
  const companyEl = document.getElementById('service-detail-company');
  const typeEl = document.getElementById('service-detail-type');
  const descEl = document.getElementById('service-detail-desc');
  const calendarLabel = document.getElementById('service-calendar-label');
  const monthSelect = document.getElementById('service-calendar-month');
  const yearSelect = document.getElementById('service-calendar-year');
  const grid = document.getElementById('service-calendar-grid');
  const eventSelect = document.getElementById('service-event-select');
  const bookingForm = document.getElementById('service-booking-form');
  const bookingSubmit = document.getElementById('service-booking-submit');
  const bookingStatus = document.getElementById('service-booking-status');
  const bookingServiceId = document.getElementById('service-booking-service-id');
  const bookingEventId = document.getElementById('service-booking-event-id');

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const calendarState = { year: today.getFullYear(), month: today.getMonth() };
  const storageKey = 'eventify.serviceDetail.state';

  let selectedService = null;
  let selectedEventId = '';
  let availabilitySet = new Set();

  function persistState() {
    if (!selectedService) return;
    localStorage.setItem(storageKey, JSON.stringify({
      serviceId: String(selectedService.id),
      eventId: String(selectedEventId || ''),
      year: calendarState.year,
      month: calendarState.month,
    }));
  }

  function loadPersistedState(serviceId) {
    try {
      const payload = JSON.parse(localStorage.getItem(storageKey) || 'null');
      if (!payload || String(payload.serviceId) !== String(serviceId)) return null;
      return payload;
    } catch (error) {
      return null;
    }
  }

  function buildMonthOptions() {
    if (!monthSelect) return;
    monthSelect.innerHTML = monthNames.map(function (name, index) {
      return '<option value="' + index + '">' + name + '</option>';
    }).join('');
  }

  function buildYearOptions() {
    if (!yearSelect) return;
    const startYear = today.getFullYear();
    const endYear = today.getFullYear() + 2;
    let options = '';
    for (let year = startYear; year <= endYear; year += 1) {
      options += '<option value="' + year + '">' + year + '</option>';
    }
    yearSelect.innerHTML = options;
  }

  function currentMonthLabel() {
    return monthNames[calendarState.month] + ' ' + calendarState.year;
  }

  function renderCalendar() {
    if (!grid) return;

    const firstDay = new Date(calendarState.year, calendarState.month, 1).getDay();
    const daysInMonth = new Date(calendarState.year, calendarState.month + 1, 0).getDate();
    const previousMonthDays = new Date(calendarState.year, calendarState.month, 0).getDate();

    if (calendarLabel) {
      calendarLabel.textContent = currentMonthLabel();
    }
    if (monthSelect) monthSelect.value = String(calendarState.month);
    if (yearSelect) yearSelect.value = String(calendarState.year);

    let cells = '';
    for (let index = 0; index < firstDay; index += 1) {
      const dayNumber = previousMonthDays - firstDay + index + 1;
      cells += '<button type="button" class="calendar-day calendar-day-outside" aria-disabled="true" tabindex="-1"><span>' + dayNumber + '</span></button>';
    }

    for (let day = 1; day <= daysInMonth; day += 1) {
      const dateString = calendarState.year + '-' + String(calendarState.month + 1).padStart(2, '0') + '-' + String(day).padStart(2, '0');
      const date = new Date(calendarState.year, calendarState.month, day);
      const isToday = date.toDateString() === today.toDateString();
      const isWeekend = date.getDay() === 0 || date.getDay() === 6;
      const isAvailable = availabilitySet.has(dateString);
      const classes = ['calendar-day'];

      if (isToday) classes.push('is-today');
      if (isWeekend) classes.push('is-weekend');
      if (!isAvailable) classes.push('calendar-day-unavailable');
      if (selectedEventId && upcomingEventMap.get(String(selectedEventId)) && upcomingEventMap.get(String(selectedEventId)).event_date === dateString) {
        classes.push('is-selected');
      }

      cells += '<button type="button" class="' + classes.join(' ') + '" aria-label="' + currentMonthLabel() + ' ' + day + '"><span class="calendar-day-number">' + day + '</span><span class="calendar-day-state">' + (isAvailable ? 'Available' : 'Unavailable') + '</span></button>';
    }

    const remainingCells = 42 - (firstDay + daysInMonth);
    for (let nextDay = 1; nextDay <= remainingCells; nextDay += 1) {
      cells += '<button type="button" class="calendar-day calendar-day-outside" aria-disabled="true" tabindex="-1"><span>' + nextDay + '</span></button>';
    }

    grid.innerHTML = cells;
  }

  function updateBookingState() {
    if (!selectedService || !bookingSubmit || !bookingStatus || !bookingEventId || !bookingServiceId) return;

    bookingServiceId.value = String(selectedService.id);
    bookingEventId.value = String(selectedEventId || '');

    const event = upcomingEventMap.get(String(selectedEventId || '')) || null;

    bookingSubmit.disabled = !event;

    if (!event) {
      bookingStatus.textContent = 'Choose an event to continue.';
      bookingStatus.style.color = '';
    } else {
      bookingStatus.textContent = 'Ready to submit booking request.';
      bookingStatus.style.color = '';
    }

    persistState();
  }

  function renderEventOptions() {
    if (!eventSelect) return;
    const options = ['<option value="">Select an event</option>'];

    upcomingEvents.forEach(function (event) {
      options.push(
        '<option value="' + event.id + '">' +
        event.title + ' - ' + event.event_date_label +
        '</option>'
      );
    });

    eventSelect.innerHTML = options.join('');
    eventSelect.value = String(selectedEventId || '');
  }

  function applyServiceData(service) {
    selectedService = service;
    availabilitySet = new Set((service.availability_dates || []).map(function (value) { return String(value); }));

    if (titleEl) titleEl.textContent = service.name || '';
    if (companyEl) companyEl.textContent = service.company_name || '';
    if (typeEl) typeEl.textContent = (service.service_type || 'other').replace(/_/g, ' ');
    if (descEl) descEl.textContent = service.description || '';
    if (icon) icon.textContent = iconMap[service.service_type] || iconMap.other;
    if (bookingServiceId) bookingServiceId.value = String(service.id);

    renderEventOptions();
    renderCalendar();
    updateBookingState();
    window.openModal(modal);
  }

  function openFromCard(card) {
    const service = serviceMap.get(String(card.dataset.serviceId || ''));
    if (!service) return;

    const persisted = loadPersistedState(service.id);
    selectedEventId = persisted && persisted.eventId ? persisted.eventId : '';
    if (persisted) {
      calendarState.year = Number.parseInt(persisted.year, 10) || today.getFullYear();
      calendarState.month = Number.parseInt(persisted.month, 10) || today.getMonth();
    } else {
      calendarState.year = today.getFullYear();
      calendarState.month = today.getMonth();
    }

    applyServiceData(service);
    if (eventSelect) eventSelect.value = String(selectedEventId || '');
  }

  function moveMonth(delta) {
    const next = new Date(calendarState.year, calendarState.month + delta, 1);
    calendarState.year = next.getFullYear();
    calendarState.month = next.getMonth();
    renderCalendar();
    persistState();
  }

  buildMonthOptions();
  buildYearOptions();
  renderCalendar();

  if (monthSelect) {
    monthSelect.addEventListener('change', function () {
      calendarState.month = Number.parseInt(monthSelect.value, 10);
      renderCalendar();
      persistState();
    });
  }

  if (yearSelect) {
    yearSelect.addEventListener('change', function () {
      calendarState.year = Number.parseInt(yearSelect.value, 10);
      renderCalendar();
      persistState();
    });
  }

  document.querySelectorAll('[data-calendar-nav]').forEach(function (button) {
    button.addEventListener('click', function () {
      const action = button.getAttribute('data-calendar-nav');
      if (action === 'prev') {
        moveMonth(-1);
      } else if (action === 'next') {
        moveMonth(1);
      } else {
        calendarState.year = today.getFullYear();
        calendarState.month = today.getMonth();
        renderCalendar();
        persistState();
      }
    });
  });

  if (eventSelect) {
    eventSelect.addEventListener('change', function () {
      selectedEventId = eventSelect.value;
      renderCalendar();
      updateBookingState();
    });
  }

  if (bookingForm) {
    bookingForm.addEventListener('submit', function (event) {
      if (!selectedService || !selectedEventId || bookingSubmit.disabled) {
        event.preventDefault();
        return;
      }
      // Standard form submission without fetch API.
      bookingSubmit.disabled = true;
      bookingSubmit.textContent = "Booking...";
    });
  }

  document.querySelectorAll('.service-card[data-service-id]').forEach(function (card) {
    function openCard() {
      openFromCard(card);
    }
    card.addEventListener('click', openCard);
    card.addEventListener('keydown', function (event) {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        openCard();
      }
    });
  });

  document.querySelectorAll('[data-close-modal]').forEach(function (button) {
    button.addEventListener('click', function () {
      const modalId = button.getAttribute('data-close-modal');
      window.closeModal(document.getElementById(modalId));
    });
  });

  document.querySelectorAll('.modal').forEach(function (overlay) {
    overlay.addEventListener('click', function (event) {
      if (event.target === overlay) {
        window.closeModal(overlay);
      }
    });
  });

  if (window.location.hash === '#service-detail-modal' && servicesData.length) {
    openFromCard(document.querySelector('.service-card[data-service-id]'));
  }
});


