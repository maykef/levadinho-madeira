/* Levadinho storm banner (2026-10-10). Reads "alert" from /status.json (written by scripts/storm.py via the
   updater) and shows one line at the top of every page:
   - IFCN blanket closure in force   -> red:   all classified trails closed (IFCN notice)
   - IFCN closure announced          -> red:   all classified trails close (tomorrow)
   - orange/red IPMA warning only    -> amber: warning + "IFCN closed all trails in past warnings, check"
   - many trails closed, no blanket  -> red:   "N of M classified trails are closed on IFCN's list (incl. PR1)"
                                               (storm.py partial(), owner 2026-11-12), with a link to the closures page
   Wording mirrors storm.py (keep them in sync). No dates shown, only "tomorrow". Injected by gen_owner.py. */
(function () {
  "use strict";
  var T = {
    en: { closed: "All classified trails are closed.", note: "IFCN has closed all classified trails (communiqué on IFCN's homepage).",
          reopen: " IFCN says they reopen tomorrow.", announced: "IFCN has announced that all classified trails will close{w}.",
          tomorrow: " tomorrow", ipma: "IPMA {lvl} warning for Madeira{w}. During past warnings IFCN closed all classified trails: check before you go.",
          now: " in force", soon: " in the next 24 hours", lvl: { yellow: "yellow", orange: "orange", red: "red" }, src: "Sources", close: "Close" },
    pt: { closed: "Todos os percursos classificados estão encerrados.", note: "O IFCN encerrou todos os percursos pedestres classificados (comunicado na página inicial do IFCN).",
          reopen: " Reabrem amanhã, segundo o IFCN.", announced: "O IFCN anunciou o encerramento de todos os percursos pedestres classificados{w}.",
          tomorrow: " amanhã", ipma: "Aviso {lvl} do IPMA para a Madeira{w}. Em avisos anteriores o IFCN encerrou todos os percursos classificados: confirme antes de ir.",
          now: " em vigor", soon: " nas próximas 24 horas", lvl: { yellow: "amarelo", orange: "laranja", red: "vermelho" }, src: "Fontes", close: "Fechar" },
    fr: { closed: "Tous les sentiers classés sont fermés.", note: "L'IFCN a fermé tous les sentiers classés (communiqué sur la page d'accueil de l'IFCN).",
          reopen: " Selon l'IFCN, ils rouvrent demain.", announced: "L'IFCN a annoncé la fermeture de tous les sentiers classés{w}.",
          tomorrow: " demain", ipma: "Avis {lvl} de l'IPMA pour Madère{w}. Lors d'avis précédents, l'IFCN a fermé tous les sentiers classés : vérifiez avant de partir.",
          now: " en vigueur", soon: " dans les prochaines 24 heures", lvl: { yellow: "jaune", orange: "orange", red: "rouge" }, src: "Sources", close: "Fermer" },
    de: { closed: "Alle klassifizierten Wege sind gesperrt.", note: "Das IFCN hat alle klassifizierten Wege gesperrt (Mitteilung auf der Startseite des IFCN).",
          reopen: " Laut IFCN öffnen sie morgen wieder.", announced: "Das IFCN hat angekündigt, alle klassifizierten Wege{w} zu sperren.",
          tomorrow: " morgen", ipma: "IPMA-Warnstufe {lvl} für Madeira{w}. Bei früheren Warnungen hat das IFCN alle klassifizierten Wege gesperrt: Prüfen Sie vor dem Losgehen.",
          now: " in Kraft", soon: " in den nächsten 24 Stunden", lvl: { yellow: "Gelb", orange: "Orange", red: "Rot" }, src: "Quellen", close: "Schließen" },
    pl: { closed: "Wszystkie sklasyfikowane szlaki są zamknięte.", note: "IFCN zamknął wszystkie sklasyfikowane szlaki (komunikat na stronie głównej IFCN).",
          reopen: " Według IFCN zostaną otwarte jutro.", announced: "IFCN zapowiedział zamknięcie wszystkich sklasyfikowanych szlaków{w}.",
          tomorrow: " jutro", ipma: "Ostrzeżenie IPMA ({lvl}) dla Madery{w}. Podczas wcześniejszych ostrzeżeń IFCN zamykał wszystkie sklasyfikowane szlaki: sprawdź przed wyjściem.",
          now: " obowiązuje", soon: " w ciągu najbliższych 24 godzin", lvl: { yellow: "żółte", orange: "pomarańczowe", red: "czerwone" }, src: "Źródła", close: "Zamknij" }
  };
  // "Bad weather coming" (owner, 2026-11-08): status.json "outlook" = IPMA's forecast / later warnings for the next days
  // (scripts/ipma_forecast.py). Amber, above everything, before anything closes. Day names, never dates.
  var O = {
    en: { head: "Bad weather coming", txt: "IPMA forecast for Madeira: {what} {days}. During past warnings IFCN closed all classified trails: book flexibly and check here first.",
          today: "today", on: "on", and: "and", heavy_rain: "heavy rain", thunder: "thunderstorms", strong_wind: "strong wind", hail: "hail", snow: "snow", warning: "an IPMA {lvl} warning" },
    pt: { head: "Mau tempo a caminho", txt: "Previsão do IPMA para a Madeira: {what} {days}. Em avisos anteriores o IFCN encerrou todos os percursos classificados: reserve com flexibilidade e confirme aqui primeiro.",
          today: "hoje", on: "na/no", and: "e", heavy_rain: "chuva forte", thunder: "trovoada", strong_wind: "vento forte", hail: "granizo", snow: "neve", warning: "aviso {lvl} do IPMA" },
    fr: { head: "Mauvais temps en approche", txt: "Prévision de l'IPMA pour Madère : {what} {days}. Lors d'avis précédents, l'IFCN a fermé tous les sentiers classés : réservez avec souplesse et vérifiez ici d'abord.",
          today: "aujourd'hui", on: "", and: "et", heavy_rain: "fortes pluies", thunder: "orages", strong_wind: "vent fort", hail: "grêle", snow: "neige", warning: "vigilance {lvl} de l'IPMA" },
    de: { head: "Schlechtes Wetter im Anmarsch", txt: "IPMA-Vorhersage für Madeira: {what} {days}. Bei früheren Warnungen hat das IFCN alle klassifizierten Wege gesperrt: Buchen Sie flexibel und prüfen Sie hier zuerst.",
          today: "heute", on: "am", and: "und", heavy_rain: "Starkregen", thunder: "Gewitter", strong_wind: "starker Wind", hail: "Hagel", snow: "Schnee", warning: "IPMA-Warnstufe {lvl}" },
    pl: { head: "Nadchodzi zła pogoda", txt: "Prognoza IPMA dla Madery: {what} {days}. Podczas wcześniejszych ostrzeżeń IFCN zamykał wszystkie sklasyfikowane szlaki: rezerwuj elastycznie i sprawdzaj najpierw tutaj.",
          today: "dziś", on: "w", and: "i", heavy_rain: "ulewny deszcz", thunder: "burze", strong_wind: "silny wiatr", hail: "grad", snow: "śnieg", warning: "ostrzeżenie IPMA ({lvl})" }
  };
  var PL_ON = { 1: "w poniedziałek", 2: "we wtorek", 3: "w środę", 4: "w czwartek", 5: "w piątek", 6: "w sobotę", 0: "w niedzielę" };
  var PT_ON = { 1: "na", 2: "na", 3: "na", 4: "na", 5: "na", 6: "no", 0: "no" };   // na segunda … no sábado / domingo
  var lang = (document.documentElement.lang || "en").slice(0, 2);
  var L = T[lang] || T.en;

  function madeiraDate(offsetDays) {
    var d = new Date(Date.now() + (offsetDays || 0) * 864e5);
    return new Intl.DateTimeFormat("en-CA", { timeZone: "Atlantic/Madeira" }).format(d);  // YYYY-MM-DD
  }
  function link(href, text) {
    return '<a href="' + href + '" target="_blank" rel="noopener" style="color:inherit;text-decoration:underline">' + text + "</a>";
  }

  function dayName(iso) {
    var n = new Intl.DateTimeFormat(lang, { weekday: "long", timeZone: "UTC" }).format(new Date(iso + "T12:00:00Z"));
    return lang === "de" || lang === "en" ? n.charAt(0).toUpperCase() + n.slice(1) : n;
  }
  function outlookText(o, fromDay) {   // the outlook sentence for the days from `fromDay` on, or ""
    var P = O[lang] || O.en, L2 = T[lang] || T.en;
    var days = ((o && o.days) || []).filter(function (x) { return x.date >= fromDay; }).slice(0, 4);
    if (!days.length) return "";
    var what = [];
    days.forEach(function (x) {
      x.reasons.forEach(function (r) {
        var w = r.indexOf("warning_") === 0 ? P.warning.replace("{lvl}", L2.lvl[r.slice(8)] || r.slice(8)) : P[r];
        if (w && what.indexOf(w) < 0) what.push(w);
      });
    });
    var names = days.map(function (x) {
      if (x.date === madeiraDate(0)) return P.today;
      var wd = new Date(x.date + "T12:00:00Z").getUTCDay();
      if (lang === "pl") return PL_ON[wd];
      var on = lang === "pt" ? PT_ON[wd] : P.on;
      return (on ? on + " " : "") + dayName(x.date);
    });
    var dayStr = names.length > 1 ? names.slice(0, -1).join(", ") + " " + P.and + " " + names[names.length - 1] : names[0];
    return P.txt.replace("{what}", what.join(", ")).replace("{days}", dayStr);
  }

  function banner(a, o) {
    a = a || {};
    var red = !!a.blanket || !!a.partial, html, P = O[lang] || O.en;
    var pt = a.partial && a.partial.text && (a.partial.text[lang] || a.partial.text.en);
    if (a.blanket === "closed") {
      html = "<b>" + L.closed + "</b> " + L.note + (a.blanket_reopen === madeiraDate(1) ? L.reopen : "");
    } else if (a.blanket === "announced") {
      html = "<b>" + L.announced.replace("{w}", a.blanket_from === madeiraDate(1) ? L.tomorrow : "") + "</b>";
    } else if (pt) {   // many trails closed without an island-wide closure (storm.py partial)
      var pre = lang === "en" || !MENU[lang] ? "" : "/" + lang;
      html = "<b>" + pt.head + "</b> " + pt.body + ' <a href="' + pre + '/trail-closures/" style="color:inherit;text-decoration:underline">' + (MENU[lang] || MENU.en) + "</a>";
      if (a.ipma_level) html += "<br>" + L.ipma.replace("{lvl}", L.lvl[a.ipma_level] || a.ipma_level).replace("{w}", a.ipma_now ? L.now : L.soon);
    } else if (a.ipma_level) {
      html = L.ipma.replace("{lvl}", L.lvl[a.ipma_level] || a.ipma_level).replace("{w}", a.ipma_now ? L.now : L.soon);
    } else if (a.ahead_text) {   // no closure, IPMA warnings ahead: the notice alone (owner, 2026-11-09)
      var ah0 = a.ahead_text[lang] || a.ahead_text.en;
      html = "<b>" + ah0.head + "</b> " + ah0.body;
    } else if (outlookText(o, madeiraDate(0))) {
      html = "<b>" + P.head + ".</b> " + outlookText(o, madeiraDate(0));
    } else {
      return null;
    }
    var ah = a.ahead_text && (a.ahead_text[lang] || a.ahead_text.en);
    if (ah && (a.blanket || a.ipma_level || pt))   // IPMA warnings ahead as advice + IPMA's forecast for the day after (storm.py ahead_text, owner 2026-11-09)
      html += "<br><b>" + ah.head + "</b> " + ah.body;
    else if ((a.blanket || a.ipma_level || pt) && outlookText(o, madeiraDate(1)))   // an alert today, more bad days to come
      html += "<br><b>" + P.head + ":</b> " + outlookText(o, madeiraDate(1));
    var src = [];
    if (a.ifcn_source || (a.partial && a.partial.source)) src.push(link(a.ifcn_source || a.partial.source, "IFCN"));
    if ((a.ipma_level || a.ahead_text || (o && o.days && o.days.length)) && (a.ipma_source || (o && o.source))) src.push(link(a.ipma_source || o.source, "IPMA"));
    var el = document.createElement("div");
    el.id = "stormAlert";
    el.setAttribute("role", "alert");
    // Fixed to the bottom of the screen (14 Nov): inserted at the top after load it pushed the whole page down
    // (Lighthouse CLS 0.14 of the homepage's 0.19). A fixed bar moves nothing; the body gets matching bottom padding
    // (below the fold, so no shift either) and the × hides it for the rest of the visit, until the wording changes.
    el.style.cssText = "position:fixed;left:0;right:0;bottom:0;z-index:9999;max-height:40vh;overflow:auto;margin:0;" +
      "padding:12px 44px 12px 16px;font-size:15px;line-height:1.45;box-shadow:0 -2px 10px rgba(0,0,0,.18);border-top:3px solid " +
      (red ? "#8f1d14;background:#fbe3df;color:#5a120c" : "#a8660a;background:#fff1d6;color:#4d3205");
    el.innerHTML = html + (src.length ? ' <span style="font-size:13px;opacity:.85">(' + L.src + ": " + src.join(" · ") + ")</span>" : "");
    var x = document.createElement("button");
    x.type = "button"; x.textContent = "×"; x.setAttribute("aria-label", L.close || "Close");
    x.style.cssText = "position:absolute;top:6px;right:8px;border:0;background:none;color:inherit;font-size:24px;line-height:1;cursor:pointer;padding:4px 8px";
    x.onclick = function () {
      el.parentNode.removeChild(el); document.body.style.paddingBottom = "";
      try { sessionStorage.setItem("stormAlertHidden", el.getAttribute("data-key")); } catch (e) {}
    };
    el.appendChild(x);
    el.setAttribute("data-key", String(html.length) + ":" + html.slice(0, 80));
    return el;
  }

  // "Trail closures" in the menu, right after "All trails", only during an IFCN island-wide closure (owner, 2026-11-08);
  // gone again as soon as status.json no longer says blanket = "closed". Added here, not in the generated menu, so the
  // ~300 pages don't change twice per storm.
  var MENU = { en: "Trail closures", pt: "Percursos encerrados", fr: "Sentiers fermés", de: "Gesperrte Wege", pl: "Zamknięte szlaki" };
  function closuresMenu(a) {
    var nav = document.querySelector("nav.sitenav");
    if (!nav || !a || (a.blanket !== "closed" && !a.partial) || nav.querySelector("a[data-closures]")) return;
    var pre = lang === "en" || !MENU[lang] ? "" : "/" + lang, href = pre + "/trail-closures/";
    var x = document.createElement("a");
    x.href = href; x.textContent = MENU[lang] || MENU.en; x.setAttribute("data-closures", "1");
    x.style.color = "#a8231a";
    if (location.pathname === href || location.pathname === href + "index.html") x.setAttribute("aria-current", "page");
    var first = nav.querySelector("a");
    if (first && first.nextSibling) nav.insertBefore(x, first.nextSibling); else nav.appendChild(x);
  }

  fetch("/status.json", { cache: "no-cache" })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (d) closuresMenu(d.alert);
      if (!d || (!d.alert && !d.outlook) || document.getElementById("stormAlert")) return;
      var el = banner(d.alert, d.outlook);
      if (!el) return;
      try { if (sessionStorage.getItem("stormAlertHidden") === el.getAttribute("data-key")) return; } catch (e) {}
      document.body.appendChild(el);
      document.body.style.paddingBottom = el.offsetHeight + "px";
    })
    .catch(function () { /* no banner without data */ });
})();
