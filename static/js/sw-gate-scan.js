/**
 * Service worker for Gate QR Scan page - enables offline scanning.
 * Caches the scan page and CDN assets; serves from cache when offline.
 */
// Bump cache version to force clients to pick up latest gate_scan.html/JS changes.
const CACHE_NAME = 'gate-scan-v35';
const GATE_PATH = '/gate/';
const CDN_URLS = [
  'https://code.jquery.com/jquery-3.6.0.min.js',
  'https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js',
  'https://cdn.jsdelivr.net/npm/html5-qrcode@2.3.8/html5-qrcode.min.js'
];
function isHtml5QrcodeUrl(url) {
  return url.indexOf('unpkg.com') !== -1 && url.indexOf('html5-qrcode') !== -1;
}

function isGatePage(url) {
  try {
    const u = new URL(url);
    return u.origin === self.location.origin && u.pathname.startsWith(GATE_PATH);
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
      return Promise.all(CDN_URLS.map(function (assetUrl) {
        return fetch(assetUrl, { mode: 'no-cors' }).then(function (res) {
          if (res && res.ok) return cache.put(assetUrl, res.clone());
          if (res && res.type === 'opaque') return cache.put(assetUrl, res.clone());
        }).catch(function () {});
      })).then(function () {
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

/**
 * Do not intercept these: live JSON polling and staff heartbeat must hit the network
 * (or fail) — never serve stale API from cache.
 * Guard-display *HTML* navigations are NOT listed here so they use the same
 * cache-as-/gate/* strategy as the staff scanner: last good shell loads when tunnel is down.
 */
function isGuardApiOrHeartbeatUrl(url) {
  try {
    var p = new URL(url).pathname;
    return p.indexOf('/guard-dashboard') !== -1 ||
           p.indexOf('/scanner-heartbeat') !== -1;
  } catch (_) { return false; }
}

self.addEventListener('fetch', function (event) {
  var url = event.request.url;
  if (event.request.method !== 'GET') return;

  if (isGuardApiOrHeartbeatUrl(url)) return;

  if (event.request.mode === 'navigate' && isGatePage(url)) {
    event.respondWith(
      fetch(event.request).then(function (response) {
        if (response.ok && (response.type === 'basic' || response.type === 'cors' || response.type === 'opaque')) {
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
      fetch(event.request).then(function (response) {
        if (response.ok && (response.type === 'basic' || response.type === 'cors' || response.type === 'opaque')) {
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
