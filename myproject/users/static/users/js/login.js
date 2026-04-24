function initLoginForms() {
  const form = document.getElementById("login-form");
  if (!form) return;

  const tabButtons = form.querySelectorAll(".auth-tab[data-role]");
  const roleInput = document.getElementById("login-role");

  tabButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const selectedRole = button.getAttribute("data-role");
      if (!selectedRole || !roleInput) {
        return;
      }

      roleInput.value = selectedRole;
      tabButtons.forEach((tab) => {
        const isActive = tab === button;
        tab.classList.toggle("active", isActive);
        tab.setAttribute("aria-selected", String(isActive));
      });
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initLoginForms();
});
