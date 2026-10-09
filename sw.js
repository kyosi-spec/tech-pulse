// Service worker: lets the app open instantly and work offline with the last briefing.
// Bump VERSION whenever you change index.html so phones pick up the new app.
const VERSION = "tech-pulse-v2";
const SHELL = ["./", "index.html", "manifest.webmanifest", "icons/icon-180.png", "icons/icon-192.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(VERSION).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k !== VERSION).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  // Briefing data: try the network first so it's fresh, fall back to the last copy offline.
  if (url.pathname.endsWith("/data/briefing.json")) {
    e.respondWith(fetch(e.request).then(res => {
      const copy = res.clone();
      caches.open(VERSION).then(c => c.put("data/briefing.json", copy));
      return res;
    }).catch(() => caches.match("data/briefing.json")));
    return;
  }
  // App files: cached copy first, network as backup.
  e.respondWith(caches.match(e.request).then(hit => hit || fetch(e.request)));
});
