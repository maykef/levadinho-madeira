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
      wlevel: {"yellow":"Yellow warning","orange":"Orange warning","red":"Red warning"}, wtype: {"wind":"wind","rain":"rain","thunder":"thunderstorms","fog":"fog","snow":"snow","sea":"rough sea","heat":"heat","cold":"cold","other":"weather"}, wgust: "gusts up to", wuntil: "until", wtomorrow: "tomorrow", wsrc: "IPMA",
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
      wlevel: {"yellow":"Aviso amarelo","orange":"Aviso laranja","red":"Aviso vermelho"}, wtype: {"wind":"vento","rain":"chuva","thunder":"trovoada","fog":"nevoeiro","snow":"neve","sea":"agitação marítima","heat":"tempo quente","cold":"tempo frio","other":"tempo"}, wgust: "rajadas até", wuntil: "até", wtomorrow: "amanhã", wsrc: "IPMA",
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
      wlevel: {"yellow":"Vigilance jaune","orange":"Vigilance orange","red":"Vigilance rouge"}, wtype: {"wind":"vent","rain":"pluie","thunder":"orages","fog":"brouillard","snow":"neige","sea":"mer agitée","heat":"chaleur","cold":"froid","other":"météo"}, wgust: "rafales jusqu'à", wuntil: "jusqu'à", wtomorrow: "demain", wsrc: "IPMA",
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
      wlevel: {"yellow":"Warnstufe Gelb","orange":"Warnstufe Orange","red":"Warnstufe Rot"}, wtype: {"wind":"Wind","rain":"Regen","thunder":"Gewitter","fog":"Nebel","snow":"Schnee","sea":"hoher Seegang","heat":"Hitze","cold":"Kälte","other":"Wetter"}, wgust: "Böen bis", wuntil: "bis", wtomorrow: "morgen", wsrc: "IPMA",
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
      wlevel: {"yellow":"Ostrzeżenie żółte","orange":"Ostrzeżenie pomarańczowe","red":"Ostrzeżenie czerwone"}, wtype: {"wind":"wiatr","rain":"deszcz","thunder":"burze","fog":"mgła","snow":"śnieg","sea":"wzburzone morze","heat":"upał","cold":"mróz","other":"pogoda"}, wgust: "porywy do", wuntil: "do", wtomorrow: "jutro", wsrc: "IPMA",
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
    var c = t.closure;   // a dated closure IFCN has announced (owner, 2026-10-11): always shown, with its dates
    if (c && c.state === "announced" && c.text)
      note += '<div class="tnote" style="color:var(--closed,#B3372E)"><b>⚠</b> ' + esc(c.text[lang] || c.text.en || "") + "</div>";
    var key = (t.name + " " + t.code).toLowerCase();
    return '<div class="tcard ' + t.status + '" data-status="' + t.status + '" data-key="' + esc(key) +
      '" data-pop="' + (t.popular ? 1 : 0) + '"' + xattrs(t.code) + '>' +
      // Code first (2026-10-03): matches the trail-page titles and the bare-code searches ("pr9.1").
      '<div class="trow">' + tname + '<span class="tcode">' + esc(t.code) + "</span> " + esc(t.name) +
      (page ? "</a>" : "</span>") + '<span class="tbadge ' + t.status + '">' + T.badge[t.status] + "</span></div>" +
      note +
      '<div class="tmeta"><span class="tfee">' + esc(fee(t.fee, T)) + temp + "</span>" + link + "</div></div>";
  }

  // ---- IPMA 5-day forecast (owner, 2026-11-08: "lead with the forecast 5 days ahead ... include rain"). Same block in
  // dashboard.js and status.js: keep them in sync. Day names, never dates. Data: status.json "forecast" (update_status.py).
  var FCW = {
    en: { today: "Today", rain: "rain", ri: ["", "light", "moderate", "heavy"], wind: "wind", head: "Next 5 days · IPMA forecast", now: "Now" },
    pt: { today: "Hoje", rain: "chuva", ri: ["", "fraca", "moderada", "forte"], wind: "vento", head: "Próximos 5 dias · previsão IPMA", now: "Agora" },
    fr: { today: "Aujourd'hui", rain: "pluie", ri: ["", "faible", "modérée", "forte"], wind: "vent", head: "5 prochains jours · prévision IPMA", now: "Maintenant" },
    de: { today: "Heute", rain: "Regen", ri: ["", "leicht", "mäßig", "stark"], wind: "Wind", head: "Nächste 5 Tage · IPMA-Vorhersage", now: "Jetzt" },
    pl: { today: "Dziś", rain: "deszcz", ri: ["", "słaby", "umiarkowany", "silny"], wind: "wiatr", head: "Najbliższe 5 dni · prognoza IPMA", now: "Teraz" }
  };
  function fcIcon(t) {
    if (t === 1) return "☀️";
    if (t === 2 || t === 3 || t === 25) return "⛅";
    if (t === 19 || t === 20 || t === 23) return "⛈️";
    if (t === 8 || t === 11 || t === 14 || t === 6 || t === 9 || t === 12) return "🌧️";
    if (t === 7 || t === 10 || t === 13 || t === 15) return "🌦️";
    if (t === 16 || t === 17 || t === 26) return "🌫️";
    if (t === 18 || t === 28) return "🌨️";
    if (t === 21) return "🧊";
    return "☁️";
  }
  function fcToday() { return new Intl.DateTimeFormat("en-CA", { timeZone: "Atlantic/Madeira" }).format(new Date()); }
  function fcDay(iso, lng) {   // "Today" or the weekday name in the page language
    if (iso === fcToday()) return (FCW[lng] || FCW.en).today;
    var n = new Intl.DateTimeFormat(lng, { weekday: "long", timeZone: "UTC" }).format(new Date(iso + "T12:00:00Z"));
    return n.charAt(0).toUpperCase() + n.slice(1);
  }
  function fcRows(days, lng, wide) {   // wide = one column per day (trail cards); else one line per day (homepage strip)
    var F = FCW[lng] || FCW.en, today = fcToday();
    var list = (days || []).filter(function (x) { return x.date >= today; }).slice(0, 5);
    if (!list.length) return "";
    var warn = "color:var(--partial,#8a5a00);font-weight:700";
    var cells = list.map(function (x) {
      var rain = x.rain_prob != null && x.rain_prob >= 20
        ? '<span style="' + (x.rain_prob >= 60 || (x.rain_int || 0) >= 2 ? warn : "") + '">' + F.rain + " " + x.rain_prob + "%" +
          ((x.rain_int || 0) >= 2 ? " · " + F.ri[x.rain_int] : "") + "</span>" : "";
      var strong = (x.wind_class || 0) >= 3 || (x.wind_kmh || 0) >= 50;
      var wind = x.wind_kmh != null && (strong || x.wind_kmh >= 30)
        ? '<span style="' + (strong ? warn : "") + '">' + F.wind + " " + x.wind_kmh + " km/h</span>" : "";
      var t = (x.tmin != null && x.tmax != null) ? x.tmin + "–" + x.tmax + "°" : "";
      var extra = [rain, wind].filter(Boolean).join(" · ");
      return wide
        ? '<div style="text-align:center;min-width:0"><div style="font-weight:700;font-size:12.5px">' + fcDay(x.date, lng) +
          '</div><div style="font-size:22px;line-height:1.2">' + fcIcon(x.type) + '</div><div style="font-weight:700">' + t +
          '</div><div style="font-size:12px;line-height:1.35">' + (extra || "&nbsp;") + "</div></div>"
        : '<div style="font-size:12.5px;line-height:1.35;padding:2px 0;border-top:1px solid rgba(0,0,0,.06)"><b>' +
          fcDay(x.date, lng) + "</b> " + fcIcon(x.type) + " " + t + (extra ? "<br>" + extra : "") + "</div>";
    });
    return wide
      ? '<div class="fc5" style="display:grid;grid-template-columns:repeat(' + cells.length + ',1fr);gap:6px;margin:6px 0">' + cells.join("") + "</div>"
      : '<div class="fc5" style="margin:4px 0 2px">' + cells.join("") + "</div>";
  }

  function render(d, T, lang) {
    var c = d.counts || { OPEN: 0, PARTIAL: 0, CLOSED: 0 };
    el("summary").innerHTML =
      '<span><span class="dot OPEN"></span><b>' + c.OPEN + "</b> " + T.open + "</span>" +
      '<span><span class="dot PARTIAL"></span><b>' + c.PARTIAL + "</b> " + T.restricted + "</span>" +
      '<span><span class="dot CLOSED"></span><b>' + c.CLOSED + "</b> " + T.closed + "</span>";

    // IPMA warnings for Madeira (yellow and up): one bar across the bottom of the card (owner, 2026-11-08), one item per
    // warning type: highest level, strongest gust, earliest start to latest end. Porto Santo is left out by storm.py.
    var WCOL = { yellow: "background:#F6D743;color:#3a2f00", orange: "background:#F08A24;color:#fff", red: "background:#C62828;color:#fff" };
    var RANKW = { yellow: 1, orange: 2, red: 3 };
    var todayISO = new Date().toLocaleDateString("sv-SE", { timeZone: "Atlantic/Madeira" });
    function hm(iso) {   // "2026-11-08T21:00" -> "21:00", or "Monday 06:00": day names, never a date on the page
      return (iso.slice(0, 10) !== todayISO ? fcDay(iso.slice(0, 10), lang) + " " : "") + iso.slice(11, 16);
    }
    function warnBar() {
      var ws = d.ipma_warnings || [];
      if (!ws.length) return "";
      var top = "yellow", by = {}, order = [];
      ws.forEach(function (w) {
        if (RANKW[w.level] > RANKW[top]) top = w.level;
        var g = by[w.type];
        if (!g) { g = by[w.type] = { type: w.type, start: w.start, end: w.end, now: w.now, gust: w.gust, rank: RANKW[w.level] }; order.push(g); return; }
        if (w.start < g.start) g.start = w.start;
        if (w.end > g.end) g.end = w.end;
        g.now = g.now || w.now;
        if ((w.gust || 0) > (g.gust || 0)) g.gust = w.gust;
        g.rank = Math.max(g.rank, RANKW[w.level]);
      });
      order.sort(function (a, b) { return b.rank - a.rank || (a.start < b.start ? -1 : 1); });
      var parts = order.map(function (g) {
        var txt = T.wtype[g.type] || T.wtype.other;
        if (g.gust) txt += " (" + T.wgust + " " + g.gust + " km/h)";
        return txt + (g.now ? " " + T.wuntil + " " + hm(g.end) : " " + hm(g.start) + "–" + hm(g.end));
      });
      return '<div class="wwarn" style="grid-column:1/-1;' + WCOL[top] + ';border-radius:8px;padding:8px 12px;font-size:14px;font-weight:600;line-height:1.4">⚠ ' +
        T.wlevel[top] + " (" + T.wsrc + "): " + esc(parts.join(" · ")) + "</div>";
    }
    el("weatherStrip").innerHTML = (d.regions || []).map(function (r) {
      var t = (r.temp != null) ? num(r.temp, T) + "°C" : "—";
      var bits = [];
      if (r.wind != null) bits.push(T.wind + " " + r.wind + " km/h");
      if (r.rain != null && r.rain > 0) bits.push('<span class="alert">' + T.rain + " " + num(r.rain, T) + " mm</span>");
      if (r.in_cloud) bits.push('<span class="alert">' + T.fog + "</span>");
      // forecast first (owner, 2026-11-08), then the reading measured now
      var fc = fcRows((d.forecast || {})[r.key], lang, false);
      return '<div class="wx"><b>' + T.region[r.key] + " · " + esc(r.place) + "</b>" + fc +
        '<span class="wext" style="margin-top:4px"><b>' + (FCW[lang] || FCW.en).now + ":</b> " + t +
        (bits.length ? " · " + bits.join(" · ") : "") + "</span></div>";
    }).join("") + warnBar() + '<div class="note">' + T.mmnote + "</div>";
    if (d.forecast && Object.keys(d.forecast).length)   // the heading leads the card
      el("weatherStrip").insertAdjacentHTML("afterbegin", '<div class="note" style="grid-column:1/-1;font-weight:700;color:var(--ink)">' + (FCW[lang] || FCW.en).head + "</div>");

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
