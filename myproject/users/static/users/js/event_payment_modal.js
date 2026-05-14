/**
 * Event Payment Modal
 * Handles billing display, amount selection, service rating, and checkout flow.
 */

(function () {
  class EventPaymentModal {
    constructor() {
      this.modal = document.getElementById("event-payment-modal");
      this.form = document.getElementById("payment-workflow");
      this.amountInput = document.getElementById("payment-amount-input");
      this.selectAllCheckbox = document.getElementById("payment-select-all-services");
      this.proceedBtn = document.getElementById("payment-proceed-btn");
      this.servicesList = document.getElementById("payment-services-list");
      this.checkboxContainer = document.getElementById("payment-service-checkboxes");
      this.serviceTemplate = document.getElementById("payment-service-template");
      this.checkboxTemplate = document.getElementById("payment-service-checkbox-template");

      this.eventId = null;
      this.services = [];
      this.bookings = [];
      this.billData = { total: 0, paid: 0, outstanding: 0 };

      if (this.modal) {
        this.setupEventListeners();
      }
    }

    setupEventListeners() {
      this.proceedBtn?.addEventListener("click", () => this.handleProceed());
      this.selectAllCheckbox?.addEventListener("change", () => this.handleSelectAllChange());
      this.amountInput?.addEventListener("input", () => this.updateRemainingText());

  const closeButtons = this.modal?.querySelectorAll("[data-close-modal='event-payment-modal'], .modal-close-btn");
      closeButtons?.forEach((btn) => {
        btn.addEventListener("click", () => this.close());
      });

      this.modal?.addEventListener("click", (e) => {
        if (e.target === this.modal) this.close();
      });
    }

    open(eventId, eventTitle, eventDate, bookings) {
      if (!this.modal || !this.servicesList) return;

      this.eventId = eventId;
      this.bookings = bookings || [];
      this.setupBill();
      this.populateServices();
      this.setupCheckboxes();

      const titleEl = document.getElementById("payment-event-title");
      const dateEl = document.getElementById("payment-event-date");
      if (titleEl) titleEl.textContent = eventTitle || "";
      if (dateEl) dateEl.textContent = eventDate ? `Event Date: ${eventDate}` : "";

      this.showStep("bill");
      this.modal.removeAttribute("hidden");
      this.modal.removeAttribute("inert");
      this.modal.classList.add("open");
      this.modal.setAttribute("aria-hidden", "false");
    }

    close() {
      if (!this.modal) return;
      this.modal.classList.remove("open");
      this.modal.setAttribute("hidden", "");
      this.modal.setAttribute("inert", "inert");
      this.modal.setAttribute("aria-hidden", "true");
    }

    showStep(stepName) {
      document.querySelectorAll(".payment-step").forEach((step) => {
        step.style.display = "none";
        step.setAttribute("hidden", "");
      });
      const activeStep = document.getElementById(`payment-step-${stepName}`);
      if (activeStep) {
        activeStep.style.display = "block";
        activeStep.removeAttribute("hidden");
      }
    }

    setupBill() {
      // Fetch bill data from API or compute from bookings
      let total = 0;
      this.bookings.forEach((booking) => {
        total += parseFloat(booking.price) || 0;
      });

      this.billData = {
        total: total,
        paid: 0, // Placeholder; fetch from API if needed
        outstanding: total,
      };

      document.getElementById("bill-total").textContent = this.billData.total.toFixed(2);
      document.getElementById("bill-paid").textContent = this.billData.paid.toFixed(2);
      document.getElementById("bill-outstanding").textContent = this.billData.outstanding.toFixed(2);
    }

    populateServices() {
      if (!this.servicesList) return;
      this.servicesList.innerHTML = "";

      this.bookings.forEach((booking) => {
        const clone = this.serviceTemplate.content.cloneNode(true);

        const nameEl = clone.querySelector(".payment-service-name");
        if (nameEl) nameEl.textContent = booking.service_name || "Service";

        const typeEl = clone.querySelector(".payment-service-type");
        if (typeEl) typeEl.textContent = booking.service_type || "";

        const priceEl = clone.querySelector(".payment-service-price");
        if (priceEl) priceEl.textContent = (parseFloat(booking.price) || 0).toFixed(2);

        const fieldset = clone.querySelector(".star-rating");
        if (fieldset) {
          fieldset.dataset.serviceId = booking.service_id;
          const inputs = clone.querySelectorAll('input[type="radio"]');
          inputs.forEach((input, idx) => {
            input.name = `rating-${booking.service_id}`;
            const label = clone.querySelectorAll(".star-label")[idx];
            if (label) label.setAttribute("for", `star-${5 - idx}-${booking.service_id}`);
            input.id = `star-${5 - idx}-${booking.service_id}`;
          });

          const ratingLabel = clone.querySelector(".payment-service-rating-label");
          inputs.forEach((input) => {
            input.addEventListener("change", () => {
              if (ratingLabel)
                ratingLabel.textContent = `${input.value} star${input.value !== "1" ? "s" : ""} selected`;
            });
          });
        }

        this.servicesList.appendChild(clone);
      });
    }

    setupCheckboxes() {
      if (!this.checkboxContainer) return;
      this.checkboxContainer.innerHTML = "";

      this.bookings.forEach((booking) => {
        const clone = this.checkboxTemplate.content.cloneNode(true);
        const checkbox = clone.querySelector(".payment-service-checkbox");
        const label = clone.querySelector(".payment-checkbox-label");

        if (checkbox) {
          checkbox.dataset.bookingId = booking.booking_id;
          checkbox.checked = true; // Default all selected
          checkbox.addEventListener("change", () => this.updateSelectAllCheckbox());
        }

        if (label) label.textContent = `${booking.service_name} (BDT ${(parseFloat(booking.price) || 0).toFixed(2)})`;

        this.checkboxContainer.appendChild(clone);
      });

      this.updateSelectAllCheckbox();
    }

    handleSelectAllChange() {
      const isChecked = this.selectAllCheckbox?.checked;
      document.querySelectorAll(".payment-service-checkbox").forEach((checkbox) => {
        checkbox.checked = isChecked;
      });
    }

    updateSelectAllCheckbox() {
      const checkboxes = document.querySelectorAll(".payment-service-checkbox");
      const checkedCount = Array.from(checkboxes).filter((cb) => cb.checked).length;
      if (this.selectAllCheckbox) {
        this.selectAllCheckbox.checked = checkedCount === checkboxes.length;
      }
    }

    updateRemainingText() {
      const amount = parseFloat(this.amountInput?.value) || 0;
      const remaining = Math.max(0, this.billData.outstanding - amount);
      const el = document.getElementById("payment-remaining-text");
      if (el) {
        if (remaining > 0) {
          el.textContent = `Due after payment: BDT ${remaining.toFixed(2)}`;
        } else if (amount === this.billData.outstanding) {
          el.textContent = "Full payment";
        } else if (amount > 0) {
          el.textContent = "Overpayment not allowed";
          this.amountInput.value = this.billData.outstanding.toFixed(2);
        } else {
          el.textContent = "Enter amount";
        }
      }
    }

    collectRatings() {
      const ratings = {};
      this.modal.querySelectorAll(".star-rating").forEach((fieldset) => {
        const serviceId = fieldset.dataset.serviceId;
        const checked = fieldset.querySelector('input[type="radio"]:checked');
        if (serviceId && checked) {
          ratings[serviceId] = parseInt(checked.value);
        }
      });
      return ratings;
    }

    getSelectedBookingIds() {
      return Array.from(document.querySelectorAll(".payment-service-checkbox:checked")).map((cb) =>
        cb.dataset.bookingId
      );
    }

    async handleProceed() {
      const amount = parseFloat(this.amountInput?.value) || 0;
      const selectedIds = this.getSelectedBookingIds();
      const ratings = this.collectRatings();

      if (amount <= 0) {
        alert("Please enter a valid amount.");
        return;
      }

      if (selectedIds.length === 0) {
        alert("Please select at least one service to pay.");
        return;
      }

      this.showStep("processing");

      try {
        const resp = await fetch(`/payment/events/${this.eventId}/checkout/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": this.getCsrfToken(),
          },
          body: JSON.stringify({
            amount: amount.toFixed(2),
            selected_booking_ids: selectedIds,
            ratings: ratings,
          }),
        });

        const data = await resp.json();

        if (!resp.ok || !data.ok) {
          // Payment failed
          const failureMsg = document.getElementById("payment-failure-message");
          if (failureMsg) failureMsg.textContent = data.error || "Payment processing failed.";

          if (data.missing_vendors && data.missing_vendors.length > 0) {
            const vendorContainer = document.getElementById("payment-failure-vendors");
            const vendorList = document.getElementById("payment-failure-vendor-list");
            if (vendorContainer && vendorList) {
              vendorContainer.style.display = "block";
              vendorList.innerHTML = "";
              data.missing_vendors.forEach((v) => {
                const li = document.createElement("li");
                li.textContent = `${v.vendor} - ${v.service}`;
                vendorList.appendChild(li);
              });
            }
          }

          this.showStep("failure");
          return;
        }

        // Payment success
        const successMsg = document.getElementById("payment-success-message");
        if (successMsg) {
          successMsg.textContent = `Transaction ${data.transaction_ref}: You paid BDT ${data.paid_amount}. ${data.due_after > 0 ? `Due: BDT ${data.due_after}` : "Event fully paid!"}`;
        }

        this.showStep("success");

        setTimeout(() => {
          window.location.reload();
        }, 2000);
      } catch (err) {
        console.error("Checkout error:", err);
        const failureMsg = document.getElementById("payment-failure-message");
        if (failureMsg) failureMsg.textContent = "Network error. Please try again.";
        this.showStep("failure");
      }
    }

    getCsrfToken() {
      return (
        document.querySelector('[name="csrfmiddlewaretoken"]')?.value ||
        document.cookie
          .split("; ")
          .find((row) => row.startsWith("csrftoken="))
          ?.split("=")[1] ||
        ""
      );
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      window.eventPaymentModal = new EventPaymentModal();
    });
  } else {
    window.eventPaymentModal = new EventPaymentModal();
  }
})();
