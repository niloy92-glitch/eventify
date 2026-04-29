(function () {
  function togglePopover() {
    const button = document.getElementById("notification-toggle");
    const popover = document.getElementById("notification-popover");

    if (!button || !popover) return;

    const close = function () {
      popover.hidden = true;
      button.setAttribute("aria-expanded", "false");
    };

    button.addEventListener("click", function (event) {
      event.stopPropagation();
      const opening = popover.hidden;
      popover.hidden = !popover.hidden;
      button.setAttribute("aria-expanded", opening ? "true" : "false");
    });

    document.addEventListener("click", function (event) {
      if (!popover.hidden && !popover.contains(event.target) && event.target !== button) {
        close();
      }
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") close();
    });
  }

  function initFilterButtons() {
    const buttons = document.querySelectorAll("[data-user-filter]");
    const rows = document.querySelectorAll("#users-table-body tr[data-user-role]");

    if (!buttons.length || !rows.length) return;

    buttons.forEach(function (button) {
      button.addEventListener("click", function () {
        const selected = button.getAttribute("data-user-filter");

        buttons.forEach(function (item) {
          item.classList.remove("active");
        });
        button.classList.add("active");

        rows.forEach(function (row) {
          const role = row.getAttribute("data-user-role");
          const show = selected === "all" || role === selected;
          row.style.display = show ? "" : "none";
        });
      });
    });
  }

  function openModal(modal) {
    if (!modal) return;
    modal.classList.add("open");
    modal.setAttribute("aria-hidden", "false");
  }

  function closeModal(modal) {
    if (!modal) return;
    modal.classList.remove("open");
    modal.setAttribute("aria-hidden", "true");
  }

  function initUserModals() {
    const editModal = document.getElementById("edit-user-modal");
    const deleteModal = document.getElementById("delete-user-modal");
    const editId = document.getElementById("edit-user-id");
    const editFirstName = document.getElementById("edit-user-first-name");
    const editLastName = document.getElementById("edit-user-last-name");
    const editEmail = document.getElementById("edit-user-email");
    const editRole = document.getElementById("edit-user-role");
    const editCompanyName = document.getElementById("edit-user-company-name");
    const editPhone = document.getElementById("edit-user-phone");
    const editAddress = document.getElementById("edit-user-address");
    const editEmailVerified = document.getElementById("edit-user-email-verified");
    const editForm = document.getElementById("edit-user-form");
    const deleteForm = document.getElementById("delete-user-form");
    const deleteText = document.getElementById("delete-user-text");

    document.querySelectorAll("[data-open-edit]").forEach(function (button) {
      button.addEventListener("click", function () {
        if (editId) editId.value = button.getAttribute("data-user-id") || "";
        if (editFirstName) editFirstName.value = button.getAttribute("data-first-name") || "";
        if (editLastName) editLastName.value = button.getAttribute("data-last-name") || "";
        if (editEmail) editEmail.value = button.getAttribute("data-email") || "";
        if (editRole) editRole.value = button.getAttribute("data-role") || "client";
        if (editCompanyName) editCompanyName.value = button.getAttribute("data-company-name") || "";
        if (editPhone) editPhone.value = button.getAttribute("data-phone") || "";
        if (editAddress) editAddress.value = button.getAttribute("data-address") || "";
        if (editEmailVerified) {
          editEmailVerified.checked = button.getAttribute("data-email-verified") === "true";
        }
        if (editForm) {
          editForm.action = button.getAttribute("data-update-url") || "#";
        }
        openModal(editModal);
      });
    });

    document.querySelectorAll("[data-open-delete]").forEach(function (button) {
      button.addEventListener("click", function () {
        const name = button.getAttribute("data-name") || "this user";
        if (deleteText) {
          deleteText.textContent = "Are you sure you want to delete " + name + "?";
        }
        if (deleteForm) {
          deleteForm.action = button.getAttribute("data-delete-url") || "#";
        }
        openModal(deleteModal);
      });
    });

    document.querySelectorAll("[data-close-modal]").forEach(function (button) {
      button.addEventListener("click", function () {
        const modalId = button.getAttribute("data-close-modal");
        closeModal(document.getElementById(modalId));
      });
    });

    document.querySelectorAll(".modal").forEach(function (modal) {
      modal.addEventListener("click", function (event) {
        if (event.target === modal) closeModal(modal);
      });
    });

    // Keep native form submit behavior for real backend update/delete actions.
  }

  function initProfileModals() {
    const editModal = document.getElementById("edit-profile-modal");
    const deleteModal = document.getElementById("delete-account-modal");

    if (!editModal && !deleteModal) {
      return;
    }

    const fieldMap = {
      "data-first-name": document.getElementById("edit-profile-first-name"),
      "data-last-name": document.getElementById("edit-profile-last-name"),
      "data-email": document.getElementById("edit-profile-email"),
      "data-company-name": document.getElementById("edit-profile-company-name"),
      "data-phone": document.getElementById("edit-profile-phone"),
      "data-address": document.getElementById("edit-profile-address"),
    };
    const passwordInput = document.getElementById("delete-account-password");

    document.querySelectorAll("[data-open-edit-profile]").forEach(function (button) {
      button.addEventListener("click", function () {
        Object.keys(fieldMap).forEach(function (attributeName) {
          const input = fieldMap[attributeName];
          if (input) {
            input.value = button.getAttribute(attributeName) || "";
          }
        });
        openModal(editModal);
      });
    });

    document.querySelectorAll("[data-open-delete-account]").forEach(function (button) {
      button.addEventListener("click", function () {
        if (passwordInput) {
          passwordInput.value = "";
        }
        openModal(deleteModal);
      });
    });

    document.querySelectorAll("[data-close-modal]").forEach(function (button) {
      button.addEventListener("click", function () {
        const modalId = button.getAttribute("data-close-modal");
        closeModal(document.getElementById(modalId));
      });
    });

    document.querySelectorAll(".modal").forEach(function (modal) {
      modal.addEventListener("click", function (event) {
        if (event.target === modal) closeModal(modal);
      });
    });
  }

  function initApprovalActions() {
    const approvalModal = document.getElementById("approval-confirm-modal");
    const modalTitle = document.getElementById("approval-modal-title");
    const modalText = document.getElementById("approval-modal-text");
    const requestTypeInput = document.getElementById("approval-request-type");
    const requestIdInput = document.getElementById("approval-request-id");
    const decisionInput = document.getElementById("approval-decision");
    const submitButton = document.getElementById("approval-confirm-submit");

    if (!approvalModal || !requestTypeInput || !requestIdInput || !decisionInput || !submitButton) {
      return;
    }

    document.querySelectorAll("[data-open-approval-modal]").forEach(function (button) {
      button.addEventListener("click", function () {
        const decision = button.getAttribute("data-decision") || "approve";
        const requestType = button.getAttribute("data-request-type") || "vendor";
        const requestId = button.getAttribute("data-request-id") || "";
        const vendorName = button.getAttribute("data-vendor-name") || "this vendor";
        const serviceName = button.getAttribute("data-service-name") || "-";

        requestTypeInput.value = requestType;
        requestIdInput.value = requestId;
        decisionInput.value = decision;

        const isApprove = decision === "approve";
        const targetLabel = requestType === "service" && serviceName !== "-"
          ? "service \"" + serviceName + "\" from " + vendorName
          : "vendor " + vendorName;

        if (modalTitle) {
          modalTitle.textContent = isApprove ? "Approve Request" : "Reject Request";
        }

        if (modalText) {
          modalText.textContent = (isApprove ? "Approve " : "Reject ") + targetLabel + "?";
        }

        submitButton.textContent = isApprove ? "Approve" : "Reject";
        submitButton.classList.toggle("btn-primary", isApprove);
        submitButton.classList.toggle("danger-btn", !isApprove);

        openModal(approvalModal);
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (window.EventifyToast) {
      window.EventifyToast.fromQuery();
    }
    togglePopover();
    initFilterButtons();
    initUserModals();
    initProfileModals();
    initApprovalActions();
  });
})();
