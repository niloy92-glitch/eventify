const DEMO_CREDENTIALS = {
  client: { username: "client", password: "1" },
  vendor: { username: "vendor", password: "1" },
  admin: { username: "admin", password: "1" },
};

const REQUEST_KEY = "eventify_requested_services";
const APPROVED_VENDOR_KEY = "eventify_approved_vendors";

function getSession() {
  const raw = localStorage.getItem("eventify_session");
  return raw ? JSON.parse(raw) : null;
}

function setSession(role, username) {
  localStorage.setItem(
    "eventify_session",
    JSON.stringify({ role, username, loginAt: new Date().toISOString() }),
  );
}

function clearSession() {
  localStorage.removeItem("eventify_session");
}

function getList(key) {
  const raw = localStorage.getItem(key);
  return raw ? JSON.parse(raw) : [];
}

function setList(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

function addRequestedService(serviceId) {
  const current = getList(REQUEST_KEY);
  if (!current.includes(serviceId)) {
    current.push(serviceId);
    setList(REQUEST_KEY, current);
  }
}

function hasRequestedAnyService() {
  return getList(REQUEST_KEY).length > 0;
}

function approveVendor(vendorId) {
  const approved = getList(APPROVED_VENDOR_KEY);
  if (!approved.includes(vendorId)) {
    approved.push(vendorId);
    setList(APPROVED_VENDOR_KEY, approved);
  }
}

function isVendorApproved(vendorId) {
  return getList(APPROVED_VENDOR_KEY).includes(vendorId);
}

function initTabs() {
  const tabGroups = document.querySelectorAll("[data-tab-group]");
  tabGroups.forEach((group) => {
    const container = group.closest(".card") || group.parentElement;
    const buttons = group.querySelectorAll(".tab-btn");
    const panels = container.querySelectorAll(".panel");

    buttons.forEach((button) => {
      button.addEventListener("click", () => {
        const selected = button.getAttribute("data-tab");
        buttons.forEach((item) => item.classList.remove("active"));
        panels.forEach((panel) => panel.classList.remove("active"));
        button.classList.add("active");
        const target = container.querySelector(`#${selected}`);
        if (target) target.classList.add("active");
      });
    });
  });
}

function initDropdowns() {
  const toggles = document.querySelectorAll("[data-dropdown-btn]");
  toggles.forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      const targetId = button.dataset.dropdownBtn;
      const dropdown = button.closest(".dropdown");
      document.querySelectorAll(".dropdown").forEach((item) => {
        if (item !== dropdown) item.classList.remove("open");
      });
      if (dropdown && document.getElementById(targetId)) {
        dropdown.classList.toggle("open");
      }
    });
  });

  document.addEventListener("click", () => {
    document.querySelectorAll(".dropdown").forEach((item) => {
      item.classList.remove("open");
    });
  });
}

function initLogoutButtons() {
  document.querySelectorAll("[data-logout]").forEach((button) => {
    button.addEventListener("click", () => {
      clearSession();
      window.location.href = "login.html";
    });
  });
}

