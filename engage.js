/* Levadinho engagement events (owner, 2026-10-07). No cookies, nothing stored in the browser.
   Sends a few GoatCounter events per visit, only when GoatCounter itself loaded (so #skipgc devices send nothing):
     time-<bucket>:<path>     how long the page stayed open (0-10s, 10-30s, 30-60s, 1-3m, 3m+), sent once on leaving
     scroll-<max>:<path>      deepest scroll reached (25, 50, 75, 100 %), sent once on leaving
     seen-<block>:<path>      a block came into view: cta (WhatsApp), status, bus, faq, webcam, map, weather
     out-<site>:<path>        a click to an outside site (simplifica, ifcn, ipma, visitmadeira, whatsapp, other)
     lang-<xx>:<path>         a click on the language switcher
   Described in the privacy policy (privacy/). Event names carry the page so the stats can be read per page. */
(function () {
  "use strict";
  var page = location.pathname || "/";
  var start = Date.now(), maxScroll = 0, sentLeave = false, seen = {};

  function gc() { return window.goatcounter && window.goatcounter.count ? window.goatcounter : null; }
  function send(name) {
    var g = gc();
    if (!g) return;
    try { g.count({ path: name + ":" + page, title: name, event: true }); } catch (e) {}
  }

  function bucket(s) {
    return s < 10 ? "0-10s" : s < 30 ? "10-30s" : s < 60 ? "30-60s" : s < 180 ? "1-3m" : "3m+";
  }
  function onScroll() {
    var h = document.documentElement, b = document.body;
    var total = Math.max(h.scrollHeight, b.scrollHeight) - window.innerHeight;
    var pct = total <= 0 ? 100 : Math.round(100 * (window.scrollY || h.scrollTop) / total);
    if (pct > maxScroll) maxScroll = pct;
  }
  function leave() {
    if (sentLeave) return;
    sentLeave = true;
    send("time-" + bucket((Date.now() - start) / 1000));
    var s = maxScroll >= 95 ? 100 : maxScroll >= 75 ? 75 : maxScroll >= 50 ? 50 : 25;
    send("scroll-" + s);
  }

  var BLOCKS = { cta: ".lvd-cta", status: "#statusCard", bus: "#bus", faq: "#faq", webcam: ".tcam",
                 map: "iframe[src*='openstreetmap']", weather: "#weather" };
  function watchBlocks() {
    if (!("IntersectionObserver" in window)) return;
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        var k = en.target.getAttribute("data-engage");
        if (en.isIntersecting && !seen[k]) { seen[k] = true; send("seen-" + k); io.unobserve(en.target); }
      });
    }, { threshold: 0.4 });
    Object.keys(BLOCKS).forEach(function (k) {
      var el = document.querySelector(BLOCKS[k]);
      if (el) { el.setAttribute("data-engage", k); io.observe(el); }
    });
  }

  function site(host) {
    host = host.replace(/^www\./, "");
    if (/simplifica\.madeira\.gov\.pt$/.test(host)) return "simplifica";
    if (/ifcn\.madeira\.gov\.pt$/.test(host)) return "ifcn";
    if (/ipma\.pt$/.test(host)) return "ipma";
    if (/visitmadeira\.com$/.test(host)) return "visitmadeira";
    if (/(^|\.)wa\.me$|whatsapp\.com$/.test(host)) return "whatsapp";
    return "other";
  }
  document.addEventListener("click", function (e) {
    var a = e.target.closest ? e.target.closest("a[href]") : null;
    if (!a) return;
    if (a.closest(".langs")) { send("lang-" + (a.getAttribute("hreflang") || "x")); return; }
    if (a.hostname && a.hostname !== location.hostname && /^https?:$/.test(a.protocol)) send("out-" + site(a.hostname));
  }, true);

  window.addEventListener("scroll", onScroll, { passive: true });
  document.addEventListener("visibilitychange", function () { if (document.visibilityState === "hidden") leave(); });
  window.addEventListener("pagehide", leave);
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", function () { onScroll(); watchBlocks(); });
  else { onScroll(); watchBlocks(); }
})();
