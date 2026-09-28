/* Levadinho guide service worker: makes the guide work with no signal.
 *
 * The page itself fills the cache as soon as it opens (see downloadPack in guide.js):
 * the page shell, the route and every clip in the visitor's language. This worker only
 * serves from that cache:
 *  - the page and guide.js: network first (fresh when online), cache when offline or slow;
 *  - route data and audio (…/r/…): cache first, network if missing.
 * The server log (POST …/log) is never cached; the page queues it on the phone instead.
 */
const CACHE = "levadinho-guide-v1";
const SLOW_MS = 4000;   // weak signal: fall back to the cache after this long

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

function networkFirst(req) {
  return new Promise((resolve) => {
    let done = false;
    const fromCache = () => caches.match(req, { ignoreSearch: true }).then((hit) => {
      if (!done && hit) { done = true; resolve(hit); }
      return hit;
    });
    const timer = setTimeout(fromCache, SLOW_MS);
    fetch(req).then((r) => {
      clearTimeout(timer);
      if (r.ok) {
        const copy = r.clone();
        const key = new URL(req.url); key.search = "";
        caches.open(CACHE).then((c) => c.put(key.href, copy));
      }
      if (!done) { done = true; resolve(r); }
    }).catch(() => {
      clearTimeout(timer);
      fromCache().then((hit) => { if (!done) { done = true; resolve(hit || Response.error()); } });
    });
  });
}

function cacheFirst(req) {
  return caches.match(req).then((hit) => hit || fetch(req).then((r) => {
    if (r.ok) { const copy = r.clone(); caches.open(CACHE).then((c) => c.put(req, copy)); }
    return r;
  }));
}

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.pathname.includes("/guide/r/")) return e.respondWith(cacheFirst(req));
  if (req.mode === "navigate" || url.pathname.endsWith("/guide.js") || url.pathname.endsWith("/guide/")) {
    return e.respondWith(networkFirst(req));
  }
});
