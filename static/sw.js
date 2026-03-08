const CACHE_NAME = 'lnct-attendance-cache-v1';
const STATIC_ASSETS = [
    '/',
    '/static/index.html',
    '/static/style.css',
    '/static/script.js',
    '/static/icon.svg',
    '/manifest.json',
    'https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
    'https://cdn.jsdelivr.net/npm/chart.js'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(STATIC_ASSETS);
        })
    );
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME) {
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
    self.clients.claim();
});

self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // Network-first strategy for API routes to always get fresh attendance data
    if (url.pathname.startsWith('/attendance') ||
        url.pathname.startsWith('/analysis') ||
        url.pathname.startsWith('/timetable') ||
        url.pathname.startsWith('/risk-engine') ||
        url.pathname.startsWith('/leave-simulator')) {

        event.respondWith(
            fetch(event.request).catch(() => {
                // If network fails, try returning from cache if we stored any previous API responses (optional)
                // For now, API requests might fail when fully offline unless we have heavy caching for them.
                return new Response(JSON.stringify({
                    success: false,
                    error: "You are offline. Please connect to the internet to fetch fresh attendance data."
                }), {
                    headers: { 'Content-Type': 'application/json' }
                });
            })
        );
        return;
    }

    // Cache-first strategy for static assets
    event.respondWith(
        caches.match(event.request).then((response) => {
            if (response) {
                return response;
            }
            return fetch(event.request).then((networkResponse) => {
                if (!networkResponse || networkResponse.status !== 200 || networkResponse.type !== 'basic') {
                    return networkResponse;
                }
                const responseToCache = networkResponse.clone();
                caches.open(CACHE_NAME).then((cache) => {
                    cache.put(event.request, responseToCache);
                });
                return networkResponse;
            });
        }).catch(() => {
            // Fallback for document requests to offline page or just root
            if (event.request.mode === 'navigate') {
                return caches.match('/');
            }
        })
    );
});
