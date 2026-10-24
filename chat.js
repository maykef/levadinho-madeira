/* Levadinho's chat at the top of the page (owner, 2026-10-10: "chat first, scroll down for the card and the rest").
   Injected by scripts/gen_chat.py on the pilot pages. The page itself is unchanged: this script adds the chat above
   it only when the model is up and answering (GET /health → model: true); asleep or off, the visitor gets the usual page.
   Opening message = the page's own quick-answers card (#answers), or on getting-back the plan table and taxi ranks,
   typed out. Follow-ups go to the bot (POST /webchat): same brain, same privacy notice (Accept first) as WhatsApp.
   Question pages with neither (owner, 2026-10-22: pr1-one-way, levadas-by-bus, weather, sunrise, free walks, booking,
   cruise port, one/two days) open on the page's lead paragraph (p.sub), with its FAQ questions as the chips; a tapped
   chip there gets the page's own answer, word for word (the section under that heading), not the model (owner, 2026-10-24).
   Counts (2026-10-11): chat-shown / chat-off (bot asleep or down) / chat-none (no opening on this page, since 2026-10-24) per page view, chat-ask-chip / chat-ask-typed (first question),
   chat-accept / chat-decline, chat-answered, chat-error, chat-down, chat-wa, chat-location (tapped Share my location), sent through /engage.js to the events
   site (never the text; #skipgc devices send nothing). */
