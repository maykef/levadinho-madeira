/* Levadinho — renders the live "trails: open or closed today?" dashboard from
   /status.json (the same file the per-trail cards use). Language comes from
   <html lang>. Wording lives in LANGS; the trail data is language-neutral. */
(function () {
  "use strict";

  var LANGS = {
    en: {
      nofee: "No IFCN fee",
      updated: "checked", ifcnUpd: "IFCN list updated", mtime: "(Madeira time)",
      open: "open", restricted: "restricted", closed: "closed",
      changed: "⚠ Changed today", changedSub: "restricted & closed — check before you go",
      openToday: "Open today", openSub: "booking still required",
      badge: { OPEN: "OPEN", PARTIAL: "RESTRICTED", CLOSED: "CLOSED" },
      defNote: { PARTIAL: "Access restricted — read the official note before you go.", CLOSED: "Closed by IFCN." },
      region: { summit: "Summit", north: "North", west: "West", east: "East", south: "Coast" },
      wind: "wind", rain: "rain", fog: "likely in cloud",
      today: "Today's status →", nomatch: "No trail matches that.",
      mmnote: "mountain ≠ coast; fog and wind change fast up high.",
      loading: "Live status is loading… if it doesn't appear, check the official sources below.",
      xfNoVert: "No vertigo", xfTunnels: "Has tunnels",
      xfNote: "Only trails with sourced tunnel/vertigo data are shown (mostly IFCN trailhead panels)."
    },
    pt: {
      nofee: "Sem taxa IFCN",
      updated: "verificado", ifcnUpd: "Lista IFCN atualizada", mtime: "(hora da Madeira)",
      open: "abertos", restricted: "condicionados", closed: "fechados",
      changed: "⚠ Alterações hoje", changedSub: "condicionados e fechados — confirme antes de ir",
      openToday: "Abertos hoje", openSub: "a reserva continua obrigatória",
      badge: { OPEN: "ABERTO", PARTIAL: "CONDICIONADO", CLOSED: "FECHADO" },
      defNote: { PARTIAL: "Acesso condicionado — leia a nota oficial antes de ir.", CLOSED: "Fechado pelo IFCN." },
      region: { summit: "Cume", north: "Norte", west: "Oeste", east: "Leste", south: "Costa" },
      wind: "vento", rain: "chuva", fog: "provavelmente dentro das nuvens",
      today: "Estado de hoje →", nomatch: "Nenhum percurso corresponde à pesquisa.",
      mmnote: "montanha ≠ costa; o nevoeiro e o vento mudam depressa em altitude.",
      loading: "O estado em direto está a carregar… se não aparecer, consulte as fontes oficiais abaixo.",
      xfNoVert: "Sem vertigens", xfTunnels: "Com túneis",
      xfNote: "Só são mostrados os percursos com dados documentados sobre túneis/vertigens (sobretudo painéis do IFCN).",
      decimalComma: true
    },
    fr: {
      nofee: "Sans taxe IFCN",
      updated: "vérifié", ifcnUpd: "Liste IFCN mise à jour", mtime: "(heure de Madère)",
      open: "ouverts", restricted: "restreints", closed: "fermés",
      changed: "⚠ Changements aujourd'hui", changedSub: "restreints & fermés — à vérifier avant de partir",
      openToday: "Ouverts aujourd'hui", openSub: "réservation toujours obligatoire",
      badge: { OPEN: "OUVERT", PARTIAL: "RESTREINT", CLOSED: "FERMÉ" },
      defNote: { PARTIAL: "Accès restreint — lisez la note officielle avant de partir.", CLOSED: "Fermé par l'IFCN." },
      region: { summit: "Sommet", north: "Nord", west: "Ouest", east: "Est", south: "Côte" },
      wind: "vent", rain: "pluie", fog: "sans doute dans les nuages",
      today: "État du jour →", nomatch: "Aucun sentier ne correspond.",
      mmnote: "montagne ≠ côte ; le brouillard et le vent changent vite en altitude.",
      xfNoVert: "Sans vertige", xfTunnels: "Avec tunnels",
      xfNote: "Seuls les sentiers avec des données sourcées sur les tunnels et le vertige sont affichés (surtout les panneaux IFCN)."
    },
    de: {
      nofee: "Keine IFCN-Gebühr",
      updated: "geprüft", ifcnUpd: "IFCN-Liste aktualisiert", mtime: "(Madeira-Zeit)",
      open: "offen", restricted: "eingeschränkt", closed: "gesperrt",
      changed: "⚠ Heute geändert", changedSub: "eingeschränkt & gesperrt — vor dem Start prüfen",
      openToday: "Heute offen", openSub: "Buchung weiterhin erforderlich",
      badge: { OPEN: "OFFEN", PARTIAL: "EINGESCHRÄNKT", CLOSED: "GESPERRT" },
      defNote: { PARTIAL: "Zugang eingeschränkt — lesen Sie vor dem Start den offiziellen Hinweis.", CLOSED: "Von IFCN gesperrt." },
      region: { summit: "Gipfel", north: "Norden", west: "Westen", east: "Osten", south: "Küste" },
      wind: "Wind", rain: "Regen", fog: "wohl in Wolken",
      today: "Heutiger Status →", nomatch: "Kein Weg passt dazu.",
      mmnote: "Berg ≠ Küste; Nebel und Wind ändern sich oben schnell.",
      xfNoVert: "Ohne Schwindelgefahr", xfTunnels: "Mit Tunneln",
      xfNote: "Nur Wege mit belegten Tunnel-/Schwindel-Daten werden angezeigt (meist IFCN-Infotafeln)."
    },
    pl: {
      nofee: "Bez opłaty IFCN",
      updated: "sprawdzono", ifcnUpd: "Lista IFCN zaktualizowana", mtime: "(czas Madery)",
      open: "otwarte", restricted: "ograniczone", closed: "zamknięte",
      changed: "⚠ Zmiany dzisiaj", changedSub: "ograniczone i zamknięte — sprawdź przed wyjściem",
      openToday: "Otwarte dzisiaj", openSub: "rezerwacja nadal wymagana",
      badge: { OPEN: "OTWARTY", PARTIAL: "OGRANICZONY", CLOSED: "ZAMKNIĘTY" },
      defNote: { PARTIAL: "Dostęp ograniczony — przed wyjściem przeczytaj oficjalną uwagę.", CLOSED: "Zamknięte przez IFCN." },
      region: { summit: "Szczyt", north: "Północ", west: "Zachód", east: "Wschód", south: "Wybrzeże" },
      wind: "wiatr", rain: "deszcz", fog: "pewnie we mgle",
      today: "Dzisiejszy status →", nomatch: "Brak pasujących szlaków.",
      mmnote: "góry ≠ wybrzeże; mgła i wiatr szybko się zmieniają na wysokości.",
      xfNoVert: "Bez lęku wysokości", xfTunnels: "Z tunelami",
      xfNote: "Pokazano tylko szlaki z udokumentowanymi danymi o tunelach i ekspozycji (głównie tablice IFCN)."
    }
  };

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function el(id) { return document.getElementById(id); }
  // Decimal comma + trailing euro sign where the language expects it (pt).
  function num(n, T) { return T.decimalComma ? String(n).replace(".", ",") : String(n); }
  // fee null = classified PR run by another body (e.g. Funchal council): no IFCN fee, not on SIMplifica.
  function fee(f, T) { if (f == null) return T.nofee; return T.decimalComma ? num(f, T) + " €" : "€" + f; }

  function noteFor(t, T, lang) {
    if (t.note) {
      if (typeof t.note === "string") return t.note;
      if (t.note[lang]) return t.note[lang];
      if (t.note.en) return t.note.en;
      for (var k in t.note) { if (t.note[k]) return t.note[k]; }
    }
    return T.defNote[t.status] || "";
  }

  // Tunnel / exposure data from /trail_extras.json (null = no sourced data).
  var EXTRAS = null;
  function xattrs(code) {
    var x = EXTRAS && EXTRAS[code];
    if (!x) return ' data-exp="" data-tun=""';
    var tun = x.tunnels === true || x.torch === "yes" || x.torch === "recommended";
    return ' data-exp="' + esc(x.exposure || "") + '" data-tun="' + (tun ? "1" : "") + '"';
  }

  function card(t, T, lang, showNote) {
    var temp = (t.temp != null) ? " · " + num(t.temp, T) + "°C" : "";
    // status.json holds the English path; pt/fr/de/pl boards link to their own spoke.
    var page = t.page && LANGS[lang] && lang !== "en" ? "/" + lang + t.page : t.page;
    // Descriptive anchors: the trail name is the link, and the CTA names its trail.
    var link = page ? '<a class="tlink" href="' + esc(page) + '">' + esc(t.code) + ": " + T.today + "</a>" : "";
    var tname = page ? '<a class="tname" href="' + esc(page) + '">' : '<span class="tname">';
    var note = showNote ? '<div class="tnote">' + esc(noteFor(t, T, lang)) + "</div>" : "";
    var key = (t.name + " " + t.code).toLowerCase();
    return '<div class="tcard ' + t.status + '" data-status="' + t.status + '" data-key="' + esc(key) +
      '" data-pop="' + (t.popular ? 1 : 0) + '"' + xattrs(t.code) + '>' +
      // Code first (2026-10-03): matches the trail-page titles and the bare-code searches ("pr9.1").
      '<div class="trow">' + tname + '<span class="tcode">' + esc(t.code) + "</span> " + esc(t.name) +
      (page ? "</a>" : "</span>") + '<span class="tbadge ' + t.status + '">' + T.badge[t.status] + "</span></div>" +
      note +
      '<div class="tmeta"><span class="tfee">' + esc(fee(t.fee, T)) + temp + "</span>" + link + "</div></div>";
  }

  function render(d, T, lang) {
    var c = d.counts || { OPEN: 0, PARTIAL: 0, CLOSED: 0 };
    el("summary").innerHTML =
      '<span class="upd">' + ((d.source || {}).updated ? T.ifcnUpd + " <b>" + esc(d.source.updated) + "</b> · " : "") +
        T.updated + " " + esc(d.stamp) + " " + T.mtime + "</span>" +
      '<span><span class="dot OPEN"></span><b>' + c.OPEN + "</b> " + T.open + "</span>" +
      '<span><span class="dot PARTIAL"></span><b>' + c.PARTIAL + "</b> " + T.restricted + "</span>" +
      '<span><span class="dot CLOSED"></span><b>' + c.CLOSED + "</b> " + T.closed + "</span>";

    el("weatherStrip").innerHTML = (d.regions || []).map(function (r) {
      var t = (r.temp != null) ? num(r.temp, T) + "°C" : "—";
      var bits = [];
      if (r.wind != null) bits.push(T.wind + " " + r.wind + " km/h");
      if (r.rain != null && r.rain > 0) bits.push('<span class="alert">' + T.rain + " " + num(r.rain, T) + " mm</span>");
      if (r.in_cloud) bits.push('<span class="alert">' + T.fog + "</span>");
      return '<div class="wx"><b>' + T.region[r.key] + " · " + esc(r.place) + "</b>" +
        '<span class="wtemp">' + t + "</span>" +
        (bits.length ? '<span class="wext">' + bits.join(" · ") + "</span>" : "") + "</div>";
    }).join("") + '<div class="note">' + T.mmnote + "</div>";

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
    var filter = "all", q = "", xf = { novert: false, tunnels: false };
    function apply() {
      var cards = document.querySelectorAll(".tcard"), any = false;
      cards.forEach(function (el2) {
        var okF = filter === "all" || (filter === "popular" ? el2.dataset.pop === "1" : el2.dataset.status === filter);
        var okQ = !q || el2.dataset.key.indexOf(q) !== -1;
        // Tunnel / vertigo toggles: trails without sourced data are hidden while one is on.
        var okX = (!xf.novert || el2.dataset.exp === "low") && (!xf.tunnels || el2.dataset.tun === "1");
        var show = okF && okQ && okX; el2.hidden = !show; if (show) any = true;
      });
      var xn = el("xfNote"); if (xn) xn.hidden = !(xf.novert || xf.tunnels);
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
      var x = e.target.closest("[data-xf]");
      if (x) { toggleX(x); return; }
      var b = e.target.closest("[data-filter]"); if (!b) return;
      filter = b.dataset.filter;
      chips.querySelectorAll(".chip[data-filter]").forEach(function (c) { c.classList.toggle("on", c === b); });
      apply();
    });
    function toggleX(x) {
      var k = x.dataset.xf; xf[k] = !xf[k];
      x.classList.toggle("on", xf[k]); x.setAttribute("aria-pressed", xf[k] ? "true" : "false");
      apply();
    }
    // Add the two toggles only when /trail_extras.json loaded (fail quietly otherwise).
    if (chips && EXTRAS && !chips.querySelector("[data-xf]")) {
      [["novert", T.xfNoVert || LANGS.en.xfNoVert], ["tunnels", T.xfTunnels || LANGS.en.xfTunnels]].forEach(function (p) {
        var s = document.createElement("span");
        s.className = "chip"; s.dataset.xf = p[0]; s.textContent = p[1];
        s.setAttribute("role", "button"); s.setAttribute("tabindex", "0"); s.setAttribute("aria-pressed", "false");
        s.addEventListener("keydown", function (e) {
          if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggleX(s); }
        });
        chips.appendChild(s);
      });
      var n = document.createElement("p");
      n.id = "xfNote"; n.hidden = true;
      n.style.cssText = "font-size:13px;color:#4A5F56;margin:6px 0 0";
      n.textContent = T.xfNote || LANGS.en.xfNote;
      chips.insertAdjacentElement("afterend", n);
    }
  }

  var root = el("trailBoard");
  if (!root) return;
  var lang = (document.documentElement.lang || "en").slice(0, 2).toLowerCase();
  var T = LANGS[lang] || LANGS.en;
  // Optional: tunnel / exposure data. A missing or broken file just means no toggles.
  var extrasP = fetch("/trail_extras.json", { cache: "no-cache" })
    .then(function (r) { return r.ok ? r.json() : null; })
    .catch(function () { return null; });
  fetch("/status.json", { cache: "no-cache" })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      return extrasP.then(function (x) { EXTRAS = (x && typeof x === "object") ? x : null; render(d, T, lang); });
    })
    .catch(function () { root.innerHTML = '<p style="color:#4A5F56">' + esc(T.loading || LANGS.en.loading) + "</p>"; });
})();
