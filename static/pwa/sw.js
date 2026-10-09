// Network-first: pages always come fresh from the server (they're per-user and change often).
// Only the offline fallback and static assets are cached, so the installed app still opens without a connection.
const CACHE = 'acvs-v1';
const OFFLINE_URL = '/offline';
const PRECACHE = [OFFLINE_URL, '/static/style.css', '/static/logo-icon.png', '/static/icon-192.png'];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(PRECACHE)));
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;

  if (request.mode === 'navigate') {
    event.respondWith(fetch(request).catch(() => caches.match(OFFLINE_URL)));
    return;
  }

  if (new URL(request.url).pathname.startsWith('/static/') && !request.url.includes('/uploads/')) {
    event.respondWith(
      fetch(request)
        .then(response => {
          const copy = response.clone();
          caches.open(CACHE).then(cache => cache.put(request, copy));
          return response;
        })
        .catch(() => caches.match(request))
    );
  }
});