function initRoleSidebar() {
  const role = document.body.dataset.requireRole;
  if (!role) return;

  const navInner = document.querySelector(".navbar .nav-inner");
  if (!navInner) return;

  const session = getSession();
  const currentPage = window.location.pathname.split("/").pop();

  const menuByRole = {
    client: [
      ["dashboard-client.html", "Dashboard"],
      ["create-event.html", "Create Event"],
      ["client-events.html", "My Events"],
      ["client-messages.html", "Messages"],
      ["profile-client.html", "Profile"],
    ],
    vendor: [
      ["dashboard-vendor.html", "Dashboard"],
      ["vendor-services.html", "Services"],
      ["vendor-events.html", "My Events"],
      ["vendor-messages.html", "Messages"],
    ],
    admin: [
      ["dashboard-admin.html", "Dashboard"],
      ["admin-users.html", "Users"],
      ["admin-vendors.html", "Vendors"],
    ],
  };

  const roleMeta = {
    client: { initials: "CL", label: "Client" },
    vendor: { initials: "VD", label: "Vendor" },
    admin: { initials: "AD", label: "Admin" },
  };

  const notificationsByRole = {
    client: [
      "Photographer accepted your request.",
      "New message from Tasty Bites.",
      "Venue quote was updated.",
    ],
    vendor: [
      "You received 2 new client messages.",
      "Service request is waiting for confirmation.",
      "Client approved your quotation.",
    ],
    admin: [
      "Two new vendor approvals are pending.",
      "A user reported profile verification issue.",
      "Daily platform summary is ready.",
    ],
  };

  const links = menuByRole[role] || [];
  const meta = roleMeta[role] || roleMeta.client;
  const displayName = session?.username
    ? session.username.charAt(0).toUpperCase() + session.username.slice(1)
    : `${meta.label} User`;

  const linkHtml = links
    .map(([href, label]) => {
      const activeClass = currentPage === href ? " active" : "";
      return `<a class="nav-link${activeClass}" href="${href}">${label}</a>`;
    })
    .join("");

  const notifMenuId = `notif-menu-${role}`;
  const notifItems = (notificationsByRole[role] || [])
    .map((item) => `<p>${item}</p>`)
    .join("");

  navInner.innerHTML = `
    <a class="logo-link" href="${links[0]?.[0] || "index.html"}">Event<span>ify</span></a>
    <section class="sidebar-user" aria-label="Current user">
      <div class="sidebar-user-avatar" aria-hidden="true">${meta.initials}</div>
      <div>
        <p class="sidebar-user-name">${displayName}</p>
        <p class="sidebar-user-role">${meta.label}</p>
      </div>
    </section>
    <nav class="nav-links nav-center">${linkHtml}</nav>
    <div class="nav-tools">
      <div class="dropdown">
        <button class="icon-btn" type="button" data-dropdown-btn="${notifMenuId}">Notifications</button>
        <div class="dropdown-menu" id="${notifMenuId}">${notifItems}</div>
      </div>
      <button class="btn" type="button" data-logout>Logout</button>
    </div>
  `;
}

function initLoginSimulation() {
  const loginForms = document.querySelectorAll("form[data-role]");
  if (!loginForms.length) return;

  loginForms.forEach((form) => {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const role = form.dataset.role;
      const usernameInput = form.querySelector('input[type="text"]');
      const passInput = form.querySelector('input[type="password"]');
      const status = form.querySelector(".status-text");
      const username = usernameInput
        ? usernameInput.value.trim().toLowerCase()
        : "";
      const password = passInput ? passInput.value.trim() : "";
      const expected = DEMO_CREDENTIALS[role];

      if (
        expected &&
        username === expected.username &&
        password === expected.password
      ) {
        setSession(role, username);
        if (status) status.textContent = "Login successful. Redirecting...";
        if (role === "client") window.location.href = "dashboard-client.html";
        if (role === "vendor") window.location.href = "dashboard-vendor.html";
        if (role === "admin") window.location.href = "dashboard-admin.html";
      } else {
        if (status) {
          status.textContent = `Invalid ${role} credentials. Use ${expected.username} / ${expected.password}`;
        }
      }
    });
  });
}

function initRegisterSimulation() {
  const registerForms = document.querySelectorAll("form[data-register-role]");
  registerForms.forEach((form) => {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const role = form.dataset.registerRole;
      const status = form.querySelector(".status-text");
      if (status) {
        const demo = DEMO_CREDENTIALS[role];
        status.textContent = `Registration simulated. Please login with fixed demo: ${demo.username} / ${demo.password}`;
      }
    });
  });
}

function protectPage() {
  const requiredRole = document.body.dataset.requireRole;
  if (!requiredRole) return;

  const session = getSession();
  if (!session || session.role !== requiredRole) {
    window.location.href = "login.html";
  }
}

function fillCurrentDate() {
  const dateText = new Date().toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
  document.querySelectorAll("[data-current-date]").forEach((el) => {
    el.textContent = dateText;
  });
}

function bindProtectedActions() {
  const actions = document.querySelectorAll("[data-action]");
  actions.forEach((button) => {
    button.addEventListener("click", () => {
      const role = button.dataset.requiresRole;
      const session = getSession();
      const statusTargetId = button.dataset.statusTarget;
      const status = statusTargetId
        ? document.getElementById(statusTargetId)
        : null;

      if (role && (!session || session.role !== role)) {
        if (status) status.textContent = `Please login as ${role} to continue.`;
        return;
      }

      const action = button.dataset.action;
      if (status) status.textContent = `${action} completed (simulation).`;
    });
  });
}

function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.add("open");
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove("open");
}

function initModals() {
  document.querySelectorAll("[data-close-modal]").forEach((button) => {
    button.addEventListener("click", () => {
      closeModal(button.dataset.closeModal);
    });
  });

  document.querySelectorAll(".modal").forEach((modal) => {
    modal.addEventListener("click", (event) => {
      if (event.target === modal) modal.classList.remove("open");
    });
  });
}

