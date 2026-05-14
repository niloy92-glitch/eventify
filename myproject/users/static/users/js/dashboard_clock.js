(function () {
  function formatClock(date) {
    const hours = String(date.getHours()).padStart(2, "0");
    const minutes = String(date.getMinutes()).padStart(2, "0");
    const seconds = String(date.getSeconds()).padStart(2, "0");
    return hours + ":" + minutes + ":" + seconds;
  }

  function updateClock() {
    const nodes = document.querySelectorAll("#dashboard-clock");
    if (!nodes.length) return;

    const value = formatClock(new Date());
    nodes.forEach(function (node) {
      node.textContent = value;
    });
  }

  function initClock() {
    updateClock();
    window.setInterval(updateClock, 1000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initClock);
  } else {
    initClock();
  }
})();