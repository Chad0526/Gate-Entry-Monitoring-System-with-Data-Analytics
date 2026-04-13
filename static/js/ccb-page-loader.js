/**
 * Shows a centered in-page loader while the document or next navigation loads.
 * Hides when window "load" fires; shows again on same-origin link clicks and GET form submits.
 * (Browsers may still show tab activity — this is normal for full navigations.)
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

  /* Bubble phase (not capture): runs after sidebar-nav-ajax.js so SPA links can preventDefault first. */
  document.addEventListener(
    'click',
    function (e) {
      var a = e.target.closest('a[href]');
      if (!a) return;
      var href = (a.getAttribute('href') || '').trim();
      if (!href || href === '#' || href.indexOf('javascript:') === 0) return;
      if (a.target === '_blank' || a.hasAttribute('download')) return;
      if (e.defaultPrevented) return;
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      if (a.hasAttribute('data-no-page-loader')) return;
      if (a.getAttribute('data-toggle')) return;
      if (a.getAttribute('data-widget')) return;
      if (a.closest('[data-toggle="dropdown"]')) return;
      if (a.closest('.dropdown-menu')) return;
      if (a.closest('.modal')) return;
      try {
        var u = new URL(a.href, window.location.href);
        if (u.origin !== window.location.origin) return;
        var curBase = window.location.href.split('#')[0];
        var nextBase = u.href.split('#')[0];
        if (curBase === nextBase && u.hash) return;
      } catch (err) {
        return;
      }
      show();
    },
    false
  );

  /* GET + AJAX: handlers should call preventDefault() on the form, and/or set data-no-page-loader="1"
     on the form so this overlay does not block the in-page fetch UX. */
  document.addEventListener('submit', function (e) {
    if (e.defaultPrevented) return;
    var f = e.target;
    if (!f || f.tagName !== 'FORM') return;
    if (f.getAttribute('data-no-page-loader') === '1') return;
    if (f.target && f.target !== '' && f.target !== '_self') return;
    var m = (f.getAttribute('method') || 'get').toLowerCase();
    if (m === 'get') show();
  });
})();
