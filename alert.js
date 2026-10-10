/* Levadinho storm banner (2026-10-10). Reads "alert" from /status.json (written by scripts/storm.py via the
   updater) and shows one line at the top of every page:
   - IFCN blanket closure in force   -> red:   all classified trails closed (IFCN notice)
   - IFCN closure announced          -> red:   all classified trails close (tomorrow)
   - orange/red IPMA warning only    -> amber: warning + "IFCN closed all trails in past warnings, check"
   Wording mirrors storm.py (keep them in sync). No dates shown, only "tomorrow". Injected by gen_owner.py. */
(function () {
  "use strict";
  var T = {
    en: { closed: "All classified trails are closed.", note: "IFCN has closed all classified trails because of IPMA weather warnings.",
          reopen: " IFCN says they reopen tomorrow.", announced: "IFCN has announced that all classified trails will close{w} because of IPMA weather warnings.",
          tomorrow: " tomorrow", ipma: "IPMA {lvl} warning for Madeira{w}. During past warnings IFCN closed all classified trails: check before you go.",
          now: " in force", soon: " in the next 24 hours", lvl: { orange: "orange", red: "red" }, src: "Sources" },
    pt: { closed: "Todos os percursos classificados estão encerrados.", note: "O IFCN encerrou todos os percursos pedestres classificados devido aos avisos meteorológicos do IPMA.",
          reopen: " Reabrem amanhã, segundo o IFCN.", announced: "O IFCN anunciou o encerramento de todos os percursos pedestres classificados{w} devido aos avisos meteorológicos do IPMA.",
          tomorrow: " amanhã", ipma: "Aviso {lvl} do IPMA para a Madeira{w}. Em avisos anteriores o IFCN encerrou todos os percursos classificados: confirme antes de ir.",
          now: " em vigor", soon: " nas próximas 24 horas", lvl: { orange: "laranja", red: "vermelho" }, src: "Fontes" },
    fr: { closed: "Tous les sentiers classés sont fermés.", note: "L'IFCN a fermé tous les sentiers classés en raison des avis météorologiques de l'IPMA.",
          reopen: " Selon l'IFCN, ils rouvrent demain.", announced: "L'IFCN a annoncé la fermeture de tous les sentiers classés{w} en raison des avis météorologiques de l'IPMA.",
          tomorrow: " demain", ipma: "Avis {lvl} de l'IPMA pour Madère{w}. Lors d'avis précédents, l'IFCN a fermé tous les sentiers classés : vérifiez avant de partir.",
          now: " en vigueur", soon: " dans les prochaines 24 heures", lvl: { orange: "orange", red: "rouge" }, src: "Sources" },
    de: { closed: "Alle klassifizierten Wege sind gesperrt.", note: "Das IFCN hat wegen der Wetterwarnungen des IPMA alle klassifizierten Wege gesperrt.",
          reopen: " Laut IFCN öffnen sie morgen wieder.", announced: "Das IFCN hat angekündigt, alle klassifizierten Wege{w} wegen der Wetterwarnungen des IPMA zu sperren.",
          tomorrow: " morgen", ipma: "IPMA-Warnstufe {lvl} für Madeira{w}. Bei früheren Warnungen hat das IFCN alle klassifizierten Wege gesperrt: Prüfen Sie vor dem Losgehen.",
          now: " in Kraft", soon: " in den nächsten 24 Stunden", lvl: { orange: "Orange", red: "Rot" }, src: "Quellen" },
    pl: { closed: "Wszystkie sklasyfikowane szlaki są zamknięte.", note: "IFCN zamknął wszystkie sklasyfikowane szlaki z powodu ostrzeżeń pogodowych IPMA.",
          reopen: " Według IFCN zostaną otwarte jutro.", announced: "IFCN zapowiedział zamknięcie wszystkich sklasyfikowanych szlaków{w} z powodu ostrzeżeń pogodowych IPMA.",
          tomorrow: " jutro", ipma: "Ostrzeżenie IPMA ({lvl}) dla Madery{w}. Podczas wcześniejszych ostrzeżeń IFCN zamykał wszystkie sklasyfikowane szlaki: sprawdź przed wyjściem.",
          now: " obowiązuje", soon: " w ciągu najbliższych 24 godzin", lvl: { orange: "pomarańczowe", red: "czerwone" }, src: "Źródła" }
  };
  var lang = (document.documentElement.lang || "en").slice(0, 2);
  var L = T[lang] || T.en;

  function madeiraDate(offsetDays) {
    var d = new Date(Date.now() + (offsetDays || 0) * 864e5);
    return new Intl.DateTimeFormat("en-CA", { timeZone: "Atlantic/Madeira" }).format(d);  // YYYY-MM-DD
  }
  function link(href, text) {
    return '<a href="' + href + '" target="_blank" rel="noopener" style="color:inherit;text-decoration:underline">' + text + "</a>";
  }

  function banner(a) {
    var red = !!a.blanket, html;
    if (a.blanket === "closed") {
      html = "<b>" + L.closed + "</b> " + L.note + (a.blanket_reopen === madeiraDate(1) ? L.reopen : "");
    } else if (a.blanket === "announced") {
      html = "<b>" + L.announced.replace("{w}", a.blanket_from === madeiraDate(1) ? L.tomorrow : "") + "</b>";
    } else if (a.ipma_level) {
      html = L.ipma.replace("{lvl}", L.lvl[a.ipma_level] || a.ipma_level).replace("{w}", a.ipma_now ? L.now : L.soon);
    } else {
      return null;
    }
    var src = [];
    if (a.ifcn_source) src.push(link(a.ifcn_source, "IFCN"));
    if (a.ipma_level && a.ipma_source) src.push(link(a.ipma_source, "IPMA"));
    var el = document.createElement("div");
    el.id = "stormAlert";
    el.setAttribute("role", "alert");
    el.style.cssText = "margin:0;padding:12px 16px;font-size:15px;line-height:1.45;border-bottom:3px solid " +
      (red ? "#8f1d14;background:#fbe3df;color:#5a120c" : "#a8660a;background:#fff1d6;color:#4d3205");
    el.innerHTML = html + (src.length ? ' <span style="font-size:13px;opacity:.85">(' + L.src + ": " + src.join(" · ") + ")</span>" : "");
    return el;
  }

  fetch("/status.json", { cache: "no-cache" })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (!d || !d.alert || document.getElementById("stormAlert")) return;
      var el = banner(d.alert);
      if (el) document.body.insertBefore(el, document.body.firstChild);
    })
    .catch(function () { /* no banner without data */ });
})();
