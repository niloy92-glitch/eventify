(function () {
  function getBodyData(name) {
    return document.body ? document.body.getAttribute(name) || "" : "";
  }

  function getCsrfToken() {
    const cookie = document.cookie.split("; ").find(function (item) {
      return item.indexOf("csrftoken=") === 0;
    });
    return cookie ? decodeURIComponent(cookie.split("=")[1]) : "";
  }

  function createNotificationItem(notification) {
    const li = document.createElement("li");
    li.className = "notification-item" + (notification.is_seen ? "" : " notification-item-unseen");

    const wrapper = notification.link_url ? document.createElement("a") : document.createElement("div");
    wrapper.className = "notification-link";
    if (notification.link_url) {
      wrapper.href = notification.link_url;
    }

    const top = document.createElement("div");
    top.className = "notification-item-top";

    const title = document.createElement("span");
    title.className = "notification-item-title";
    title.textContent = notification.title || "Notification";

    const time = document.createElement("span");
    time.className = "notification-item-time";
    time.textContent = notification.created_at_label || "";

    const message = document.createElement("p");
    message.className = "notification-item-message";
    message.textContent = notification.message || "";

    top.appendChild(title);
    top.appendChild(time);
    wrapper.appendChild(top);
    wrapper.appendChild(message);
    li.appendChild(wrapper);
    return li;
  }

  function getNotificationNodes() {
    return {
      button: document.getElementById("notification-toggle"),
      popover: document.getElementById("notification-popover"),
      badge: document.getElementById("notification-badge"),
      list: document.getElementById("notification-list"),
      markRead: document.getElementById("notification-mark-read"),
    };
  }

  function updateBadge(count) {
    const nodes = getNotificationNodes();
    if (!nodes.badge) return;

    const nextCount = Number(count || 0);
    nodes.badge.textContent = String(nextCount);
    nodes.badge.hidden = nextCount <= 0;
  }

  function renderNotifications(items) {
    const nodes = getNotificationNodes();
    if (!nodes.list) return;

    nodes.list.innerHTML = "";
    const notifications = Array.isArray(items) ? items : [];

    if (!notifications.length) {
      const emptyItem = document.createElement("li");
      emptyItem.className = "notification-empty";
      emptyItem.textContent = "No notifications yet.";
      nodes.list.appendChild(emptyItem);
      return;
    }

    notifications.forEach(function (notification) {
      nodes.list.appendChild(createNotificationItem(notification));
    });
  }

  function playTwing() {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) return;

    try {
      const audioContext = new AudioContextClass();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();

      oscillator.type = "sine";
      oscillator.frequency.value = 880;
      gainNode.gain.value = 0.03;

      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);
      oscillator.start();
      oscillator.stop(audioContext.currentTime + 0.12);
    } catch (error) {
      // Ignore audio failures on browsers that block it.
    }
  }

  function initNotifications() {
    const nodes = getNotificationNodes();
    const feedUrl = getBodyData("data-notification-feed-url");
    const markSeenUrl = getBodyData("data-notification-mark-seen-url");
    let lastCount = Number(getBodyData("data-notification-initial-unseen") || 0);
    let soundArmed = false;

    if (!nodes.button || !nodes.popover || !feedUrl || !nodes.list) {
      return;
    }

    function closePopover() {
      nodes.popover.hidden = true;
      nodes.button.setAttribute("aria-expanded", "false");
    }

    function openPopover() {
      nodes.popover.hidden = false;
      nodes.button.setAttribute("aria-expanded", "true");
    }

    function fetchNotifications(allowSound) {
      return fetch(feedUrl, {
        credentials: "same-origin",
        headers: { "X-Requested-With": "XMLHttpRequest" },
      })
        .then(function (response) {
          if (!response.ok) {
            throw new Error("Unable to load notifications");
          }
          return response.json();
        })
        .then(function (data) {
          const nextCount = Number(data.notification_unseen_count || 0);
          renderNotifications(data.notification_items || []);
          updateBadge(nextCount);

          if (allowSound && soundArmed && nextCount > lastCount) {
            playTwing();
          }

          lastCount = nextCount;
        })
        .catch(function () {
          // Keep the existing UI if the request fails.
        });
    }

    function markAllSeen() {
      if (!markSeenUrl) {
        return Promise.resolve();
      }

      return fetch(markSeenUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "X-CSRFToken": getCsrfToken(),
          "X-Requested-With": "XMLHttpRequest",
        },
      }).then(function () {
        lastCount = 0;
        updateBadge(0);
        return fetchNotifications(false);
      });
    }

    nodes.button.addEventListener("click", function (event) {
      event.stopPropagation();
      soundArmed = true;
      if (nodes.popover.hidden) {
        openPopover();
        markAllSeen();
      } else {
        closePopover();
      }
    });

    if (nodes.markRead) {
      nodes.markRead.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        markAllSeen();
      });
    }

    document.addEventListener("click", function (event) {
      if (!nodes.popover.hidden && !nodes.popover.contains(event.target) && event.target !== nodes.button) {
        closePopover();
      }
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        closePopover();
      }
    });

    document.addEventListener("pointerdown", function () {
      soundArmed = true;
    }, { once: true });

    renderNotifications([]);
    updateBadge(lastCount);
    fetchNotifications(false);
    window.setInterval(function () {
      fetchNotifications(true);
    }, 30000);
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

  // Make these global so other scripts can access them
  window.openModal = function (modal) {
    if (!modal) return;
    modal.classList.add("open");
    modal.setAttribute("aria-hidden", "false");
  };

  window.closeModal = function (modal) {
    if (!modal) return;
    modal.classList.remove("open");
    modal.setAttribute("aria-hidden", "true");
  };

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
    initNotifications();
    initFilterButtons();
    initUserModals();
    initProfileModals();
    initApprovalActions();
  });
})();
