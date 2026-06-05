// 电子衣橱 Service Worker — 离线缓存
const CACHE_NAME = 'wardrobe-v1';

const PRECACHE_URLS = [
  '/',
  '/static/manifest.json',
  '/static/icon.svg',
];

// 安装：预缓存核心资源
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(PRECACHE_URLS).catch(() => {});
    })
  );
  self.skipWaiting();
});

// 激活：清理旧缓存
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
      );
    })
  );
  self.clients.claim();
});

// 请求拦截：网络优先，失败时降级到缓存
self.addEventListener('fetch', (event) => {
  // 跳过非 GET 请求和 /api/ 接口（不缓存动态数据）
  if (event.request.method !== 'GET') return;
  if (event.request.url.includes('/api/')) return;

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // 缓存成功的响应（只缓存同源静态资源）
        if (response.status === 200) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, clone);
          });
        }
        return response;
      })
      .catch(() => {
        // 网络失败时返回缓存
        return caches.match(event.request);
      })
  );
});
