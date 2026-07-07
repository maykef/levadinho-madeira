/* Levadinho — renders the live "trails: open or closed today?" dashboard from
   /status.json (the same file the per-trail cards use). Language comes from
   <html lang>. Wording lives in LANGS; the trail data is language-neutral. */
(function () {
  "use strict";

  var LANGS = {
    en: {
      updated: "Updated", mtime: "(Madeira time)",
      open: "open", restricted: "restricted", closed: "closed",
      changed: "⚠ Changed today", changedSub: "restricted & closed — check before you go",
      openToday: "Open today", openSub: "booking still required",
      badge: { OPEN: "OPEN", PARTIAL: "RESTRICTED", CLOSED: "CLOSED" },
      defNote: { PARTIAL: "Access restricted — read the official note before you go.", CLOSED: "Closed by IFCN." },
      region: { summit: "Summit", north: "North", west: "West", east: "East", south: "Coast" },
      today: "Today's status →", nomatch: "No trail matches that.",
      mmnote: "mountain ≠ coast; fog and wind change fast up high."
    },
    fr: {
      updated: "Mis à jour", mtime: "(heure de Madère)",
      open: "ouverts", restricted: "restreints", closed: "fermés",
      changed: "⚠ Changements aujourd'hui", changedSub: "restreints & fermés — à vérifier avant de partir",
      openToday: "Ouverts aujourd'hui", openSub: "réservation toujours obligatoire",
      badge: { OPEN: "OUVERT", PARTIAL: "RESTREINT", CLOSED: "FERMÉ" },
      defNote: { PARTIAL: "Accès restreint — lisez la note officielle avant de partir.", CLOSED: "Fermé par l'IFCN." },
      region: { summit: "Sommet", north: "Nord", west: "Ouest", east: "Est", south: "Côte" },
      today: "État du jour →", nomatch: "Aucun sentier ne correspond.",
      mmnote: "montagne ≠ côte ; le brouillard et le vent changent vite en altitude."
    },
    de: {
      updated: "Aktualisiert", mtime: "(Madeira-Zeit)",
      open: "offen", restricted: "eingeschränkt", closed: "gesperrt",
      changed: "⚠ Heute geändert", changedSub: "eingeschränkt & gesperrt — vor dem Start prüfen",
      openToday: "Heute offen", openSub: "Buchung weiterhin erforderlich",
      badge: { OPEN: "OFFEN", PARTIAL: "EINGESCHRÄNKT", CLOSED: "GESPERRT" },
      defNote: { PARTIAL: "Zugang eingeschränkt — lesen Sie vor dem Start den offiziellen Hinweis.", CLOSED: "Von IFCN gesperrt." },
      region: { summit: "Gipfel", north: "Norden", west: "Westen", east: "Osten", south: "Küste" },
      today: "Heutiger Status →", nomatch: "Kein Weg passt dazu.",
      mmnote: "Berg ≠ Küste; Nebel und Wind ändern sich oben schnell."
    },
    pl: {
      updated: "Zaktualizowano", mtime: "(czas Madery)",
      open: "otwarte", restricted: "ograniczone", closed: "zamknięte",
      changed: "⚠ Zmiany dzisiaj", changedSub: "ograniczone i zamknięte — sprawdź przed wyjściem",
      openToday: "Otwarte dzisiaj", openSub: "rezerwacja nadal wymagana",
      badge: { OPEN: "OTWARTY", PARTIAL: "OGRANICZONY", CLOSED: "ZAMKNIĘTY" },
      defNote: { PARTIAL: "Dostęp ograniczony — przed wyjściem przeczytaj oficjalną uwagę.", CLOSED: "Zamknięte przez IFCN." },
      region: { summit: "Szczyt", north: "Północ", west: "Zachód", east: "Wschód", south: "Wybrzeże" },
      today: "Dzisiejszy status →", nomatch: "Brak pasujących szlaków.",
      mmnote: "góry ≠ wybrzeże; mgła i wiatr szybko się zmieniają na wysokości."
    }
  };

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function el(id) { return document.getElementById(id); }

  function noteFor(t, T, lang) {
    if (t.note) return (typeof t.note === "string") ? t.note : (t.note[lang] || t.note.en || "");
    return T.defNote[t.status] || "";
  }

  function card(t, T, lang, showNote) {
    var temp = (t.temp != null) ? " · " + t.temp + "°C" : "";
    var link = t.page ? '<a class="tlink" href="' + esc(t.page) + '">' + T.today + "</a>" : "";
    var note = showNote ? '<div class="tnote">' + esc(noteFor(t, T, lang)) + "</div>" : "";
    var key = (t.name + " " + t.code).toLowerCase();
    return '<div class="tcard ' + t.status + '" data-status="' + t.status + '" data-key="' + esc(key) +
      '" data-pop="' + (t.popular ? 1 : 0) + '">' +
      '<div class="trow"><span class="tname">' + esc(t.name) + ' <span class="tcode">' + esc(t.code) +
      '</span></span><span class="tbadge ' + t.status + '">' + T.badge[t.status] + "</span></div>" +
      note +
      '<div class="tmeta"><span class="tfee">€' + esc(t.fee) + temp + "</span>" + link + "</div></div>";
  }

  function render(d, T, lang) {
    var c = d.counts || { OPEN: 0, PARTIAL: 0, CLOSED: 0 };
    el("summary").innerHTML =
      '<span class="upd">' + T.updated + " <b>" + esc(d.stamp) + "</b> " + T.mtime + "</span>" +
      '<span><span class="dot OPEN"></span><b>' + c.OPEN + "</b> " + T.open + "</span>" +
      '<span><span class="dot PARTIAL"></span><b>' + c.PARTIAL + "</b> " + T.restricted + "</span>" +
      '<span><span class="dot CLOSED"></span><b>' + c.CLOSED + "</b> " + T.closed + "</span>";

    el("weatherStrip").innerHTML = (d.regions || []).map(function (r) {
      var t = (r.temp != null) ? " " + r.temp + "°C" : " —";
      return '<span class="wx"><b>' + T.region[r.key] + " · " + esc(r.place) + "</b>" + t + "</span>";
    }).join("") + '<span class="note">— ' + T.mmnote + "</span>";

    var trails = (d.trails || []).slice();
    var byPop = function (a, b) { return (b.popular - a.popular) || a.code.localeCompare(b.code, undefined, { numeric: true }); };
    var changed = trails.filter(function (t) { return t.status !== "OPEN"; }).sort(byPop);
    var openT = trails.filter(function (t) { return t.status === "OPEN"; }).sort(byPop);

    var html = "";
    if (changed.length) {
      html += '<div class="sec-h"><h2>' + T.changed + '</h2><span class="count">' + T.changedSub + "</span></div>";
      html += '<div class="grid">' + changed.map(function (t) { return card(t, T, lang, true); }).join("") + "</div>";
    }
    html += '<div class="sec-h"><h2>' + T.openToday + '</h2><span class="count">' + openT.length + " · " + T.openSub + "</span></div>";
    html += '<div class="grid compact">' + openT.map(function (t) { return card(t, T, lang, false); }).join("") + "</div>";
    html += '<p id="noMatch" class="nomatch" hidden>' + T.nomatch + "</p>";
    el("trailBoard").innerHTML = html;

    wireFilters(T);
  }

  function wireFilters(T) {
    var search = el("trailSearch"), chips = el("chips");
    var filter = "all", q = "";
    function apply() {
      var cards = document.querySelectorAll(".tcard"), any = false;
      cards.forEach(function (el2) {
        var okF = filter === "all" || (filter === "popular" ? el2.dataset.pop === "1" : el2.dataset.status === filter);
        var okQ = !q || el2.dataset.key.indexOf(q) !== -1;
        var show = okF && okQ; el2.hidden = !show; if (show) any = true;
      });
      // hide a section header whose grid has no visible cards
      document.querySelectorAll(".grid").forEach(function (g) {
        var vis = g.querySelectorAll(".tcard:not([hidden])").length;
        if (g.previousElementSibling) g.previousElementSibling.hidden = !vis;
        g.hidden = !vis;
      });
      var nm = el("noMatch"); if (nm) nm.hidden = any;
    }
    if (search) search.addEventListener("input", function () { q = search.value.trim().toLowerCase(); apply(); });
    if (chips) chips.addEventListener("click", function (e) {
      var b = e.target.closest("[data-filter]"); if (!b) return;
      filter = b.dataset.filter;
      chips.querySelectorAll(".chip").forEach(function (c) { c.classList.toggle("on", c === b); });
      apply();
    });
  }

  var root = el("trailBoard");
  if (!root) return;
  var lang = (document.documentElement.lang || "en").slice(0, 2).toLowerCase();
  var T = LANGS[lang] || LANGS.en;
  fetch("/status.json", { cache: "no-cache" })
    .then(function (r) { return r.json(); })
    .then(function (d) { render(d, T, lang); })
    .catch(function () { root.innerHTML = '<p style="color:#4A5F56">Live status is loading… if it doesn\'t appear, check the official sources below.</p>'; });
})();
