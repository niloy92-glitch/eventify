(function () {
  function ensureWrap() {
    let wrap = document.querySelector(".toast-wrap");
    if (!wrap) {
      wrap = document.createElement("div");
      wrap.className = "toast-wrap";
      document.body.appendChild(wrap);
    }
    return wrap;
  }

  function show(message, level = "info", duration = 3600) {
    if (!message) {
      return;
    }
    const wrap = ensureWrap();
    const toast = document.createElement("div");
    toast.className = `toast toast-${level}`;
    toast.textContent = message;
    wrap.appendChild(toast);

    requestAnimationFrame(() => {
      toast.classList.add("show");
    });

    window.setTimeout(() => {
      toast.classList.remove("show");
      window.setTimeout(() => toast.remove(), 200);
    }, duration);
  }

  function fromQuery() {
    const url = new URL(window.location.href);
    const message = url.searchParams.get("auth_message");
    const level = url.searchParams.get("auth_level") || "info";
    if (message) {
      show(message, level);
      url.searchParams.delete("auth_message");
      url.searchParams.delete("auth_level");
      window.history.replaceState({}, "", url.toString());
    }
  }

  window.EventifyToast = { show, fromQuery };
})();
