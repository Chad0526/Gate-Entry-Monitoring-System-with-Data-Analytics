/**
 * Reports → Exports: fetch partial HTML and replace #reports-exports-root (no full page reload).
 */
(function () {
  function getRoot() {
    return document.getElementById('reports-exports-root');
  }

  function buildUrlFromForm(form) {
    var u = new URL(window.location.pathname, window.location.origin);
    var fd = new FormData(form);
    u.search = '';
    fd.forEach(function (v, k) {
      u.searchParams.append(k, v);
    });
    return u;
  }

  function fetchPartial(url) {
    var root = getRoot();
    if (!root) return;
    var u = new URL(url, window.location.origin);
    u.searchParams.set('partial', '1');
    root.style.opacity = '0.65';
    root.style.transition = 'opacity 0.12s ease';
    root.style.pointerEvents = 'none';
    fetch(u.toString(), {
      credentials: 'same-origin',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        Accept: 'text/html',
      },
    })
      .then(function (r) {
        if (!r.ok) throw new Error('partial');
        return r.text();
      })
      .then(function (html) {
        root.innerHTML = html;
        root.style.opacity = '';
        root.style.pointerEvents = '';
        var uClean = new URL(url, window.location.origin);
        uClean.searchParams.delete('partial');
        if (window.history && window.history.replaceState) {
          window.history.replaceState({}, '', uClean.pathname + uClean.search);
        }
        if (window.initReportsFilterBar) window.initReportsFilterBar();
        if (window.bindReportsExportsFilterFormAjax) window.bindReportsExportsFilterFormAjax();
        if (window.initReportsExportsExportButtons) window.initReportsExportsExportButtons();
      })
      .catch(function () {
        root.style.opacity = '';
        root.style.pointerEvents = '';
        window.location.href = url;
      });
  }

  window.initReportsExportsExportButtons = function () {
    var btn = document.getElementById('export-download-btn');
    var select = document.getElementById('export-format-select');
    if (!btn || !select) return;
    var baseUrl = btn.getAttribute('data-export-base');
    if (!baseUrl) return;
    btn.onclick = function () {
      var format = select.value || 'csv';
      var sep = baseUrl.indexOf('?') !== -1 ? '&' : '?';
      window.location.href = baseUrl + sep + 'format=' + encodeURIComponent(format);
    };
  };

  window.bindReportsExportsFilterFormAjax = function () {
    var form = document.getElementById('report-filter-form');
    if (!form) return;
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var u = buildUrlFromForm(form);
      fetchPartial(u.toString());
    });
  };

  window.reportsExportsAjaxInit = function () {
    var root = getRoot();
    if (!root || root._reportsExportsAjaxClickBound) return;
    root._reportsExportsAjaxClickBound = true;
    root.addEventListener('click', function (e) {
      var reset = e.target.closest('a.rf-btn-reset');
      if (reset && root.contains(reset)) {
        e.preventDefault();
        fetchPartial(reset.href);
        return;
      }
      var chip = e.target.closest('a.rf-chip');
      if (chip && chip.getAttribute('href') && root.contains(chip)) {
        e.preventDefault();
        fetchPartial(chip.getAttribute('href'));
      }
    });
  };
})();
