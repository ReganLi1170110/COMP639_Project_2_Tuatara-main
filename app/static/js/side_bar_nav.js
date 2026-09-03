document.addEventListener('DOMContentLoaded', function () {
    var mobileQuery = window.matchMedia('(max-width: 991.98px)');
    var body = document.body;
    var panel = document.getElementById('sidebar-panel');
    var toggle = document.getElementById('sidebar-mobile-toggle');
    var backdrop = document.getElementById('sidebar-mobile-backdrop');

    if (!panel || !toggle || !backdrop) {
      return;
    }

    function closeMenu() {
      body.classList.remove('sidebar-mobile-open');
      toggle.setAttribute('aria-expanded', 'false');
    }

    function openMenu() {
      body.classList.add('sidebar-mobile-open');
      toggle.setAttribute('aria-expanded', 'true');
    }

    toggle.addEventListener('click', function () {
      if (!mobileQuery.matches) {
        return;
      }
      if (body.classList.contains('sidebar-mobile-open')) {
        closeMenu();
      } else {
        openMenu();
      }
    });

    backdrop.addEventListener('click', closeMenu);

    panel.addEventListener('click', function (event) {
      if (!mobileQuery.matches) {
        return;
      }
      if (event.target.closest('a')) {
        closeMenu();
      }
    });

    window.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') {
        closeMenu();
      }
    });

    mobileQuery.addEventListener('change', function (event) {
      if (!event.matches) {
        closeMenu();
      }
    });
  });