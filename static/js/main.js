/* ShareSplit Rent — UI interactions (vanilla JS, no dependencies). */
(function () {
  'use strict';

  // Mobile navigation toggle.
  var navToggle = document.getElementById('nav-toggle');
  var nav = document.getElementById('site-nav');
  if (navToggle && nav) {
    navToggle.addEventListener('click', function () {
      var isOpen = nav.classList.toggle('open');
      navToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });
  }

  // Account dropdown menu.
  var userMenu = document.getElementById('user-menu');
  var userTrigger = document.getElementById('user-menu-trigger');
  if (userMenu && userTrigger) {
    userTrigger.addEventListener('click', function (e) {
      e.stopPropagation();
      var isOpen = userMenu.classList.toggle('open');
      userTrigger.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });
    document.addEventListener('click', function (e) {
      if (!userMenu.contains(e.target)) {
        userMenu.classList.remove('open');
        userTrigger.setAttribute('aria-expanded', 'false');
      }
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        userMenu.classList.remove('open');
        userTrigger.setAttribute('aria-expanded', 'false');
      }
    });
  }

  // Flash messages: manual close + auto-dismiss.
  document.querySelectorAll('.alert').forEach(function (alert) {
    var close = alert.querySelector('.alert-close');
    function dismiss() {
      alert.style.transition = 'opacity 0.35s ease, transform 0.35s ease';
      alert.style.opacity = '0';
      alert.style.transform = 'translateY(-6px)';
      setTimeout(function () { alert.remove(); }, 380);
    }
    if (close) close.addEventListener('click', dismiss);
  });

  // Password visibility toggles.
  document.querySelectorAll('[data-password-toggle]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var input = document.getElementById(btn.getAttribute('data-password-toggle'));
      if (!input) return;
      var show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      btn.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
      btn.innerHTML = show ? btn.dataset.iconOff : btn.dataset.iconOn;
    });
  });

  // Room detail gallery: thumbnail switches the main image.
  var galleryMain = document.getElementById('gallery-main-img');
  if (galleryMain) {
    document.querySelectorAll('.gallery-thumbs button').forEach(function (thumb) {
      thumb.addEventListener('click', function () {
        galleryMain.src = thumb.dataset.full;
        galleryMain.alt = thumb.dataset.caption || galleryMain.alt;
        document.querySelectorAll('.gallery-thumbs button').forEach(function (t) {
          t.classList.remove('active');
          t.setAttribute('aria-pressed', 'false');
        });
        thumb.classList.add('active');
        thumb.setAttribute('aria-pressed', 'true');
      });
    });
  }

  // Sort select submits its form immediately.
  document.querySelectorAll('[data-auto-submit]').forEach(function (el) {
    el.addEventListener('change', function () { el.form.submit(); });
  });

  // Mobile filter panel toggle.
  var filterToggle = document.getElementById('filter-toggle');
  var filterPanel = document.getElementById('filter-panel');
  if (filterToggle && filterPanel) {
    filterToggle.addEventListener('click', function () {
      var isOpen = filterPanel.classList.toggle('open');
      filterToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });
  }

  // Confirmation modal for destructive actions (data-confirm on forms/buttons).
  var overlay = document.getElementById('confirm-modal');
  if (overlay) {
    var modalTitle = overlay.querySelector('[data-modal-title]');
    var modalText = overlay.querySelector('[data-modal-text]');
    var modalOk = overlay.querySelector('[data-modal-ok]');
    var pendingForm = null;
    var previousFocus = null;
    var previousOverflow = '';
    overlay.setAttribute('aria-hidden', 'true');

    document.querySelectorAll('form[data-confirm]').forEach(function (form) {
      form.addEventListener('submit', function (e) {
        if (form.dataset.confirmed === '1') return;
        e.preventDefault();
        pendingForm = form;
        modalTitle.textContent = form.dataset.confirmTitle || 'Are you sure?';
        modalText.textContent = form.dataset.confirm;
        modalOk.textContent = form.dataset.confirmOk || 'Confirm';
        previousFocus = document.activeElement;
        previousOverflow = document.body.style.overflow;
        document.body.style.overflow = 'hidden';
        overlay.classList.add('open');
        overlay.setAttribute('aria-hidden', 'false');
        modalOk.focus();
      });
    });

    function closeModal() {
      if (!overlay.classList.contains('open')) return;
      overlay.classList.remove('open');
      overlay.setAttribute('aria-hidden', 'true');
      document.body.style.overflow = previousOverflow;
      pendingForm = null;
      if (previousFocus) previousFocus.focus();
    }
    overlay.querySelector('[data-modal-cancel]').addEventListener('click', closeModal);
    overlay.addEventListener('click', function (e) { if (e.target === overlay) closeModal(); });
    document.addEventListener('keydown', function (e) {
      if (!overlay.classList.contains('open')) return;
      if (e.key === 'Escape') closeModal();
      if (e.key === 'Tab') {
        var focusable = overlay.querySelectorAll('button, a[href], input, select, textarea');
        var first = focusable[0];
        var last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    });
    modalOk.addEventListener('click', function () {
      if (pendingForm) {
        pendingForm.dataset.confirmed = '1';
        pendingForm.submit();
      }
      closeModal();
    });
  }

})();