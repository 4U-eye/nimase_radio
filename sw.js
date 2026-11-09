// myradio — smartphone (PWA) service worker
// Shell and scripts are cached so the station opens fast and the script
// pages stay readable offline. Audio (.mp3), weather and other sites are
// never cached here: audio is large/streamed, the rest must stay fresh.
const CACHE = "myradio-v1";
const SHELL = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./station.json",
  "./episodes.json",
  "./logo.svg",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
  "./character/character.json",
  "./character/base.png",
  "./character/blink.png",
  "./character/half_blink.png",
  "./character/mouth_half.png",
  "./character/mouth_open.png",
  "./character/smile_mouth.png",
  "./character/depth.png"
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  if (url.pathname.endsWith(".mp3")) return; // audio: always the network

  // Episode lists and scripts change every morning: network first, cache as fallback.
  if (url.pathname.endsWith(".json")) {
    e.respondWith(
      fetch(e.request)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(e.request, copy));
          return res;
        })
        .catch(() => caches.match(e.request))
    );
    return;
  }

  // Everything else from this station: cache first, refresh in the background.
  e.respondWith(
    caches.match(e.request).then((hit) => {
      const fresh = fetch(e.request)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(e.request, copy));
          return res;
        })
        .catch(() => hit);
      return hit || fresh;
    })
  );
});
