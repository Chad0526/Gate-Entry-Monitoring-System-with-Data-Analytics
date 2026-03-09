/**
 * Service worker for Gate QR Scan page - enables offline scanning.
 * Caches the scan page and CDN assets; serves from cache when offline.
 */
const CACHE_NAME = 'gate-scan-v1';
const GATE_PATH = '/gate/';
const CDN_URLS = [
  'https://code.jquery.com/jquery-3.6.0.min.js'
];
function isHtml5QrcodeUrl(url) {
  return url.indexOf('unpkg.com') !== -1 && url.indexOf('html5-qrcode') !== -1;
}

function isGatePage(url) {
  try {
    const u = new URL(url);
    return u.origin === self.location.origin && (u.pathname === GATE_PATH || u.pathname === GATE_PATH.replace(/\/$/, ''));
  } catch (_) {
    return false;
  }
}

function isCdnAsset(url) {
  if (isHtml5QrcodeUrl(url)) return true;
  return CDN_URLS.some(function (base) {
    return url === base || url.startsWith(base + '?');
  });
}

self.addEventListener('install', function (event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function (cache) {
      var jq = 'https://code.jquery.com/jquery-3.6.0.min.js';
      return fetch(jq, { mode: 'cors' }).then(function (res) {
        if (res.ok) return cache.put(jq, res);
      }).catch(function () {}).then(function () {
        return self.skipWaiting();
      });
    })
  );
});

self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(
        keys.filter(function (k) { return k.startsWith('gate-scan-') && k !== CACHE_NAME; }).map(function (k) {
          return caches.delete(k);
        })
      );
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function (event) {
  var url = event.request.url;
  if (event.request.method !== 'GET') return;

  if (isGatePage(url)) {
    event.respondWith(
      fetch(event.request).then(function (response) {
        if (response.ok && response.type === 'basic') {
          var clone = response.clone();
          caches.open(CACHE_NAME).then(function (cache) {
            cache.put(event.request, clone);
          });
        }
        return response;
      }).catch(function () {
        return caches.match(event.request);
      })
    );
    return;
  }

  if (isCdnAsset(url)) {
    event.respondWith(
      fetch(event.request, { mode: 'cors' }).then(function (response) {
        if (response.ok && response.type === 'basic') {
          var clone = response.clone();
          caches.open(CACHE_NAME).then(function (cache) {
            cache.put(event.request, clone);
          });
        }
        return response;
      }).catch(function () {
        return caches.match(event.request);
      })
    );
  }
});
