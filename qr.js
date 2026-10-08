/* Levadinho QR codes (owner, 2026-10-08). A printed code opens /q/<code>/, which sends the visitor to the target
   page in their phone's language with #qr=<code> appended (scripts/gen_qr.py writes those redirect pages).
   On the target page this script, loaded in the <head> before the others:
     * sets window.LEVADINHO_QR = "<code>" (and data-qr on <html>), so the page's "now" panel knows the visitor is
       standing in the place, not planning from home (funchal.js);
     * adds "-qr" to the #web-<tag> of every WhatsApp link, so the bot records the conversation as started from a scan;
     * removes #qr=... from the address bar, so a shared or bookmarked link isn't counted as another scan.
   The scan itself is counted by /engage.js as the event qr-<code>:<path>. Search engines ignore the part after #,
   so a QR link never creates a second URL for the page. No cookies, nothing stored. */
(function () {
  "use strict";
  var m = /(?:^#|&)qr=([a-z0-9-]{1,30})(?:&|$)/.exec(location.hash || "");
  if (!m) return;
  var code = m[1];
  window.LEVADINHO_QR = code;
  document.documentElement.setAttribute("data-qr", code);
  try { history.replaceState(null, "", location.pathname + location.search); } catch (e) {}

  function tagLinks() {
    document.querySelectorAll('a[href*="wa.me/"]').forEach(function (a) {
      a.href = a.href.replace(/(%23web-[a-z0-9-]+?)(-qr)?(?=$|&|%20|")/i, function (_, t) {
        return t.length <= 40 ? t + "-qr" : t;   // t is %23web-...; the bot accepts web-[a-z0-9-]{1,40}
      });
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", tagLinks); else tagLinks();
})();