function initEventInfoModal() {
  const triggers = document.querySelectorAll("[data-open-event-modal]");
  if (!triggers.length) return;

  triggers.forEach((card) => {
    card.addEventListener("click", () => {
      const title = card.dataset.eventTitle || "Event";
      const date = card.dataset.eventDate || "-";
      const location = card.dataset.eventLocation || "-";
      const services = card.dataset.eventServices || "-";
      const status = card.dataset.eventStatus || "-";

      const byId = (id) => document.getElementById(id);
      if (byId("modal-event-title")) byId("modal-event-title").textContent = title;
      if (byId("modal-event-date")) byId("modal-event-date").textContent = date;
      if (byId("modal-event-location")) {
        byId("modal-event-location").textContent = location;
      }
      if (byId("modal-event-services")) byId("modal-event-services").textContent = services;
      if (byId("modal-event-status")) byId("modal-event-status").textContent = status;
      openModal("event-info-modal");
    });
  });
}

function initCreateEventFlow() {
  const stages = [...document.querySelectorAll(".stage[data-stage]")];
  if (!stages.length) return;

  let current = 1;
  const stageCount = stages.length;
  const stepLabels = [...document.querySelectorAll(".stepper .step")];

  const renderStage = () => {
    stages.forEach((stage) => {
      stage.classList.toggle("active", Number(stage.dataset.stage) === current);
    });
    stepLabels.forEach((step, index) => {
      step.classList.toggle("active", index + 1 === current);
    });
  };

  document.querySelector("[data-stage-next]")?.addEventListener("click", () => {
    if (current < stageCount) current += 1;
    renderStage();
  });

  document.querySelector("[data-stage-prev]")?.addEventListener("click", () => {
    if (current > 1) current -= 1;
    renderStage();
  });

  const addressInput = document.querySelector("[data-venue-address]");
  const venueOptions = document.querySelector("[data-venue-options]");
  const modeRadios = document.querySelectorAll("[data-venue-mode]");

  const updateVenueMode = () => {
    const mode = [...modeRadios].find((r) => r.checked)?.value || "need";
    const hasVenue = mode === "has";
    if (addressInput) addressInput.disabled = !hasVenue;
    if (venueOptions) venueOptions.style.opacity = hasVenue ? "0.5" : "1";
    venueOptions?.querySelectorAll("button").forEach((btn) => {
      btn.disabled = hasVenue;
    });
  };

  modeRadios.forEach((radio) => {
    radio.addEventListener("change", updateVenueMode);
  });
  updateVenueMode();

  const venueTitle = document.getElementById("venue-modal-title");
  document.querySelectorAll("[data-open-venue-modal]").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (venueTitle) {
        venueTitle.textContent = `${btn.dataset.serviceName} - Venue Details`;
      }
      openModal("venue-modal");
    });
  });

  document.querySelector("[data-select-venue]")?.addEventListener("click", () => {
    addRequestedService("venue-service");
    closeModal("venue-modal");
  });

  document.querySelector("[data-open-service-modal]")?.addEventListener("click", () => {
    openModal("service-modal");
  });

  renderStage();
}

function initServiceRequests() {
  document.querySelectorAll("[data-request-service]").forEach((btn) => {
    if (btn.dataset.boundRequest === "1") return;
    btn.dataset.boundRequest = "1";

    btn.addEventListener("click", () => {
      const id = btn.dataset.requestService;
      addRequestedService(id);
      btn.textContent = "Requested";
      btn.disabled = true;

      const specificStatusId = btn.dataset.statusTarget;
      const status = specificStatusId
        ? document.getElementById(specificStatusId)
        : document.getElementById("selected-services-status") ||
          document.getElementById("book-status");

      if (status) {
        status.textContent = "Service request submitted. Status: pending confirmation.";
      }
    });
  });
}

function initMessageGate() {
  const gate = document.querySelector("[data-message-gate]");
  if (!gate) return;

  const canMessage = hasRequestedAnyService();
  const input = gate.querySelector("[data-message-input]");
  const sendBtn = gate.querySelector("[data-send-message]");
  const status = gate.querySelector("[data-message-status]");

  if (input) input.disabled = !canMessage;
  if (sendBtn) sendBtn.disabled = !canMessage;
  if (status) {
    status.textContent = canMessage
      ? "Messaging is enabled because at least one service was requested."
      : "Messaging is locked. Request a service first.";
  }

  sendBtn?.addEventListener("click", () => {
    if (status) status.textContent = "Message sent (simulation).";
  });
}

