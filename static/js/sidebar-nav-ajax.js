/**
 * In-app navigation: fetch HTML and swap .content-wrapper + sidebar nav (no full document reload).
 * Targets: sidebar (nav, brand, profile strip), navbar user menu, notification items,
 * and main content tabs/pagination (section.content .nav-link / .page-link / .ccb-spa-nav).
 * Page scripts in {% block extrascript_inner %} are reinjected via markers in base.html.
 *
 * IMPORTANT: SPA mode is OFF by default. Partial DOM swaps break page-specific CSS in <head>,
 * AdminLTE treeview/sidebar state, and many inline scripts that assume a full load. Users get
 * broken layouts until full reload. Set CCB_SPA_NAV_ENABLED to true only after hardening.
 */
(function () {
  'use strict';

  /** Full page navigation — reliable UX. Set true to experiment with in-app HTML swap again. */
  var CCB_SPA_NAV_ENABLED = false;

  /**
   * Run after DOM is ready. After SPA navigation, document.readyState is already "complete",
   * so DOMContentLoaded never fires — use this instead of only DOMContentLoaded in page scripts.
   */
  window.ccbRunWhenDocumentReady = function (fn) {
    if (typeof fn !== 'function') return;
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', fn);
    } else {
      fn();
    }
  };

  var navLoadingClass = 'ccb-nav-loading';

  function sameOrigin(a) {
    try {
      return new URL(a.href, window.location.href).origin === window.location.origin;
    } catch (e) {
      return false;
    }
  }

  function hasScriptSrc(src) {
    if (!src) return false;
    try {
      var want = new URL(src, window.location.href).pathname;
      var list = document.querySelectorAll('script[src]');
      for (var i = 0; i < list.length; i++) {
        if (new URL(list[i].src, window.location.href).pathname === want) return true;
      }
    } catch (e) {}
    return false;
  }

  function injectPageScripts(html) {
    var re = /<!--\s*ccb-nav-page-scripts\s*-->([\s\S]*?)<!--\s*\/ccb-nav-page-scripts\s*-->/;
    var m = html.match(re);
    if (!m || !m[1]) return;
    var parser = new DOMParser();
    var fragDoc = parser.parseFromString(m[1].trim(), 'text/html');
    fragDoc.querySelectorAll('script').forEach(function (oldScript) {
      if (oldScript.src) {
        if (hasScriptSrc(oldScript.src)) return;
        var s = document.createElement('script');
        s.src = oldScript.src;
        if (oldScript.async) s.async = true;
        if (oldScript.defer) s.defer = true;
        document.body.appendChild(s);
        return;
      }
      var s = document.createElement('script');
      s.textContent = oldScript.textContent;
      document.body.appendChild(s);
    });
  }

  function initTreeview() {
    if (!window.jQuery || typeof jQuery.fn.Treeview !== 'function') return;
    try {
      jQuery('[data-widget="treeview"]').each(function () {
        jQuery(this).Treeview('init');
      });
    } catch (e) {}
  }

  /**
   * SPA navigation replaces .content-wrapper only; <head> is not replaced, so {% block extrahead %}
   * styles never apply when opening a page via sidebar/ccb-spa-nav. Merge stylesheet links and
   * inline <style> from the fetched document into the live document.head.
   */
  var BASE_NAV_LOADING_STYLE =
    '.content-wrapper.ccb-nav-loading { opacity: 0.72; transition: opacity 0.12s ease; pointer-events: none; }';

  function normalizeStyleText(text) {
    return String(text || '')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function isBaseTemplateNavStyle(text) {
    return normalizeStyleText(text) === normalizeStyleText(BASE_NAV_LOADING_STYLE);
  }

  function mergeSpaHeadAssets(doc) {
    if (!doc || !doc.head) return;
    var head = document.head;

    head.querySelectorAll('style[data-ccb-spa-nav="1"]').forEach(function (el) {
      el.remove();
    });

    doc.head.querySelectorAll('link[rel="stylesheet"]').forEach(function (link) {
      var href = link.getAttribute('href');
      if (!href) return;
      var abs;
      try {
        abs = new URL(href, window.location.href).href;
      } catch (e) {
        return;
      }
      var dup = false;
      document.querySelectorAll('head link[rel="stylesheet"]').forEach(function (existing) {
        try {
          if (existing.href === abs) dup = true;
        } catch (e2) {}
      });
      if (dup) return;
      head.appendChild(link.cloneNode(true));
    });

    doc.head.querySelectorAll('style').forEach(function (style) {
      var t = style.textContent || '';
      if (isBaseTemplateNavStyle(t)) return;
      var s = document.createElement('style');
      s.setAttribute('data-ccb-spa-nav', '1');
      s.textContent = t;
      head.appendChild(s);
    });
  }

  function shouldNavigateSpa(a, e) {
    if (!CCB_SPA_NAV_ENABLED) return false;
    if (!a || !a.getAttribute('href')) return false;
    var href = a.getAttribute('href');
    if (href === '#' || href === '' || href.indexOf('javascript:') === 0) return false;
    if (a.getAttribute('data-cc-full-nav') === '1') return false;
    if (a.target === '_blank' || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return false;
    if (a.hasAttribute('download')) return false;
    if (!sameOrigin(a)) return false;

    if (a.closest('.main-sidebar')) {
      if (a.classList.contains('nav-link') || a.classList.contains('brand-link') || a.classList.contains('user-panel')) {
        return true;
      }
    }

    if (a.closest('#user-dropdown') && a.classList.contains('user-dropdown-item')) {
      if (a.id === 'navbar-logout-link') return false;
      return true;
    }

    if (a.classList.contains('notif-item') && a.closest('#notifications-dropdown')) {
      return true;
    }

    if (a.closest('section.content')) {
      if (a.classList.contains('ccb-spa-nav')) return true;
      if (a.classList.contains('nav-link') || a.classList.contains('page-link')) return true;
    }

    return false;
  }

  var loading = false;

  function navigate(url, doPushState) {
    if (loading) return;
    var wrapper = document.querySelector('.content-wrapper');
    var sidebar = document.querySelector('.main-sidebar');
    if (!wrapper || !sidebar) return;

    loading = true;
    wrapper.classList.add(navLoadingClass);

    fetch(url, {
      credentials: 'same-origin',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        Accept: 'text/html',
      },
    })
      .then(function (res) {
        if (res.redirected) {
          window.location.href = res.url;
          return null;
        }
        if (res.status === 401 || res.status === 403) {
          window.location.href = url;
          return null;
        }
        if (!res.ok) throw new Error('status ' + res.status);
        return res.text();
      })
      .then(function (html) {
        if (!html) return;
        var parser = new DOMParser();
        var doc = parser.parseFromString(html, 'text/html');
        var newWrapper = doc.querySelector('.content-wrapper');
        if (!newWrapper) {
          window.location.href = url;
          return;
        }
        var newNav = doc.querySelector('.main-sidebar .sidebar nav.mt-2');
        var curNav = document.querySelector('.main-sidebar .sidebar nav.mt-2');
        if (newNav && curNav) {
          curNav.innerHTML = newNav.innerHTML;
        }

        if (doPushState !== false) {
          try {
            history.pushState({ ccbNav: true }, '', url);
          } catch (e) {}
        }

        var titleEl = doc.querySelector('title');
        if (titleEl && titleEl.textContent) {
          document.title = titleEl.textContent;
        }

        wrapper.outerHTML = newWrapper.outerHTML;

        mergeSpaHeadAssets(doc);
        injectPageScripts(html);
        initTreeview();

        window.scrollTo(0, 0);
      })
      .catch(function () {
        window.location.href = url;
      })
      .finally(function () {
        loading = false;
        var w = document.querySelector('.content-wrapper');
        if (w) w.classList.remove(navLoadingClass);
      });
  }

  document.addEventListener(
    'click',
    function (e) {
      var a = e.target.closest('a');
      if (!a || !shouldNavigateSpa(a, e)) return;
      e.preventDefault();
      navigate(a.href, true);
    },
    false
  );

  window.addEventListener('popstate', function () {
    if (!CCB_SPA_NAV_ENABLED) return;
    navigate(window.location.href, false);
  });
})();
