// Service Worker for Nanay's Kakanin PWA
const CACHE_NAME = 'nanays-kakanin-v3';
const urlsToCache = [
  '/',
  '/static/kakanin/style.css',
  '/static/kakanin/img/logo.png',
  '/static/kakanin/img/logo1.png',
  '/static/kakanin/img/kakanin.png',
  '/shop/',
  '/about/',
  '/contact/'
];

// CDN resources to cache on first load
const cdnResources = [
  'https://cdn.tailwindcss.com',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css'
];

// Install event - cache resources
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Opened cache');
        return cache.addAll(urlsToCache);
      })
  );
});

// Fetch event - serve from cache when offline
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Return cached version or fetch from network
        if (response) {
          return response;
        }
        
        return fetch(event.request).then(response => {
          // Don't cache if not a valid response
          if (!response || response.status !== 200) {
            return response;
          }

          // Check if this is a CDN resource or important asset
          const shouldCache = 
            event.request.url.includes('cdn.tailwindcss.com') ||
            event.request.url.includes('cdnjs.cloudflare.com') ||
            event.request.url.includes('cdn.jsdelivr.net') ||
            event.request.url.includes('/static/') ||
            event.request.destination === 'style' ||
            event.request.destination === 'script' ||
            event.request.destination === 'font';

          if (shouldCache) {
            // Clone the response
            const responseToCache = response.clone();
            caches.open(CACHE_NAME)
              .then(cache => {
                cache.put(event.request, responseToCache);
              });
          }

          return response;
        }).catch(() => {
          // Return offline page for navigation requests
          if (event.request.destination === 'document') {
            return caches.match('/offline/');
          }
          
          // Return skeleton for API requests
          if (event.request.url.includes('/api/') || event.request.url.includes('/shop/')) {
            return new Response(JSON.stringify({
              offline: true,
              message: 'You are currently offline. Some features may be limited.'
            }), {
              headers: { 'Content-Type': 'application/json' }
            });
          }
        });
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            console.log('Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// Background sync for offline orders
self.addEventListener('sync', event => {
  if (event.tag === 'background-sync') {
    event.waitUntil(doBackgroundSync());
  }
});

function doBackgroundSync() {
  // Handle offline orders when back online
  return new Promise((resolve) => {
    // This would sync any offline orders stored in IndexedDB
    console.log('Background sync triggered');
    resolve();
  });
}
