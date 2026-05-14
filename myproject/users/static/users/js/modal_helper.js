(function () {
  function showModal(modal) {
    if (!modal) return;
    modal.classList.add('open');
    modal.removeAttribute('hidden');
    modal.setAttribute('aria-hidden', 'false');
    modal.removeAttribute('inert');
  }

  function hideModal(modal) {
    if (!modal) return;
    modal.classList.remove('open');
    modal.setAttribute('hidden', '');
    modal.setAttribute('aria-hidden', 'true');
    modal.setAttribute('inert', 'inert');
    // reset forms inside modal to avoid stale state
    modal.querySelectorAll('form').forEach(function (f) {
      try { f.reset(); } catch (e) {}
    });
  }

  window.openModal = function (modalOrId) {
    var modal = typeof modalOrId === 'string' ? document.getElementById(modalOrId) : modalOrId;
    showModal(modal);
  };

  window.closeModal = function (modalOrId) {
    var modal = typeof modalOrId === 'string' ? document.getElementById(modalOrId) : modalOrId;
    hideModal(modal);
  };

  document.addEventListener('click', function (ev) {
    var openTarget = ev.target.closest('[data-open-modal]');
    if (openTarget) {
      ev.preventDefault();
      var id = openTarget.getAttribute('data-open-modal') || openTarget.getAttribute('data-open-event-edit') || openTarget.getAttribute('data-open-create-event');
      if (id) {
        var modal = document.getElementById(id);
        if (modal) showModal(modal);
      } else if (openTarget.hasAttribute('data-open-event-edit')) {
        var edit = document.getElementById('event-edit-modal');
        if (edit) showModal(edit);
      }
      return;
    }

    var closeTarget = ev.target.closest('[data-close-modal], .modal-close, .modal-close-btn');
    if (closeTarget) {
      ev.preventDefault();
      var closeId = closeTarget.getAttribute('data-close-modal');
      if (closeId) {
        var modal = document.getElementById(closeId);
        if (modal) hideModal(modal);
      } else {
        var modal = closeTarget.closest('.modal');
        if (modal) hideModal(modal);
      }
      return;
    }

    // clicking on modal overlay to close
    if (ev.target.classList && ev.target.classList.contains('modal')) {
      var m = ev.target;
      hideModal(m);
    }
  }, true);

  document.addEventListener('keydown', function (ev) {
    if (ev.key === 'Escape') {
      document.querySelectorAll('.modal.open').forEach(function (m) { hideModal(m); });
    }
  });

  // Allow other scripts to request opening a modal via a global flag
  if (window.__openEventCompletionModal && window.__openEventCompletionModal.eventId) {
    // prefer the dedicated eventCompletionModal if present
    if (window.eventCompletionModal && typeof window.eventCompletionModal.open === 'function') {
      try {
        window.eventCompletionModal.open(
          window.__openEventCompletionModal.eventId,
          window.__openEventCompletionModal.eventTitle,
          window.__openEventCompletionModal.eventDate,
          window.__openEventCompletionModal.services || []
        );
      } catch (e) {
        var modal = document.getElementById('event-completion-modal');
        if (modal) showModal(modal);
      }
    } else {
      var modal = document.getElementById('event-completion-modal');
      if (modal) showModal(modal);
    }
    window.__openEventCompletionModal = null;
  }

})();
