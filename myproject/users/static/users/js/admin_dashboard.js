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
    const editName = document.getElementById("edit-user-name");
    const editEmail = document.getElementById("edit-user-email");
    const editRole = document.getElementById("edit-user-role");
    const deleteText = document.getElementById("delete-user-text");

    document.querySelectorAll("[data-open-edit]").forEach(function (button) {
      button.addEventListener("click", function () {
        if (editName) editName.value = button.getAttribute("data-name") || "";
        if (editEmail) editEmail.value = button.getAttribute("data-email") || "";
        if (editRole) editRole.value = button.getAttribute("data-role") || "client";
        openModal(editModal);
      });
    });

    document.querySelectorAll("[data-open-delete]").forEach(function (button) {
      button.addEventListener("click", function () {
        const name = button.getAttribute("data-name") || "this user";
        if (deleteText) {
          deleteText.textContent = "Are you sure you want to delete " + name + "?";
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

    const confirmDelete = document.querySelector("[data-confirm-delete]");
    if (confirmDelete) {
      confirmDelete.addEventListener("click", function () {
        closeModal(deleteModal);
      });
    }

    const editForm = editModal ? editModal.querySelector("form") : null;
    if (editForm) {
      editForm.addEventListener("submit", function (event) {
        event.preventDefault();
        closeModal(editModal);
      });
    }
  }

  function initApprovalActions() {
    document.querySelectorAll("[data-approval-action]").forEach(function (button) {
      button.addEventListener("click", function () {
        const row = button.closest("tr");
        if (!row) return;

        const approved = button.getAttribute("data-approval-action") === "approve";
        row.style.opacity = "0.45";
        const cell = row.querySelector(".actions-cell");
        if (cell) {
          cell.innerHTML = approved
            ? '<span class="badge confirmed">Approved</span>'
            : '<span class="badge rejected">Rejected</span>';
        }
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    togglePopover();
    initFilterButtons();
    initUserModals();
    initApprovalActions();
  });
})();
