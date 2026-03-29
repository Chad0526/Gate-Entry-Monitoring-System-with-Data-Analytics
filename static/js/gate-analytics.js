/**
 * Gate analytics: Chart.js instances + init/destroy for full page and AJAX partial reloads.
 */
(function () {
  'use strict';

  window._gateAnalyticsCharts = window._gateAnalyticsCharts || [];

  window.gateAnalyticsDestroyCharts = function () {
    (window._gateAnalyticsCharts || []).forEach(function (ch) {
      try {
        if (ch && typeof ch.destroy === 'function') ch.destroy();
      } catch (e) {}
    });
    window._gateAnalyticsCharts = [];
  };

  function readJsonScript(id) {
    var el = document.getElementById(id);
    if (!el || !el.textContent) return [];
    try {
      return JSON.parse(el.textContent);
    } catch (e) {
      return [];
    }
  }

  window.gateAnalyticsInitCharts = function () {
    if (typeof Chart === 'undefined') return;
    window.gateAnalyticsDestroyCharts();

    Chart.defaults.global.defaultFontFamily =
      "'Source Sans 3', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial";
    Chart.defaults.global.defaultFontColor = '#1a5c35';

    var ctxTraffic = document.getElementById('chartTrafficFlow');
    if (ctxTraffic) {
      var trafficLabels = readJsonScript('analytics-traffic-labels');
      var trafficIn = readJsonScript('analytics-traffic-in');
      var trafficOut = readJsonScript('analytics-traffic-out');
      var maxIn = trafficIn.length ? Math.max.apply(null, trafficIn) : 0;
      var maxOut = trafficOut.length ? Math.max.apply(null, trafficOut) : 0;
      var peak = Math.max(0, maxIn, maxOut);
      var step = peak === 0 ? 50 : peak <= 50 ? 10 : peak <= 200 ? 25 : 50;
      var yMax = peak === 0 ? 50 : Math.max(step, Math.ceil(peak / step) * step);
      var ch2 = new Chart(ctxTraffic.getContext('2d'), {
        type: 'line',
        data: {
          labels: trafficLabels,
          datasets: [
            {
              label: 'Entries',
              data: trafficIn,
              borderColor: 'rgba(22, 163, 74, 1)',
              backgroundColor: 'rgba(34, 197, 94, 0.28)',
              borderWidth: 2.5,
              lineTension: 0.45,
              fill: true,
              pointRadius: 4,
              pointHoverRadius: 5,
              pointBackgroundColor: 'rgba(22, 163, 74, 1)',
              pointBorderColor: '#ffffff',
              pointBorderWidth: 2,
            },
            {
              label: 'Exits',
              data: trafficOut,
              borderColor: 'rgba(249, 115, 22, 1)',
              backgroundColor: 'rgba(254, 215, 170, 0.45)',
              borderWidth: 2.5,
              lineTension: 0.45,
              fill: true,
              pointRadius: 4,
              pointHoverRadius: 5,
              pointBackgroundColor: 'rgba(249, 115, 22, 1)',
              pointBorderColor: '#ffffff',
              pointBorderWidth: 2,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          legend: {
            position: 'bottom',
            labels: { usePointStyle: true, padding: 16, fontColor: '#475569' },
          },
          tooltips: {
            mode: 'index',
            intersect: false,
            callbacks: {
              label: function (tooltipItem, data) {
                var ds = data.datasets[tooltipItem.datasetIndex];
                return ds.label + ': ' + tooltipItem.yLabel;
              },
            },
          },
          scales: {
            xAxes: [{ gridLines: { display: false }, ticks: { maxRotation: 0, autoSkip: false } }],
            yAxes: [
              {
                ticks: {
                  beginAtZero: true,
                  precision: 0,
                  max: yMax,
                  stepSize: step,
                },
                gridLines: { color: 'rgba(148, 163, 184, 0.25)', drawBorder: false },
              },
            ],
          },
        },
      });
      window._gateAnalyticsCharts.push(ch2);
    }

    var ctxRole = document.getElementById('chartEntryByRole');
    if (ctxRole) {
      var roleLabels = readJsonScript('analytics-role-labels');
      var roleData = readJsonScript('analytics-role-values');
      var ch3 = new Chart(ctxRole.getContext('2d'), {
        type: 'doughnut',
        data: {
          labels: roleLabels,
          datasets: [
            {
              data: roleData,
              backgroundColor: [
                'rgba(22, 163, 74, 0.92)',
                'rgba(249, 115, 22, 0.92)',
              ],
              borderColor: '#ffffff',
              borderWidth: 2,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutoutPercentage: 58,
          legend: {
            position: 'bottom',
            labels: { usePointStyle: true, padding: 10, fontColor: '#475569' },
          },
          tooltips: {
            callbacks: {
              label: function (tooltipItem, data) {
                var label = data.labels[tooltipItem.index] || '';
                var v = data.datasets[0].data[tooltipItem.index];
                return label + ': ' + v;
              },
            },
          },
        },
      });
      window._gateAnalyticsCharts.push(ch3);
    }

  };
})();