function initDynamicChats() {
  document.querySelectorAll(".message-workspace").forEach((workspace) => {
    const chatItems = [...workspace.querySelectorAll("[data-chat-item]")];
    if (!chatItems.length) return;

    const threadName = workspace.querySelector("[data-thread-name]");
    const threadSubtitle = workspace.querySelector("[data-thread-subtitle]");
    const threadAvatar = workspace.querySelector("[data-thread-avatar]");
    const threadBody = workspace.querySelector("[data-thread-body]");

    const activateChat = (item) => {
      chatItems.forEach((chatItem) => {
        chatItem.classList.toggle("active", chatItem === item);
      });

      if (threadName) threadName.textContent = item.dataset.chatName || "";
      if (threadSubtitle) threadSubtitle.textContent = item.dataset.chatSubtitle || "";
      if (threadAvatar) threadAvatar.textContent = item.dataset.chatAvatar || "";

      const template = item.querySelector(".chat-thread-template");
      if (threadBody && template) {
        threadBody.innerHTML = template.innerHTML.trim();
      }
    };

    chatItems.forEach((item) => {
      item.addEventListener("click", () => activateChat(item));
    });

    activateChat(chatItems.find((item) => item.classList.contains("active")) || chatItems[0]);
  });
}

function initFilters() {
  document.querySelectorAll("[data-filter-group]").forEach((group) => {
    const list = group.parentElement?.querySelector("[data-filter-list]");
    if (!list) return;

    const chips = group.querySelectorAll("[data-filter]");
    const cards = list.querySelectorAll("[data-status]");
    chips.forEach((chip) => {
      chip.addEventListener("click", () => {
        const filter = chip.dataset.filter;
        chips.forEach((c) => c.classList.remove("active"));
        chip.classList.add("active");

        cards.forEach((card) => {
          const matches = filter === "all" || card.dataset.status === filter;
          card.style.display = matches ? "block" : "none";
        });
      });
    });
  });
}

function initProfileActions() {
  document.querySelector("[data-save-profile]")?.addEventListener("click", () => {
    const targetId = document.querySelector("[data-save-profile]")?.dataset.statusTarget;
    const status = targetId ? document.getElementById(targetId) : null;
    if (status) status.textContent = "Profile changes saved (simulation).";
  });

  document.querySelector("[data-delete-account]")?.addEventListener("click", () => {
    clearSession();
    localStorage.removeItem(REQUEST_KEY);
    window.location.href = "login.html";
  });
}

function initVendorApproval() {
  document.querySelectorAll("[data-approve-vendor]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const vendorId = btn.dataset.approveVendor;
      approveVendor(vendorId);
      updateVendorApprovalUI();
    });
  });

  updateVendorApprovalUI();
}

function updateVendorApprovalUI() {
  document.querySelectorAll("[data-vendor-status]").forEach((el) => {
    const vendorId = el.dataset.vendorStatus;
    if (isVendorApproved(vendorId)) {
      el.textContent = "Approved";
      el.classList.remove("pending");
      el.classList.add("confirmed");
    }
  });

  document.querySelectorAll("[data-vendor-check]").forEach((el) => {
    const vendorId = el.dataset.vendorCheck;
    el.textContent = isVendorApproved(vendorId) ? "✔" : "";
  });
}

function injectSessionUI() {
  const session = getSession();
  const target = document.querySelector("[data-session-bar]");
  if (!target) return;

  if (!session) {
    target.innerHTML = '<a class="btn" href="login.html">Login to Continue</a>';
    return;
  }

  target.innerHTML = `<span class="muted">Logged in as ${session.role}</span> <button class="btn" id="logout-btn" type="button">Logout</button>`;
  const logoutBtn = document.getElementById("logout-btn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", () => {
      clearSession();
      window.location.href = "login.html";
    });
  }
}

document.addEventListener("DOMContentLoaded", () => {
  protectPage();
  initRoleSidebar();
  fillCurrentDate();
  initTabs();
  initDropdowns();
  initLogoutButtons();
  initModals();
  initLoginSimulation();
  initRegisterSimulation();
  initEventInfoModal();
  initCreateEventFlow();
  initServiceRequests();
  initFilters();
  initDynamicChats();
  initMessageGate();
  initProfileActions();
  initVendorApproval();
  bindProtectedActions();
  injectSessionUI();
});
