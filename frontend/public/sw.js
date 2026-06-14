const CACHE_STATIC = "successcore-static-v1";
const CACHE_API = "successcore-api-v1";
const CACHE_DYNAMIC = "successcore-dynamic-v1";

const STATIC_ASSETS = [
  "/dashboard",
  "/favicon.ico",
  "/manifest.json",
];

const STATIC_EXTENSIONS = /\.(?:js|css|png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf|eot)$/i;
const API_ROUTE = /\/api\/v1\//i;

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_STATIC).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => {
            return name.startsWith("successcore-") &&
              name !== CACHE_STATIC &&
              name !== CACHE_API &&
              name !== CACHE_DYNAMIC;
          })
          .map((name) => caches.delete(name))
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  if (API_ROUTE.test(url.pathname)) {
    event.respondWith(
      fetch(event.request, { credentials: "include" }).catch((err) => {
        console.error("SW API fetch failed:", err);
        return new Response(JSON.stringify({ error: "network_error" }), {
          status: 502,
          headers: { "Content-Type": "application/json" },
        });
      })
    );
    return;
  }

  if (STATIC_EXTENSIONS.test(url.pathname)) {
    event.respondWith(cacheFirst(event.request));
    return;
  }

  event.respondWith(networkFirst(event.request));
});

function cacheFirst(request) {
  return caches.match(request).then((cached) => {
    if (cached) return cached;
    return fetch(request).then((response) => {
      if (!response || response.status !== 200 || response.type !== "basic") {
        return response;
      }
      const clone = response.clone();
      caches.open(CACHE_STATIC).then((cache) => cache.put(request, clone));
      return response;
    });
  });
}

function networkFirst(request) {
  return fetch(request)
    .then((response) => {
      if (!response || response.status !== 200) return response;
      const clone = response.clone();
      caches.open(API_ROUTE.test(request.url) ? CACHE_API : CACHE_DYNAMIC).then((cache) =>
        cache.put(request, clone)
      );
      return response;
    })
    .catch(() => {
      return caches.match(request).then((cached) => {
        if (cached) return cached;
        return new Response(
          JSON.stringify({ error: "offline", detail: "You are offline and this resource is not cached." }),
          { status: 503, headers: { "Content-Type": "application/json" } }
        );
      });
    });
}

self.addEventListener("push", (event) => {
  let data = {};
  if (event.data) {
    try {
      data = event.data.json();
    } catch (_) {
      data = { title: "SuccessCore", body: event.data.text() };
    }
  }
  const options = {
    body: data.body || "You have a new notification.",
    icon: data.icon || "/icons/icon-192x192.png",
    badge: "/icons/icon-192x192.png",
    vibrate: data.vibrate || [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: data.primaryKey || "1",
      url: data.url || "/dashboard",
    },
    actions: data.actions || [],
    tag: data.tag || "successcore",
    requireInteraction: data.requireInteraction || false,
  };
  event.waitUntil(self.registration.showNotification(data.title || "SuccessCore", options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = event.notification.data?.url || "/dashboard";
  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((windowClients) => {
      for (const client of windowClients) {
        if (client.url.includes(self.location.origin) && "focus" in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(url);
      }
    })
  );
});

self.addEventListener("sync", (event) => {
  if (event.tag === "sync-pto-requests") {
    event.waitUntil(syncPTORequests());
  }
});

function openDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open("successcore-offline", 1);
    req.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains("ptoRequests")) {
        db.createObjectStore("ptoRequests", { keyPath: "id", autoIncrement: true });
      }
    };
    req.onsuccess = (e) => resolve(e.target.result);
    req.onerror = (e) => reject(e.target.error);
  });
}

function syncPTORequests() {
  return openDB().then((db) => {
    const tx = db.transaction("ptoRequests", "readwrite");
    const store = tx.objectStore("ptoRequests");
    const getAll = store.getAll();

    return new Promise((resolve) => {
      getAll.onsuccess = () => {
        const requests = getAll.result;
        if (requests.length === 0) return resolve();

        const syncPromises = Promise.all(
          requests.map((req) => {
            return fetch("/api/v1/pto/requests", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(req.payload),
              credentials: "include",
            }).then((response) => {
              if (response.ok) {
                const deleteTx = db.transaction("ptoRequests", "readwrite");
                deleteTx.objectStore("ptoRequests").delete(req.id);
              }
            }).catch(() => {});
          })
        );

        syncPromises.then(resolve);
      };
    });
  });
}
