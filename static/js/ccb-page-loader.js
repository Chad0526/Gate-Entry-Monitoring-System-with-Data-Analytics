/**
 * Full-page loader is used only for the first paint after login → dashboard/analytics
 * (server sets ccb_post_login_loader; overlay starts visible, then hides on window "load").
 * Sidebar and in-app navigation do not show this overlay (no click/submit handlers).
 */
(function () {
  'use strict';

  var el = null;

  function getEl() {
    if (!el) el = document.getElementById('ccb-page-loader');
    return el;
  }

  function hide() {
    var e = getEl();
    if (e) {
      e.classList.add('ccb-page-loader--hidden');
      e.setAttribute('aria-busy', 'false');
    }
  }

  function show() {
    var e = getEl();
    if (e) {
      e.classList.remove('ccb-page-loader--hidden');
      e.setAttribute('aria-busy', 'true');
    }
  }

  window.ccbHidePageLoader = hide;
  window.ccbShowPageLoader = show;

  window.addEventListener('load', hide);
  window.addEventListener('pageshow', function (ev) {
    if (ev.persisted) hide();
  });
})();
