/**
 * Report filter bar (custom dropdowns, mode sync). Call after DOM updates (e.g. AJAX partial).
 * Document-level click handler is registered once to avoid duplicate listeners on repeated inits.
 */
(function () {
  if (!window.__reportsFilterBarDocClickBound) {
    window.__reportsFilterBarDocClickBound = true;
    document.addEventListener('click', function (e) {
      if (e.target.closest('.ccb-custom-dropdown-wrap') || e.target.closest('#report-type-dropdown-wrap')) return;
      document.querySelectorAll('.ccb-custom-dropdown-wrap.open, .report-type-dropdown-wrap.open').forEach(function (w) {
        w.classList.remove('open');
        var btn = w.querySelector('button');
        var listbox = w.querySelector('[role="listbox"]');
        if (btn) btn.setAttribute('aria-expanded', 'false');
        if (listbox) listbox.setAttribute('aria-hidden', 'true');
      });
    });
  }

  window.initReportsFilterBar = function () {
    var form = document.getElementById('report-filter-form');
    if (!form) return;
    var dateRangeInput = document.getElementById('report-date-range-input');
    var customStart = document.getElementById('report-custom-dates');
    var customEnd = document.getElementById('report-custom-dates-end');
    var allDay = document.getElementById('report-all-day');
    var timeRange = document.getElementById('report-time-range');
    var scopeInput = document.getElementById('report-scope-input');
    var eventWrap = document.getElementById('report-event-wrap');

    function toggleCustomDates() {
      var show = dateRangeInput && dateRangeInput.value === 'custom';
      if (customStart) customStart.style.display = show ? 'flex' : 'none';
      if (customEnd) customEnd.style.display = show ? 'flex' : 'none';
    }
    function toggleTime() {
      var show = !allDay || !allDay.checked;
      if (timeRange) timeRange.style.display = show ? 'flex' : 'none';
    }
    function toggleEvent() {
      var show = scopeInput && scopeInput.value === 'specific_event';
      if (eventWrap) eventWrap.style.display = show ? 'flex' : 'none';
    }

    function initCustomDropdown(wrapId, triggerId, panelId, inputId, triggerTextSel, onSelect) {
      var wrap = document.getElementById(wrapId);
      var trigger = document.getElementById(triggerId);
      var panel = document.getElementById(panelId);
      var input = document.getElementById(inputId);
      var triggerText = trigger && trigger.querySelector('.report-type-trigger-text');
      if (!wrap || !trigger || !panel || !input) return;
      trigger.addEventListener('click', function (e) {
        e.stopPropagation();
        var isOpen = wrap.classList.contains('open');
        document.querySelectorAll('.ccb-custom-dropdown-wrap.open, .report-type-dropdown-wrap.open').forEach(function (w) {
          if (w !== wrap) {
            w.classList.remove('open');
            w.querySelector('button').setAttribute('aria-expanded', 'false');
            w.querySelector('[role="listbox"]').setAttribute('aria-hidden', 'true');
          }
        });
        if (!isOpen) {
          wrap.classList.add('open');
          trigger.setAttribute('aria-expanded', 'true');
          panel.setAttribute('aria-hidden', 'false');
        } else {
          wrap.classList.remove('open');
          trigger.setAttribute('aria-expanded', 'false');
          panel.setAttribute('aria-hidden', 'true');
        }
      });
      panel.querySelectorAll('.report-type-option').forEach(function (opt) {
        opt.addEventListener('click', function () {
          var val = this.getAttribute('data-value');
          var label = this.textContent.trim();
          input.value = val;
          if (triggerText) triggerText.textContent = label;
          panel.querySelectorAll('.report-type-option').forEach(function (o) { o.classList.remove('selected'); });
          this.classList.add('selected');
          wrap.classList.remove('open');
          trigger.setAttribute('aria-expanded', 'false');
          panel.setAttribute('aria-hidden', 'true');
          if (onSelect) onSelect(val);
        });
      });
    }

    initCustomDropdown('report-date-range-wrap', 'report-date-range-trigger', 'report-date-range-panel', 'report-date-range-input', null, function () {
      toggleCustomDates();
    });
    initCustomDropdown('report-scope-wrap', 'report-scope-trigger', 'report-scope-panel', 'report-scope-input', null, function () {
      toggleEvent();
    });
    if (document.getElementById('report-event-wrap-dropdown')) {
      initCustomDropdown('report-event-wrap-dropdown', 'report-event-trigger', 'report-event-panel', 'report-event-input');
    }

    if (allDay) allDay.addEventListener('change', toggleTime);

    var reportTypeWrap = document.getElementById('report-type-dropdown-wrap');
    var reportTypeTrigger = document.getElementById('report-type-trigger');
    var reportTypePanel = document.getElementById('report-type-dropdown-panel');
    var reportTypeInput = document.getElementById('filter-report-type-input');
    var reportTypeTriggerText = reportTypeTrigger && reportTypeTrigger.querySelector('.report-type-trigger-text');
    if (reportTypeWrap && reportTypeTrigger && reportTypePanel && reportTypeInput) {
      reportTypeTrigger.addEventListener('click', function (e) {
        e.stopPropagation();
        document.querySelectorAll('.ccb-custom-dropdown-wrap.open').forEach(function (w) {
          w.classList.remove('open');
          w.querySelector('button').setAttribute('aria-expanded', 'false');
          w.querySelector('[role="listbox"]').setAttribute('aria-hidden', 'true');
        });
        reportTypeWrap.classList.toggle('open');
        reportTypeTrigger.setAttribute('aria-expanded', reportTypeWrap.classList.contains('open'));
        reportTypePanel.setAttribute('aria-hidden', !reportTypeWrap.classList.contains('open'));
      });
      reportTypePanel.querySelectorAll('.report-type-option').forEach(function (opt) {
        opt.addEventListener('click', function () {
          var val = this.getAttribute('data-value');
          var label = this.textContent.trim();
          reportTypeInput.value = val;
          if (reportTypeTriggerText) reportTypeTriggerText.textContent = label;
          reportTypePanel.querySelectorAll('.report-type-option').forEach(function (o) { o.classList.remove('selected'); });
          this.classList.add('selected');
          reportTypeWrap.classList.remove('open');
          reportTypeTrigger.setAttribute('aria-expanded', 'false');
          reportTypePanel.setAttribute('aria-hidden', 'true');
          if (typeof form.requestSubmit === 'function') {
            form.requestSubmit();
          } else {
            form.submit();
          }
        });
      });
    }

    form.addEventListener('submit', function () {
      if (scopeInput && scopeInput.value === 'daily_gate_only') {
        var evInput = document.getElementById('report-event-input');
        if (evInput) evInput.removeAttribute('name');
      } else {
        var evInput2 = document.getElementById('report-event-input');
        if (evInput2 && !evInput2.hasAttribute('name')) evInput2.setAttribute('name', 'event_id');
      }
    });

    var modeSelect = document.getElementById('reports-mode-select');
    var programWrap = document.getElementById('report-program-wrap');
    var eventIoWrap = document.getElementById('report-event-io-wrap');
    var yearWrap = document.getElementById('report-year-level-wrap');
    var sectionWrap = document.getElementById('report-section-wrap');
    var audienceWrap = document.getElementById('report-audience-wrap');
    var eventWrapLegacy = document.getElementById('report-event-wrap');
    var specificEventWrap = document.getElementById('report-specific-event-wrap');
    function syncReportModeUI() {
      var isEvents = modeSelect && modeSelect.value === 'event_attendance';
      if (programWrap) programWrap.style.display = isEvents ? 'none' : 'flex';
      if (eventIoWrap) eventIoWrap.style.display = 'flex';
      if (yearWrap) yearWrap.style.display = isEvents ? 'none' : 'flex';
      if (sectionWrap) sectionWrap.style.display = isEvents ? 'none' : 'flex';
      if (audienceWrap) audienceWrap.style.display = isEvents ? 'none' : 'flex';
      if (eventWrapLegacy) eventWrapLegacy.style.display = isEvents ? 'flex' : 'none';
      if (specificEventWrap) specificEventWrap.style.display = isEvents ? 'flex' : 'none';
    }

    function _setSelectValueWithin(wrapEl, value) {
      if (!wrapEl) return;
      var sel = wrapEl.querySelector('select');
      if (sel) sel.value = value;
    }

    function syncAudienceUI() {
      // Requirement: show Program/Year/Section only when Audience = Students only.
      // Hide (and clear) them for Visitors only and All.
      var isEvents = modeSelect && modeSelect.value === 'event_attendance';
      if (isEvents) return;
      var sel = audienceWrap ? audienceWrap.querySelector('select[name="audience"]') : null;
      var audience = sel ? String(sel.value || '').toLowerCase() : 'all';
      var showStudentFilters = (audience === 'students');
      if (programWrap) programWrap.style.display = showStudentFilters ? 'flex' : 'none';
      if (yearWrap) yearWrap.style.display = showStudentFilters ? 'flex' : 'none';
      if (sectionWrap) sectionWrap.style.display = showStudentFilters ? 'flex' : 'none';

      if (!showStudentFilters) {
        _setSelectValueWithin(programWrap, '');
        _setSelectValueWithin(yearWrap, '');
        _setSelectValueWithin(sectionWrap, '');
      }
    }
    if (modeSelect) {
      modeSelect.addEventListener('change', function () {
        syncReportModeUI();
        syncAudienceUI();
        if (typeof form.requestSubmit === 'function') {
          form.requestSubmit();
        } else {
          form.submit();
        }
      });
      syncReportModeUI();
    }

    if (audienceWrap) {
      var audienceSelect = audienceWrap.querySelector('select[name="audience"]');
      if (audienceSelect) {
        audienceSelect.addEventListener('change', function () {
          syncAudienceUI();
          if (typeof form.requestSubmit === 'function') {
            form.requestSubmit();
          } else {
            form.submit();
          }
        });
      }
    }
    syncAudienceUI();

    toggleCustomDates();
    toggleTime();
    toggleEvent();
  };
})();
