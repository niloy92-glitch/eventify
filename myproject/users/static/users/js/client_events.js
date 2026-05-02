(function () {
  const storageKeys = {
    draft: "eventify.clientEvents.draft",
  };

  function readJsonScript(id) {
    const node = document.getElementById(id);
    if (!node) return [];
    try {
      return JSON.parse(node.textContent || "[]");
    } catch (error) {
      return [];
    }
  }

  function loadDraft() {
    try {
      return JSON.parse(localStorage.getItem(storageKeys.draft) || "null") || {};
    } catch (error) {
      return {};
    }
  }

  function saveDraft(payload) {
    localStorage.setItem(storageKeys.draft, JSON.stringify(payload));
  }

  function clearDraft() {
    localStorage.removeItem(storageKeys.draft);
  }

  function buildEventMap(events) {
    const map = new Map();
    events.forEach(function (event) {
      map.set(String(event.id), event);
    });
    return map;
  }

  function formatMoney(value) {
    const amount = Number.parseFloat(value || 0);
    return "BDT " + amount.toFixed(2);
  }

  function toggleModal(modal, open) {
    if (!modal) return;
    if (open) {
      window.openModal(modal);
    } else {
      window.closeModal(modal);
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (window.EventifyToast) {
      window.EventifyToast.fromQuery();
    }

    localStorage.removeItem("eventify.clientEvents.selectedEventId");

    const eventData = readJsonScript("client-events-data");
    const eventMap = buildEventMap(eventData);
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const listPanel = document.getElementById("client-events-list-panel");
    const detailPanel = document.getElementById("client-event-detail-panel");
    const listContainer = document.getElementById("client-events-list");
    const backButton = document.getElementById("client-event-back");
    const editButton = document.getElementById("client-event-edit");
    const deleteButton = document.getElementById("client-event-delete");
    const paymentBadge = document.getElementById("client-event-payment-badge");
    const detailTitle = document.getElementById("client-event-title");
    const detailDate = document.getElementById("client-event-date-label");
    const detailVenue = document.getElementById("client-event-venue");
    const detailAddress = document.getElementById("client-event-address");
    const detailOwnVenue = document.getElementById("client-event-own-venue");
    const detailNotes = document.getElementById("client-event-notes");
    const detailServices = document.getElementById("client-event-services");
    const detailTotal = document.getElementById("client-event-total");
    const paymentForm = document.getElementById("client-event-payment-form");
    const paymentInput = document.getElementById("client-event-payment-input");
    const paymentSave = document.getElementById("client-event-payment-save");
    const paymentButtons = Array.from(document.querySelectorAll("[data-payment-option]"));
    const eventModal = document.getElementById("client-event-modal");
    const eventForm = document.getElementById("client-event-form");
    const eventSubmit = document.getElementById("client-event-submit");
    const eventModalTitle = document.getElementById("client-event-modal-title");
    const eventIdInput = document.getElementById("client-event-id");
    const eventDeleteModal = document.getElementById("event-delete-modal");
    const eventDeleteForm = document.getElementById("event-delete-form");
    const eventDeletePassword = document.getElementById("event-delete-password");
    const createButtons = Array.from(document.querySelectorAll("[data-open-create-event]"));
    const filterButtons = Array.from(document.querySelectorAll("[data-event-filter]"));
    const cardButtons = Array.from(document.querySelectorAll("[data-event-card]"));

    const formFieldIds = [
      "client-event-title",
      "client-event-date",
      "client-event-venue-name",
      "client-event-venue-address",
      "client-event-own-venue",
      "client-event-notes",
    ];

    function toggleVenueFields() {
      const ownVenue = document.getElementById("client-event-own-venue");
      const venueName = document.getElementById("client-event-venue-name");
      const venueAddress = document.getElementById("client-event-venue-address");
      if (ownVenue && venueName && venueAddress) {
        venueName.disabled = ownVenue.checked;
        venueAddress.disabled = ownVenue.checked;
        const nameGroup = venueName.closest(".form-field");
        const addressGroup = venueAddress.closest(".form-field");
        if (nameGroup) nameGroup.style.opacity = ownVenue.checked ? "0.5" : "1";
        if (addressGroup) addressGroup.style.opacity = ownVenue.checked ? "0.5" : "1";
      }
    }

    const ownVenueCheck = document.getElementById("client-event-own-venue");
    if (ownVenueCheck) {
      ownVenueCheck.addEventListener("change", toggleVenueFields);
    }

    let selectedEvent = null;
    let savedPaymentMethod = "";
    let selectedPaymentMethod = "";

    function setListVisible() {
      if (listPanel) {
        listPanel.hidden = false;
      }
    }

    function setDetailVisible(showDetail) {
      if (detailPanel) {
        detailPanel.hidden = !showDetail;
      }
    }

    function renderServices(event) {
      if (!detailServices) return;
      const services = (event && (event.services || event.service_rows)) || [];
      if (!services.length) {
        detailServices.innerHTML = '<p class="muted">No services attached to this event yet.</p>';
        return;
      }

      detailServices.innerHTML = services.map(function (service) {
        return [
          '<div class="event-service-row">',
          '<div>',
          '<strong>' + (service.service_name || service.name || 'Service') + '</strong>',
          '<p class="muted">' + (service.vendor_name || service.vendor || '') + '</p>',
          '</div>',
          '<div class="event-service-meta">',
          '<span class="badge ' + (service.status_badge || 'pending') + '">' + (service.status_label || 'Pending') + '</span>',
          '<strong>' + formatMoney(service.price) + '</strong>',
          '</div>',
          '</div>',
        ].join("");
      }).join("");
    }

    function updatePaymentButtons() {
      paymentButtons.forEach(function (button) {
        const value = button.getAttribute("data-payment-option") || "";
        const isActive = value === selectedPaymentMethod;
        const isSaved = value === savedPaymentMethod;
        button.classList.toggle("active", isActive);
        button.classList.toggle("inactive", Boolean(selectedPaymentMethod) && !isActive);
        button.classList.toggle("is-saved", isSaved && !isActive);
        button.setAttribute("aria-pressed", isActive ? "true" : "false");
      });

      if (paymentInput) {
        paymentInput.value = selectedPaymentMethod;
      }
      if (paymentSave) {
        paymentSave.disabled = !selectedPaymentMethod || selectedPaymentMethod === savedPaymentMethod;
      }
      if (paymentBadge) {
        paymentBadge.textContent = selectedPaymentMethod ? selectedPaymentMethod.replace(/_/g, " ").replace(/\b\w/g, function (letter) { return letter.toUpperCase(); }) : "Payment pending";
        paymentBadge.className = "badge " + (selectedPaymentMethod ? "confirmed" : "pending");
      }
    }

    function selectPayment(value) {
      selectedPaymentMethod = value;
      updatePaymentButtons();
    }

    function populatePaymentArea(event) {
      savedPaymentMethod = event.payment_method || "";
      selectedPaymentMethod = event.payment_method || "";
      if (paymentForm && event.id) {
        const template = paymentForm.getAttribute("data-payment-url-template") || "";
        paymentForm.action = template.replace(/\/0\//, "/" + event.id + "/");
      }
      updatePaymentButtons();
    }

    function renderEvent(event) {
      selectedEvent = event;
      if (!event) return;

      if (detailTitle) detailTitle.textContent = event.title || "";
      if (detailDate) detailDate.textContent = event.event_date_label || "";
      if (detailVenue) detailVenue.textContent = event.venue_name || "Venue not set";
      if (detailAddress) detailAddress.textContent = event.venue_address || "—";
      if (detailOwnVenue) detailOwnVenue.textContent = event.has_own_venue ? "Yes" : "No";
      if (detailNotes) detailNotes.textContent = event.notes || "—";
      if (detailTotal) detailTotal.textContent = formatMoney(event.total_cost);
      renderServices(event);
      populatePaymentArea(event);
      setDetailVisible(true);
      setListVisible();
    }

    function renderEmptyState() {
      selectedEvent = null;
      if (detailTitle) detailTitle.textContent = "No event selected";
      if (detailDate) detailDate.textContent = "";
      if (detailVenue) detailVenue.textContent = "Select an event from the list above.";
      if (detailAddress) detailAddress.textContent = "";
      if (detailOwnVenue) detailOwnVenue.textContent = "";
      if (detailNotes) detailNotes.textContent = "";
      if (detailServices) detailServices.innerHTML = '<p class="muted">Choose an event to see the booked services and cost breakdown.</p>';
      if (detailTotal) detailTotal.textContent = "BDT 0.00";
      if (paymentBadge) paymentBadge.textContent = "Select an event";
      if (paymentBadge) paymentBadge.className = "badge pending";
      if (paymentSave) paymentSave.disabled = true;
      if (paymentInput) paymentInput.value = "";
      setDetailVisible(false);
    }

    function openCreateModal() {
      if (!eventForm || !eventModal) return;
      const draft = loadDraft();
      const createUrl = eventForm.getAttribute("data-create-url") || eventForm.action;
      eventForm.action = createUrl;
      if (eventModalTitle) eventModalTitle.textContent = "Create Event";
      if (eventSubmit) eventSubmit.textContent = "Save Event";
      if (eventIdInput) eventIdInput.value = "";

      formFieldIds.forEach(function (fieldId) {
        const field = document.getElementById(fieldId);
        if (!field) return;
        const key = field.name || field.id;
        if (field.type === "checkbox") {
          field.checked = Boolean(draft[key]);
        } else if (draft[key] !== undefined) {
          field.value = draft[key];
        }
      });

      if (typeof toggleVenueFields === "function") {
        toggleVenueFields();
      }

      toggleModal(eventModal, true);
    }

    function openEditModal(event) {
      if (!eventForm || !eventModal) return;
      const template = eventForm.getAttribute("data-update-url-template") || eventForm.action;
      eventForm.action = template.replace(/\/0\//, "/" + event.id + "/");
      if (eventModalTitle) eventModalTitle.textContent = "Edit Event";
      if (eventSubmit) eventSubmit.textContent = "Update Event";
      if (eventIdInput) eventIdInput.value = String(event.id);

      const titleField = document.getElementById("client-event-title");
      const dateField = document.getElementById("client-event-date");
      const venueField = document.getElementById("client-event-venue-name");
      const addressField = document.getElementById("client-event-venue-address");
      const ownVenueField = document.getElementById("client-event-own-venue");
      const notesField = document.getElementById("client-event-notes");

      if (titleField) titleField.value = event.title || "";
      if (dateField) dateField.value = event.event_date || "";
      if (venueField) venueField.value = event.venue_name || "";
      if (addressField) addressField.value = event.venue_address || "";
      if (ownVenueField) ownVenueField.checked = Boolean(event.has_own_venue);
      if (notesField) notesField.value = event.notes || "";

      if (typeof toggleVenueFields === "function") {
        toggleVenueFields();
      }

      toggleModal(eventModal, true);
    }

    function openDeleteModal(event) {
      if (!eventDeleteModal || !eventDeleteForm) return;
      const template = eventDeleteForm.getAttribute("data-delete-url-template") || eventDeleteForm.action;
      eventDeleteForm.action = template.replace(/\/0\//, "/" + event.id + "/");
      if (eventDeletePassword) eventDeletePassword.value = "";
      if (document.getElementById("event-delete-title")) {
        document.getElementById("event-delete-title").textContent = "Delete " + (event.title || "event") + "?";
      }
      toggleModal(eventDeleteModal, true);
    }

    function applyFilter(filterKey) {
      cardButtons.forEach(function (card) {
        const event = eventMap.get(String(card.getAttribute("data-event-id") || ""));
        if (!event) return;

        const eventDate = new Date(event.event_date + "T00:00:00");
        const matches = filterKey === "all" ||
          (filterKey === "upcoming" && eventDate >= today) ||
          (filterKey === "completed" && eventDate < today) ||
          (filterKey === "venue" && Boolean(event.has_own_venue));
        card.hidden = !matches;
      });
    }

    formFieldIds.forEach(function (fieldId) {
      const field = document.getElementById(fieldId);
      if (!field || !eventForm) return;
      field.addEventListener("input", function () {
        if (eventForm.action === eventForm.getAttribute("data-create-url")) {
          const draft = loadDraft();
          formFieldIds.forEach(function (id) {
            const input = document.getElementById(id);
            if (!input) return;
            draft[input.name || input.id] = input.type === "checkbox" ? input.checked : input.value;
          });
          saveDraft(draft);
        }
      });
    });

    createButtons.forEach(function (button) {
      button.addEventListener("click", openCreateModal);
    });

    if (backButton) {
      backButton.addEventListener("click", function () {
        setListVisible();
      });
    }

    if (editButton) {
      editButton.addEventListener("click", function () {
        if (selectedEvent) {
          openEditModal(selectedEvent);
        }
      });
    }

    if (deleteButton) {
      deleteButton.addEventListener("click", function () {
        if (selectedEvent) {
          openDeleteModal(selectedEvent);
        }
      });
    }

    cardButtons.forEach(function (button) {
      function activate() {
        const event = eventMap.get(String(button.getAttribute("data-event-id") || ""));
        if (event) {
          renderEvent(event);
        }
      }
      button.addEventListener("click", activate);
      button.addEventListener("keydown", function (event) {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          activate();
        }
      });
    });

    filterButtons.forEach(function (button) {
      button.addEventListener("click", function () {
        filterButtons.forEach(function (item) { item.classList.remove("active"); });
        button.classList.add("active");
        applyFilter(button.getAttribute("data-event-filter") || "all");
      });
    });

    paymentButtons.forEach(function (button) {
      button.addEventListener("click", function () {
        selectPayment(button.getAttribute("data-payment-option") || "");
      });
    });

    if (paymentForm) {
      paymentForm.addEventListener("submit", function (event) {
        if (!selectedEvent || !selectedPaymentMethod || selectedPaymentMethod === savedPaymentMethod) {
          event.preventDefault();
        }
      });
    }

    if (eventForm) {
      eventForm.addEventListener("submit", function () {
        clearDraft();
      });
    }

    document.querySelectorAll("[data-close-modal]").forEach(function (button) {
      button.addEventListener("click", function () {
        const modalId = button.getAttribute("data-close-modal");
        toggleModal(document.getElementById(modalId), false);
      });
    });

    document.querySelectorAll(".modal").forEach(function (modal) {
      modal.addEventListener("click", function (event) {
        if (event.target === modal) {
          toggleModal(modal, false);
        }
      });
    });

    applyFilter("all");
    renderEmptyState();
  });
})();
