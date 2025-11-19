// service-worker.js
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open('messenger-cache').then((cache) => {
            return cache.addAll([
                '/',
                '/static/style.css',
                '/manifest.json',
                '/uploads/default.png'
            ]);
        })
    );
});

self.addEventListener('fetch', (event) => {
    event.respondWith(
        caches.match(event.request).then((response) => {
            return response || fetch(event.request);
        })
    );
});