(function () {
  "use strict";
  var API = "https://microscopy-rig-system.tail53cc58.ts.net/levadinho";
  var LANG = (document.documentElement.lang || "en").slice(0, 2);
  var UI = {
    en: { online: "Madeira trails · online", typing: "typing…", ph: "Ask Levadinho…", send: "Send", more: "↓ Card and full guide",
          wa: "Continue on WhatsApp", more2: "Anything else? Ask me here, for example:", err: "Sorry, I couldn't reach Levadinho. Try again in a moment.",
          slow: "Levadinho is taking too long. Try again in a moment, or continue on WhatsApp.",
          loc: "📍 Share my location", locNo: "I couldn't get your location. Tell me where you are instead." },
    pt: { online: "Percursos da Madeira · online", typing: "a escrever…", ph: "Pergunte ao Levadinho…", send: "Enviar", more: "↓ Cartão e guia completo",
          wa: "Continuar no WhatsApp", more2: "Mais alguma coisa? Pergunte aqui, por exemplo:", err: "Não foi possível falar com o Levadinho. Tente daqui a pouco.",
          slow: "O Levadinho está a demorar. Tente daqui a pouco ou continue no WhatsApp.",
          loc: "📍 Partilhar a minha localização", locNo: "Não consegui obter a sua localização. Diga-me onde está." },
    fr: { online: "Sentiers de Madère · en ligne", typing: "écrit…", ph: "Demandez à Levadinho…", send: "Envoyer", more: "↓ Fiche et guide complet",
          wa: "Continuer sur WhatsApp", more2: "Autre chose ? Demandez ici, par exemple :", err: "Impossible de joindre Levadinho. Réessayez dans un instant.",
          slow: "Levadinho met trop de temps. Réessayez dans un instant ou continuez sur WhatsApp.",
          loc: "📍 Partager ma position", locNo: "Je n'ai pas pu obtenir votre position. Dites-moi plutôt où vous êtes." },
    de: { online: "Madeiras Wanderwege · online", typing: "schreibt…", ph: "Fragen Sie Levadinho…", send: "Senden", more: "↓ Übersicht und ganzer Guide",
          wa: "Weiter auf WhatsApp", more2: "Sonst noch etwas? Fragen Sie hier, zum Beispiel:", err: "Levadinho ist gerade nicht erreichbar. Versuchen Sie es gleich noch einmal.",
          slow: "Levadinho braucht zu lange. Versuchen Sie es gleich noch einmal oder weiter auf WhatsApp.",
          loc: "📍 Meinen Standort teilen", locNo: "Ihr Standort war nicht abrufbar. Schreiben Sie mir stattdessen, wo Sie sind." },
    pl: { online: "Szlaki Madery · online", typing: "pisze…", ph: "Zapytaj Levadinho…", send: "Wyślij", more: "↓ Karta i pełny przewodnik",
          wa: "Kontynuuj na WhatsAppie", more2: "Coś jeszcze? Zapytaj tutaj, na przykład:", err: "Nie udało się połączyć z Levadinho. Spróbuj za chwilę.",
          slow: "Levadinho odpowiada zbyt długo. Spróbuj za chwilę albo kontynuuj na WhatsAppie.",
          loc: "📍 Udostępnij lokalizację", locNo: "Nie udało się pobrać lokalizacji. Napisz, gdzie jesteś." }
  };
  var CHIPS = {
    trail: { en: ["How do I get there?", "Where do I park?", "Is there an easier walk nearby?"],
             pt: ["Como chego lá?", "Onde estaciono?", "Há um percurso mais fácil perto?"],
             fr: ["Comment y aller ?", "Où se garer ?", "Y a-t-il une rando plus facile à côté ?"],
             de: ["Wie komme ich hin?", "Wo parke ich?", "Gibt es eine leichtere Wanderung in der Nähe?"],
             pl: ["Jak tam dojechać?", "Gdzie zaparkować?", "Czy w pobliżu jest łatwiejszy szlak?"] },
    closed: { en: ["Which walk nearby is open today?", "Is there an easy open walk nearby?"],
              pt: ["Que percurso perto está aberto hoje?", "Há um percurso fácil aberto perto?"],
              fr: ["Quelle rando proche est ouverte aujourd'hui ?", "Y a-t-il une rando facile ouverte à côté ?"],
              de: ["Welcher Weg in der Nähe ist heute geöffnet?", "Gibt es eine leichte geöffnete Wanderung in der Nähe?"],
              pl: ["Który szlak w pobliżu jest dziś otwarty?", "Czy w pobliżu jest łatwy otwarty szlak?"] },
    back: { en: ["Is there a bus from Santana to Funchal?", "Can I walk back to Pico do Areeiro?", "When should I book the taxi?"],
            pt: ["Há autocarro de Santana para o Funchal?", "Posso voltar a pé ao Pico do Areeiro?", "Para que hora marco o táxi?"],
            fr: ["Y a-t-il un bus de Santana à Funchal ?", "Puis-je revenir à pied au Pico do Areeiro ?", "Pour quelle heure réserver le taxi ?"],
            de: ["Fährt ein Bus von Santana nach Funchal?", "Kann ich zum Pico do Areeiro zurücklaufen?", "Für wann bestelle ich das Taxi?"],
            pl: ["Czy jest autobus z Santany do Funchal?", "Czy mogę wrócić pieszo na Pico do Areeiro?", "Na którą zamówić taksówkę?"] }
  };
  var CLOSED = {  // a closed trail: say so, then the open trails nearby, nothing else (owner, 2026-10-10)
    en: { line: "<b>CLOSED</b> on IFCN's official warnings list: don't walk it while it is closed.", near: "Open trails nearby", away: "away" },
    pt: { line: "<b>ENCERRADO</b> na lista oficial de avisos do IFCN: não o faça enquanto estiver encerrado.", near: "Percursos abertos perto", away: "de distância" },
    fr: { line: "<b>FERMÉ</b> sur la liste officielle des avis de l'IFCN : ne le parcourez pas tant qu'il est fermé.", near: "Sentiers ouverts à proximité", away: "" },
    de: { line: "<b>GESPERRT</b> laut offizieller Hinweisliste des IFCN: Gehen Sie ihn nicht, solange er gesperrt ist.", near: "Geöffnete Wege in der Nähe", away: "entfernt" },
    pl: { line: "<b>ZAMKNIĘTY</b> według oficjalnej listy komunikatów IFCN: nie wchodź na szlak, dopóki jest zamknięty.", near: "Otwarte szlaki w pobliżu", away: "" }
  };
  var U = UI[LANG] || UI.en;
  // the owner's devices (#skipgc on any page sets it, #countme clears it): chats answered but never recorded
  var OWNER = (function () { try { return localStorage.getItem("gc-skip") === "1"; } catch (e) { return false; } })();
  var CSS = "html,body{margin-top:0!important;padding-top:0!important}" +
    "#lvc{--lp:#f6f1e4;--li:#1f3a2c;--lm:#5d6b62;--lme:#d8ecd9;--lbar:#efe7d2;position:relative;width:100vw;margin:0 calc(50% - 50vw) 16px;" +
    "height:100svh;display:flex;flex-direction:column;background:var(--lp);color:var(--li);font:16px/1.45 system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;text-align:left}" +
    "#lvc *{box-sizing:border-box}#lvc .lvc-head{background:var(--li);color:#fff;padding:10px 16px;display:flex;gap:12px;align-items:center;flex:none}" +
    "#lvc .lvc-head img{width:40px;height:40px;border-radius:50%;background:#fff}#lvc .lvc-head b{display:block;font-size:16px}#lvc .lvc-head span{font-size:13px;opacity:.8}" +
    "#lvc .lvc-way{height:4px;flex:none;background:linear-gradient(90deg,#f2c230 50%,#c8372d 50%)}" +
    "#lvc .lvc-log{flex:1;overflow-y:auto;padding:14px 12px 8px;display:flex;flex-direction:column;gap:8px;overscroll-behavior:contain}" +
    "#lvc .lvc-q{align-self:center;font-size:13px;color:var(--lm);background:var(--lbar);border-radius:12px;padding:4px 10px;text-align:center}" +
    "#lvc .lvc-msg{max-width:88%;padding:9px 12px;border-radius:14px;box-shadow:0 1px 1px rgba(0,0,0,.08);overflow-wrap:anywhere}" +
    "#lvc .lvc-bot{align-self:flex-start;background:#fff;border-top-left-radius:4px}#lvc .lvc-me{align-self:flex-end;background:var(--lme);border-top-right-radius:4px}" +
    "#lvc .lvc-msg .h{display:block;font-weight:700;font-size:14px;color:var(--lm);margin-bottom:2px}#lvc .lvc-msg a{color:#1d6b45}" +
    "#lvc .lvc-msg img{display:block;width:100%;border-radius:10px}" +
    "#lvc .lvc-btns{display:flex;gap:8px;margin-top:8px;flex-wrap:wrap}#lvc .lvc-btns button{border:0;border-radius:16px;padding:7px 14px;font:inherit;font-size:15px;background:var(--li);color:#fff}" +
    "#lvc .lvc-btns button+button{background:#fff;color:var(--li);border:1px solid var(--li)}" +
    "#lvc .lvc-typing{align-self:flex-start;background:#fff;border-radius:14px;padding:12px 14px;display:flex;gap:4px}" +
    "#lvc .lvc-typing i{width:7px;height:7px;border-radius:50%;background:#9aa69e;animation:lvcb 1s infinite}" +
    "#lvc .lvc-typing i:nth-child(2){animation-delay:.15s}#lvc .lvc-typing i:nth-child(3){animation-delay:.3s}" +
    "@keyframes lvcb{0%,60%,100%{transform:translateY(0);opacity:.5}30%{transform:translateY(-4px);opacity:1}}" +
    "#lvc .lvc-chips{display:flex;gap:6px;overflow-x:auto;padding:6px 12px;flex:none}" +
    "#lvc .lvc-chips button{flex:none;border:1px solid var(--li);background:#fff;color:var(--li);border-radius:16px;padding:6px 12px;font:inherit;font-size:14px}" +
    "#lvc form{display:flex;gap:8px;padding:8px 12px;background:var(--lbar);flex:none;margin:0}" +
    "#lvc form input{flex:1;min-width:0;border:1px solid #e2dac6;border-radius:20px;padding:10px 14px;font:inherit;background:#fff;color:var(--li)}" +
    "#lvc form button{border:0;background:var(--li);color:#fff;border-radius:20px;padding:0 16px;font:inherit;font-weight:600}" +
    "#lvc .lvc-more{display:flex;justify-content:space-between;gap:8px;font-size:13px;padding:6px 12px 8px;background:var(--lbar);color:var(--lm);flex:none}" +
    "#lvc .lvc-more a{color:#1d6b45;font-weight:600;text-decoration:none}";

  var once = {};
  function ev(name) {  // one count per page view; engage.js sends it (or picks it up from the queue when it loads)
    if (once[name]) return; once[name] = true;
    if (window.LEVADINHO_EVENT) window.LEVADINHO_EVENT("chat-" + name);
    else (window.LEVADINHO_EVQ = window.LEVADINHO_EVQ || []).push("chat-" + name);
  }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function txt(el) { return el ? el.textContent.replace(/\s+/g, " ").trim() : ""; }
  function fmt(s) {  // the bot writes WhatsApp text: *bold*, bare links, line breaks
    return esc(s).replace(/\*([^*\n]+)\*/g, "<b>$1</b>")
      .replace(/(https?:\/\/[^\s<]+[^\s<.,)])/g, '<a href="$1" target="_blank" rel="noopener">$1</a>').replace(/\n/g, "<br>");
  }
  function clean(html) { return html.replace(/<!--[\s\S]*?-->/g, "").replace(/\sid="[^"]*"/g, "").replace(/<\/?(div|p|span)[^>]*>/g, " ").replace(/\s+/g, " ").trim(); }
  function wait(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }

  function openingRows() {
    var rows = [], card = document.getElementById("answers");
    if (card) {
      card.querySelectorAll(".qa-row").forEach(function (r) {
        var a = r.querySelector(".qa-a"), body = a ? clean(a.innerHTML) : "";
        if (txt(a)) rows.push([txt(r.querySelector(".qa-q")), body]);
      });
      return { rows: rows, kind: "trail" };
    }
    var dec = document.getElementById("decide"), taxi = document.getElementById("taxi");
    if (!dec) return guideRows();
    var warn = dec.previousElementSibling;
    if (warn && warn.tagName === "DIV" && txt(warn)) rows.push(["", clean(warn.innerHTML)]);
    var lines = [];
    dec.querySelectorAll("tbody tr").forEach(function (tr) {
      var td = tr.querySelectorAll("td");
      if (td.length >= 3) lines.push("<b>" + esc(txt(td[0])) + "</b>: " + esc(txt(td[1])) + " (" + esc(txt(td[2])) + ")");
    });
    if (lines.length) rows.push([txt(dec.querySelector("h2")), lines.join("<br>")]);
    if (taxi) {
      var ranks = [];
      taxi.querySelectorAll("tbody tr").forEach(function (tr) {
        var td = tr.querySelectorAll("td");
        if (td.length >= 2) ranks.push("<b>" + esc(txt(td[0])) + "</b> " + esc(txt(td[1])));
      });
      rows.push([txt(taxi.querySelector("h2")), esc(txt(taxi.querySelector("p"))) + (ranks.length ? "<br>" + ranks.join("<br>") : "")]);
    }
    return { rows: rows, kind: "back" };
  }

  // a question page: its lead paragraph answers the title; its FAQ questions (verbatim visible text) become the chips,
  // skipping the first, which restates the title the lead has just answered
  function guideRows() {
    var sub = document.querySelector("p.sub"), h1 = txt(document.querySelector("h1")).toLowerCase(), qs = [], faq = {};
    if (!txt(sub)) return null;
    document.querySelectorAll('script[type="application/ld+json"]').forEach(function (s) {
      try {
        [].concat(JSON.parse(s.textContent)).forEach(function (d) {
          [].concat(d["@graph"] || d).forEach(function (x) {
            if (x && x["@type"] === "FAQPage") [].concat(x.mainEntity || []).forEach(function (q) {
              if (q && q.name && q.name.trim().toLowerCase() !== h1) {
                qs.push(q.name.trim());
                faq[q.name.trim()] = q.acceptedAnswer && q.acceptedAnswer.text ? esc(q.acceptedAnswer.text) : "";
              }
            });
          });
        });
      } catch (e) {}
    });
    return { rows: [["", esc(txt(sub))]], kind: "guide", chips: qs.slice(1, 4), faq: faq };
  }

  // the page's own answer to one of its FAQ questions: the visible section under the heading with that exact text
  // (paragraphs, lists, a table as lines, the first picture), else the FAQ schema's answer (the same words)
  function pageAnswer(q, fallback) {
    var hs = document.querySelectorAll("h2, h3"), h = null, key = q.replace(/\s+/g, " ").trim().toLowerCase();
    for (var i = 0; i < hs.length && !h; i++) if (txt(hs[i]).toLowerCase() === key) h = hs[i];
    if (!h) return fallback;
    var parts = [], el = h.nextElementSibling;
    for (; el && !/^H[1-3]$/.test(el.tagName) && parts.length < 8; el = el.nextElementSibling) {
      if (el.tagName === "P" && txt(el)) parts.push(clean(el.innerHTML));
      else if (el.tagName === "UL" || el.tagName === "OL")
        parts.push([].map.call(el.querySelectorAll("li"), function (li) { return "• " + clean(li.innerHTML); }).join("<br>"));
      else {
        var tb = el.tagName === "TABLE" ? el : el.querySelector("table"), im = el.tagName === "IMG" ? el : el.querySelector("img");
        if (tb) {
          var lines = [];
          tb.querySelectorAll("tbody tr").forEach(function (tr) {
            var c = [].map.call(tr.querySelectorAll("th,td"), function (td) { return esc(txt(td)); }).filter(Boolean);
            if (c.length) lines.push("<b>" + c[0] + "</b> " + c.slice(1).join(" · "));
          });
          if (lines.length) parts.push(lines.join("<br>"));
        } else if (im && im.getAttribute("src")) {
          parts.push('<img alt="" src="' + esc(im.currentSrc || im.getAttribute("src")) + '">');
        }
      }
    }
    return parts.length ? parts.join("<br><br>") : fallback;
  }

  // CLOSED on today's list → [status row, open nearby trails row]; otherwise null (status.json, same as the card)
  async function closedRows() {
    var card = document.querySelector("#answers [data-trail]");
    if (!card) return null;
    var code = card.getAttribute("data-trail"), st;
    try { st = await (await fetch("/status.json", { cache: "no-store" })).json(); } catch (e) { return null; }
    var by = {}; (st.trails || []).forEach(function (t) { by[t.code] = t; });
    if (!by[code] || by[code].status !== "CLOSED") return null;
    var C = CLOSED[LANG] || CLOSED.en, note = by[code].note;
    note = note && typeof note === "object" ? (note[LANG] || note.en || "") : (note || "");
    var rows = [[txt(document.querySelector("#answers .qa-q")), C.line + (note ? " " + esc(note) : "")]];
    var open = [];
    document.querySelectorAll("#nearby li a").forEach(function (a) {
      var m = txt(a).match(/^(PR[\d.]+)/), t = m && by[m[1]];
      if (t && t.status === "OPEN") {
        var km = a.querySelector("span") ? txt(a.querySelector("span")) : "";
        open.push('<a href="' + a.getAttribute("href") + '">' + esc(txt(a).replace(km, "").trim()) + "</a>" + (km ? " · " + esc(km) : ""));
      }
    });
    if (open.length) rows.push([C.near, open.join("<br>")]);
    return rows;
  }

  function build() {
    var open = openingRows();
    var waLink = document.querySelector('a[href*="wa.me/447455718697"]');
    var tag = waLink ? (decodeURIComponent(waLink.getAttribute("href")).match(/#(web-[a-z0-9-]+)/) || [])[1] : null;
    if (!open || !open.rows.length || !tag) return false;
    var st = document.createElement("style"); st.textContent = CSS; document.head.appendChild(st);
    var sec = document.createElement("section");
    sec.id = "lvc"; sec.setAttribute("aria-label", "Levadinho");
    sec.innerHTML = '<div class="lvc-head"><img src="/img/icon-192.png" alt=""><div><b>Levadinho</b><span class="lvc-sub"></span></div></div>' +
      '<div class="lvc-way"></div><div class="lvc-log" aria-live="polite"></div><div class="lvc-chips"></div>' +
      '<form autocomplete="off"><input maxlength="500" enterkeyhint="send"><button></button></form>' +
      '<div class="lvc-more"><a class="lvc-down" href="#"></a><a class="lvc-wa" href="#"></a></div>';
    document.body.insertBefore(sec, document.body.firstChild);
    var log = sec.querySelector(".lvc-log"), sub = sec.querySelector(".lvc-sub"), chipsEl = sec.querySelector(".lvc-chips");
    var input = sec.querySelector("input"), down = sec.querySelector(".lvc-down"), wa = sec.querySelector(".lvc-wa");
    sub.textContent = U.online; input.placeholder = U.ph; sec.querySelector("form button").textContent = U.send;
    down.textContent = U.more; wa.textContent = U.wa; wa.href = waLink.getAttribute("href");
    var target = document.getElementById("answers") || document.querySelector("h1");
    down.addEventListener("click", function (e) { e.preventDefault(); ev("down"); if (target) target.scrollIntoView({ behavior: "smooth" }); });
    wa.addEventListener("click", function () { ev("wa"); });
    var sid; try { sid = localStorage.getItem("lvchat"); } catch (e) {}
    if (!sid || !/^[a-z0-9]{12,32}$/.test(sid)) { sid = (Math.random().toString(36) + Math.random().toString(36)).replace(/[^a-z0-9]/g, "").slice(0, 20); try { localStorage.setItem("lvchat", sid); } catch (e) {} }

    function scroll() { log.scrollTo({ top: log.scrollHeight, behavior: "smooth" }); }
    function add(cls, html) { var d = document.createElement("div"); d.className = cls; d.innerHTML = html; log.appendChild(d); scroll(); return d; }
    function typing() { sub.textContent = U.typing; return add("lvc-typing", "<i></i><i></i><i></i>"); }
    function done(t) { if (t) t.remove(); sub.textContent = U.online; }
    async function typeOut(el, html) {
      var parts = html.match(/<[^>]+>|[^<\s]+\s*|\s+/g) || [], out = "";
      for (var i = 0; i < parts.length; i++) { out += parts[i]; el.innerHTML = out; if (parts[i][0] !== "<") await wait(18); }
      scroll();
    }
    function chips() {
      chipsEl.innerHTML = "";
      var list = open.chips || (CHIPS[open.kind] ? CHIPS[open.kind][LANG] || CHIPS[open.kind].en : []);
      list.forEach(function (s) {
        var b = document.createElement("button"); b.type = "button"; b.textContent = s;
        b.onclick = function () { open.faq && open.faq[s] !== undefined ? faqAnswer(s) : ask(s, "chip"); }; chipsEl.appendChild(b);
      });
    }
    async function show(msgs) {
      for (var i = 0; i < msgs.length; i++) {
        var m = msgs[i];
        if (m.type === "image") { var im = add("lvc-msg lvc-bot", '<img alt="" src="' + esc(m.url) + '">'); im.querySelector("img").onload = scroll; continue; }
        var el = add("lvc-msg lvc-bot", "");
        await typeOut(el, fmt(m.body || ""));
        if (m.type === "buttons") {
          var bx = document.createElement("div"); bx.className = "lvc-btns";
          m.buttons.forEach(function (b) {
            var btn = document.createElement("button"); btn.type = "button"; btn.textContent = b[1];
            btn.onclick = function () {
              if (b[0] === "consent_yes") ev("accept"); else if (b[0] === "consent_no") ev("decline");
              bx.remove(); add("lvc-msg lvc-me", esc(b[1])); send({ choice: b[0] });
            };
            bx.appendChild(btn);
          });
          el.appendChild(bx); scroll();
        }
        if (m.type === "location_request" && navigator.geolocation) {  // "bus now": the nearest stop needs a position
          var lx = document.createElement("div"); lx.className = "lvc-btns";
          var lb = document.createElement("button"); lb.type = "button"; lb.textContent = U.loc;
          lb.onclick = function () {
            ev("location"); lx.remove(); add("lvc-msg lvc-me", esc(U.loc));
            navigator.geolocation.getCurrentPosition(
              function (p) { send({ location: { lat: p.coords.latitude, lon: p.coords.longitude } }); },
              function () { add("lvc-msg lvc-bot", esc(U.locNo)); },
              { enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 });
          };
          lx.appendChild(lb); el.appendChild(lx); scroll();
        }
      }
    }
    var busy = false;
    async function send(payload) {
      if (busy) return; busy = true;
      var t = typing(), told = false;
      try {
        for (var i = 0; i < 30; i++) {
          var r = await fetch(API + "/webchat", { method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify(Object.assign({ sid: sid, tag: tag, lang: LANG, test: OWNER }, payload)) });
          if (!r.ok) throw new Error(r.status);
          var j = await r.json();
          if (j.waking) {
            if (!told) { done(t); await show(j.messages || []); t = typing(); told = true; }
            if (j.retry) payload = { text: j.retry };
            await wait(10000); continue;
          }
          done(t); t = null;
          var notice = (j.messages || []).some(function (m) {  // the privacy notice is not an answer
            return m.type === "buttons" && (m.buttons || []).some(function (x) { return x[0] === "consent_yes"; });
          });
          if (!notice && (j.messages || []).length) ev("answered");
          await show(j.messages || []);
          break;
        }
      } catch (e) { done(t); t = null; ev("error"); add("lvc-msg lvc-bot", esc(U.err)); }
      if (t) { done(t); ev("error"); add("lvc-msg lvc-bot", esc(U.slow)); }
      busy = false;
    }
    async function faqAnswer(q) {  // a guide page's own FAQ: the page's words, no model
      if (busy) return; busy = true;
      ev("ask-faq");
      open.chips = open.chips.filter(function (c) { return c !== q; });
      chipsEl.innerHTML = "";
      add("lvc-msg lvc-me", esc(q));
      var t = typing(); await wait(600); done(t);
      var el = add("lvc-msg lvc-bot", ""), html = pageAnswer(q, open.faq[q]);
      if (/<img/.test(html)) { el.innerHTML = html; el.querySelectorAll("img").forEach(function (i) { i.onload = scroll; }); scroll(); }
      else await typeOut(el, html);
      busy = false;
      chips();
    }
    function ask(text, how) {
      text = (text || "").trim();
      if (!text || busy) return;
      ev("ask-" + (how || "typed"));
      chipsEl.innerHTML = "";
      add("lvc-msg lvc-me", esc(text));
      send({ text: text });
    }
    sec.querySelector("form").onsubmit = function (e) { e.preventDefault(); var v = input.value; input.value = ""; ask(v); };
    (async function opening() {
      var h1 = document.querySelector("h1");
      if (h1) add("lvc-q", esc(txt(h1)));
      await wait(500);  // status.js fills the card's live status first
      var fresh = openingRows() || open;
      var closed = open.kind === "trail" ? await closedRows() : null;
      if (closed) { fresh = { rows: closed, kind: "closed" }; open.kind = "closed"; }
      for (var i = 0; i < fresh.rows.length; i++) {
        var t = typing(); await wait(600); done(t);
        var m = add("lvc-msg lvc-bot", fresh.rows[i][0] ? '<span class="h">' + esc(fresh.rows[i][0]) + "</span>" : "");
        var b = document.createElement("span"); m.appendChild(b);
        await typeOut(b, fresh.rows[i][1]);
      }
      var t2 = typing(); await wait(400); done(t2);
      if ((open.chips || CHIPS[open.kind] || []).length !== 0) add("lvc-msg lvc-bot", esc(U.more2));
      chips();
    })();
    return true;
  }

  function start() {
    var ctl = window.AbortController ? new AbortController() : null;
    var timer = setTimeout(function () { if (ctl) ctl.abort(); }, 2500);
    fetch(API + "/health", { signal: ctl ? ctl.signal : undefined, cache: "no-store" })
      .then(function (r) { clearTimeout(timer); return r.ok ? r.json() : null; })
      .then(function (j) { ev(!(j && j.ok && j.model) ? "off" : build() ? "shown" : "none"); })  // asleep or off: the usual page
      .catch(function () { ev("off"); });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();
