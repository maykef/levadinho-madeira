/* Levadinho — renders the live status card from /status.json.
   - PR1 pages: #statusCard with no data-trail -> the detailed top-level card.
   - Spoke pages: #statusCard data-trail="PR6" -> that trail's card from trails[].
   Language comes from <html lang>; all wording lives in LANGS. */
(function () {
  "use strict";

  var LANGS = {
    en: {
      badge: { OPEN: "OPEN", PARTIAL: "PARTIAL", CLOSED: "CLOSED" },
      summit: "Summit now:", sky: { CLEAR: "CLEAR", CLOUDY: "CLOUDY" },
      officialNote: "Official note:",
      defaultNote: {
        OPEN: "One-way only: Pico do Areeiro → Pico Ruivo. Book on SIMplifica before you go.",
        PARTIAL: "Access is restricted — read the official note above before planning.",
        CLOSED: "The trail is officially closed. See below for rescheduling your SIMplifica booking and open alternatives."
      },
      spokeNote: {
        OPEN: "Open today — book your slot on SIMplifica before you go.",
        PARTIAL: "Access is restricted — read the official note above before planning.",
        CLOSED: "Officially closed — see rescheduling and open alternatives below."
      },
      weather: function (w) {
        if (!w || !w.ok) return "Check the mountain forecast before you go — summit conditions differ sharply from Funchal.";
        var cloud = w.in_cloud ? ", likely in cloud/fog (humidity " + Math.round(w.humidity) + "%)" : "";
        var wind = w.wind_strong ? ", strong wind (" + Math.round(w.wind_kmh) + " km/h)" : "";
        return "Summit weather now: " + Math.round(w.temp_c) + "°C measured at the Pico do Areeiro station (~1,800 m)" + cloud + wind + " — expect it far colder and cloudier than Funchal.";
      },
      nearby: function (r) { return "Weather near the trail (IPMA " + esc(r.place) + " station): " + r.temp + "°C" + (r.wind != null ? ", wind " + r.wind + " km/h" : "") + (r.in_cloud ? ", likely in cloud" : "") + (r.rain ? ", rain " + r.rain + " mm in the last hour" : "") + " — expect the mountains cooler and cloudier than the coast."; },
      advisory: "The webcam shows you a snippet of the summit right now — don't assume conditions will stay that way. Pack a good anorak and fleece, carry enough water, and wear adequate footwear.",
      ifcnUpdated: "Official IFCN list · updated:", lastChecked: "Checked by Levadinho:", madeiraTime: "(Madeira time)", source: "Source:"
    },
    pt: {
      badge: { OPEN: "ABERTO", PARTIAL: "PARCIAL", CLOSED: "FECHADO" },
      summit: "Cume agora:", sky: { CLEAR: "LIMPO", CLOUDY: "NUBLADO" },
      officialNote: "Nota oficial:",
      defaultNote: {
        OPEN: "Apenas num sentido: Pico do Areeiro → Pico Ruivo. Reserve no SIMplifica antes de ir.",
        PARTIAL: "Acesso condicionado — leia a nota oficial acima antes de planear.",
        CLOSED: "O percurso está oficialmente fechado. Veja abaixo como reagendar a sua reserva no SIMplifica e as alternativas abertas."
      },
      spokeNote: {
        OPEN: "Aberto hoje — reserve a sua vaga no SIMplifica antes de ir.",
        PARTIAL: "Acesso condicionado — leia a nota oficial acima antes de planear.",
        CLOSED: "Oficialmente fechado — veja abaixo como reagendar e as alternativas abertas."
      },
      weather: function (w) {
        if (!w || !w.ok) return "Consulte a previsão para a montanha antes de ir — as condições no cume são muito diferentes das do Funchal.";
        var cloud = w.in_cloud ? ", provavelmente dentro das nuvens/nevoeiro (humidade " + Math.round(w.humidity) + " %)" : "";
        var wind = w.wind_strong ? ", vento forte (" + Math.round(w.wind_kmh) + " km/h)" : "";
        return "Tempo no cume agora: " + Math.round(w.temp_c) + " °C medidos na estação do Pico do Areeiro (~1800 m)" + cloud + wind + " — conte com bastante mais frio e nebulosidade do que no Funchal.";
      },
      nearby: function (r) { return "Tempo perto do percurso (estação IPMA " + esc(r.place) + "): " + r.temp + " °C" + (r.wind != null ? ", vento " + r.wind + " km/h" : "") + (r.in_cloud ? ", provavelmente dentro das nuvens" : "") + (r.rain ? ", chuva " + r.rain + " mm na última hora" : "") + " — conte com a montanha mais fresca e nublada do que a costa."; },
      advisory: "A webcam mostra apenas um instante do cume — não assuma que as condições se vão manter. Leve um bom corta-vento impermeável e um polar, água suficiente e calçado adequado.",
      ifcnUpdated: "Lista oficial do IFCN · atualizado:", lastChecked: "Verificado pelo Levadinho:", madeiraTime: "(hora da Madeira)", source: "Fonte:"
    },
    fr: {
      badge: { OPEN: "OUVERT", PARTIAL: "PARTIEL", CLOSED: "FERMÉ" },
      summit: "Sommet :", sky: { CLEAR: "DÉGAGÉ", CLOUDY: "NUAGEUX" },
      officialNote: "Note officielle :",
      defaultNote: {
        OPEN: "Sens unique : Pico do Areeiro → Pico Ruivo. Réservez sur SIMplifica avant de partir.",
        PARTIAL: "Accès restreint — lisez la note officielle ci-dessus avant de planifier.",
        CLOSED: "Le sentier est officiellement fermé. Voir ci-dessous pour reprogrammer votre réservation SIMplifica et les alternatives ouvertes."
      },
      spokeNote: {
        OPEN: "Ouvert aujourd'hui — réservez votre créneau sur SIMplifica avant de partir.",
        PARTIAL: "Accès restreint — lisez la note officielle ci-dessus avant de planifier.",
        CLOSED: "Officiellement fermé — voir ci-dessous la reprogrammation et les alternatives ouvertes."
      },
      weather: function (w) {
        if (!w || !w.ok) return "Consultez la météo de montagne avant de partir — les conditions au sommet diffèrent fortement de Funchal.";
        var cloud = w.in_cloud ? ", probablement dans les nuages/le brouillard (humidité " + Math.round(w.humidity) + " %)" : "";
        var wind = w.wind_strong ? ", vent fort (" + Math.round(w.wind_kmh) + " km/h)" : "";
        return "Météo au sommet : " + Math.round(w.temp_c) + " °C mesurés à la station du Pico do Areeiro (~1 800 m)" + cloud + wind + " — attendez-vous à bien plus froid et nuageux qu'à Funchal.";
      },
      nearby: function (r) { return "Météo près du sentier (station IPMA " + esc(r.place) + ") : " + r.temp + " °C" + (r.wind != null ? ", vent " + r.wind + " km/h" : "") + (r.in_cloud ? ", probablement dans les nuages" : "") + (r.rain ? ", pluie " + r.rain + " mm sur la dernière heure" : "") + " — attendez-vous à des montagnes plus fraîches et nuageuses que la côte."; },
      advisory: "La webcam ne montre qu'un aperçu du sommet à l'instant — ne supposez pas que les conditions resteront les mêmes. Emportez un bon anorak et une polaire, assez d'eau, et portez des chaussures adaptées.",
      ifcnUpdated: "Liste officielle de l'IFCN · mise à jour :", lastChecked: "Vérifié par Levadinho :", madeiraTime: "(heure de Madère)", source: "Source :"
    },
    de: {
      badge: { OPEN: "OFFEN", PARTIAL: "TEILWEISE", CLOSED: "GESPERRT" },
      summit: "Gipfel jetzt:", sky: { CLEAR: "KLAR", CLOUDY: "BEWÖLKT" },
      officialNote: "Offizieller Hinweis:",
      defaultNote: {
        OPEN: "Nur Einbahnrichtung: Pico do Areeiro → Pico Ruivo. Vor dem Start auf SIMplifica buchen.",
        PARTIAL: "Zugang eingeschränkt — lesen Sie den offiziellen Hinweis oben, bevor Sie planen.",
        CLOSED: "Der Weg ist offiziell gesperrt. Siehe unten zum Umbuchen Ihrer SIMplifica-Reservierung und zu offenen Alternativen."
      },
      spokeNote: {
        OPEN: "Heute offen — buchen Sie Ihren Platz vor dem Start auf SIMplifica.",
        PARTIAL: "Zugang eingeschränkt — lesen Sie den offiziellen Hinweis oben, bevor Sie planen.",
        CLOSED: "Offiziell gesperrt — siehe unten Umbuchung und offene Alternativen."
      },
      weather: function (w) {
        if (!w || !w.ok) return "Prüfen Sie vor dem Aufbruch den Bergwetterbericht — die Bedingungen am Gipfel unterscheiden sich stark von Funchal.";
        var cloud = w.in_cloud ? ", wahrscheinlich in Wolken/Nebel (Luftfeuchte " + Math.round(w.humidity) + " %)" : "";
        var wind = w.wind_strong ? ", starker Wind (" + Math.round(w.wind_kmh) + " km/h)" : "";
        return "Gipfelwetter jetzt: " + Math.round(w.temp_c) + " °C gemessen an der Station Pico do Areeiro (~1.800 m)" + cloud + wind + " — rechnen Sie mit deutlich kälterem und wolkigerem Wetter als in Funchal.";
      },
      nearby: function (r) { return "Wetter am Weg (IPMA-Station " + esc(r.place) + "): " + r.temp + " °C" + (r.wind != null ? ", Wind " + r.wind + " km/h" : "") + (r.in_cloud ? ", wahrscheinlich in Wolken" : "") + (r.rain ? ", Regen " + r.rain + " mm in der letzten Stunde" : "") + " — in den Bergen kühler und wolkiger als an der Küste."; },
      advisory: "Die Webcam zeigt nur einen Moment des Gipfels — gehen Sie nicht davon aus, dass die Bedingungen so bleiben. Nehmen Sie einen guten Anorak und Fleece mit, genügend Wasser und tragen Sie geeignetes Schuhwerk.",
      ifcnUpdated: "Offizielle IFCN-Liste · aktualisiert:", lastChecked: "Von Levadinho geprüft:", madeiraTime: "(Madeira-Zeit)", source: "Quelle:"
    },
    pl: {
      badge: { OPEN: "OTWARTY", PARTIAL: "CZĘŚCIOWO", CLOSED: "ZAMKNIĘTY" },
      summit: "Szczyt teraz:", sky: { CLEAR: "BEZ CHMUR", CLOUDY: "POCHMURNO" },
      officialNote: "Uwaga oficjalna:",
      defaultNote: {
        OPEN: "Tylko w jedną stronę: Pico do Areeiro → Pico Ruivo. Zarezerwuj w SIMplifica przed wyjściem.",
        PARTIAL: "Dostęp ograniczony — przed planowaniem przeczytaj powyższą uwagę oficjalną.",
        CLOSED: "Szlak jest oficjalnie zamknięty. Poniżej znajdziesz informacje o zmianie rezerwacji SIMplifica i otwartych alternatywach."
      },
      spokeNote: {
        OPEN: "Otwarty dzisiaj — zarezerwuj miejsce w SIMplifica przed wyjściem.",
        PARTIAL: "Dostęp ograniczony — przed planowaniem przeczytaj powyższą uwagę oficjalną.",
        CLOSED: "Oficjalnie zamknięty — poniżej zmiana rezerwacji i otwarte alternatywy."
      },
      weather: function (w) {
        if (!w || !w.ok) return "Przed wyjściem sprawdź górską prognozę — warunki na szczycie znacznie różnią się od Funchal.";
        var cloud = w.in_cloud ? ", prawdopodobnie w chmurze/mgle (wilgotność " + Math.round(w.humidity) + " %)" : "";
        var wind = w.wind_strong ? ", silny wiatr (" + Math.round(w.wind_kmh) + " km/h)" : "";
        return "Pogoda na szczycie: " + Math.round(w.temp_c) + " °C zmierzone na stacji Pico do Areeiro (~1800 m)" + cloud + wind + " — spodziewaj się znacznie zimniej i bardziej pochmurno niż w Funchal.";
      },
      nearby: function (r) { return "Pogoda przy szlaku (stacja IPMA " + esc(r.place) + "): " + r.temp + " °C" + (r.wind != null ? ", wiatr " + r.wind + " km/h" : "") + (r.in_cloud ? ", prawdopodobnie w chmurach" : "") + (r.rain ? ", deszcz " + r.rain + " mm w ostatniej godzinie" : "") + " — w górach chłodniej i bardziej pochmurno niż na wybrzeżu."; },
      advisory: "Kamera pokazuje tylko chwilowy widok szczytu — nie zakładaj, że warunki się nie zmienią. Zabierz dobrą kurtkę i polar, wystarczająco wody i włóż odpowiednie obuwie.",
      ifcnUpdated: "Oficjalna lista IFCN · aktualizacja:", lastChecked: "Sprawdzone przez Levadinho:", madeiraTime: "(czas Madery)", source: "Źródło:"
    }
  };

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  var lang, L;
  function noteText(note, fallback) {
    if (!note) return fallback;
    if (typeof note === "string") return note;
    if (note[lang]) return note[lang];
    if (note.en) return note.en;
    // Portuguese is the original since 2026-09-30; take any language rather than nothing.
    for (var k in note) { if (note[k]) return note[k]; }
    return fallback;
  }
  function stamp(d) {
    // No dates (owner, 2026-10-05): IFCN's "updated" date is often weeks old and made the site look stale.
    var src = d.source || {};
    return '<div class="stamp"><span>' + L.source + ' <a href="' + esc(src.url || "https://ifcn.madeira.gov.pt/") +
      '" rel="noopener">IFCN</a> · IPMA</span></div>';
  }

  // Summit sky badge on PR1 cards (owner, 2026-10-08): CLOUDY (red) when the IPMA Pico do Areeiro station is at or
  // above 90 % humidity (the updater's in_cloud rule), else CLEAR (green). Refreshed live from IPMA (CORS-open).
  var SUMMIT = 1210974, SUMMIT_WIND = 1210973, CLOUD_PCT = 90, WIND_STRONG = 40;
  function summitHead(w) {
    if (!w || !w.ok || w.humidity == null) return "";
    var s = w.in_cloud ? "CLOUDY" : "CLEAR";
    return '<div class="summit-head">' + L.summit + ' <span class="summit-badge ' + s + '">' + L.sky[s] + "</span></div>";
  }
  function liveSummit() {
    return fetch("https://api.ipma.pt/open-data/observation/meteorology/stations/observations.json")
      .then(function (r) { return r.json(); })
      .then(function (obs) {
        function f(rec, k) { var v = rec && rec[k]; return (v == null || v <= -98.5) ? null : +v; }
        var times = Object.keys(obs).sort().reverse(), rec = null, wrec = null;
        for (var i = 0; i < times.length && !rec; i++) {
          var r = obs[times[i]][SUMMIT];
          if (f(r, "temperatura") != null) { rec = r; wrec = obs[times[i]][SUMMIT_WIND]; }
        }
        var t = f(rec, "temperatura"), h = f(rec, "humidade");
        if (t == null || t < -10 || t > 30) return null;
        var wind = f(rec, "intensidadeVentoKM"); if (wind == null) wind = f(wrec, "intensidadeVentoKM");
        return { ok: true, temp_c: t, humidity: h, in_cloud: h != null && h >= CLOUD_PCT,
                 wind_kmh: wind, wind_strong: wind != null && wind >= WIND_STRONG };
      });
  }

  function render(d, L) {
    var st = (d.status === "OPEN" || d.status === "CLOSED") ? d.status : "PARTIAL";
    var body = "";
    var note = d.note ? noteText(d.note, "") : "";
    if (note) body += "<p><b>" + L.officialNote + "</b> " + esc(note) + "</p>";
    body += "<p>" + L.defaultNote[st] + "</p>";
    if (d.manual_note) body += "<p>" + esc(d.manual_note) + "</p>";
    body += "<p>" + L.weather(d.weather) + "</p>";
    body += '<p class="advisory">' + L.advisory + "</p>";
    return '<div class="status-head"><span class="status-dot ' + st + '"></span>' +
      '<span class="status-badge ' + st + '">' + L.badge[st] + "</span></div>" + summitHead(d.weather) +
      '<div class="status-body">' + body + "</div>" + stamp(d);
  }

  function renderSpoke(t, d) {
    if (!t) return '<div class="status-body"><p>' + L.spokeNote.PARTIAL + "</p></div>";
    var st = (t.status === "OPEN" || t.status === "CLOSED") ? t.status : "PARTIAL";
    var note = t.note ? noteText(t.note, L.spokeNote[st]) : L.spokeNote[st];
    var body = "<p>" + esc(note) + "</p>";
    var r = (d.regions || []).find(function (x) { return x.key === t.region; });
    if (r && r.temp != null) body += "<p>" + L.nearby(r) + "</p>";
    return '<div class="status-head"><span class="status-dot ' + st + '"></span>' +
      '<span class="status-badge ' + st + '">' + L.badge[st] + "</span></div>" +
      (t.code === "PR1" ? summitHead(d.weather) : "") +
      '<div class="status-body">' + body + "</div>" + stamp(d);
  }

  var el = document.getElementById("statusCard");
  if (!el) return;
  lang = (document.documentElement.lang || "en").slice(0, 2).toLowerCase();
  L = LANGS[lang] || LANGS.en;
  var code = el.getAttribute("data-trail");
  if (!code || code === "PR1") {
    var css = document.createElement("style");
    css.textContent = ".summit-head{padding:0 18px 12px;font-weight:800;font-size:clamp(20px,6vw,28px)}" +
      ".summit-badge.CLEAR{color:var(--open,#1E7A45)}.summit-badge.CLOUDY{color:var(--closed,#B3372E)}";
    document.head.appendChild(css);
  }
  function draw(d) {
    if (code) {
      var t = (d.trails || []).find(function (x) { return x.code === code; });
      el.innerHTML = renderSpoke(t, d);
    } else {
      el.innerHTML = render(d, L);
    }
  }
  fetch("/status.json", { cache: "no-cache" })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      draw(d);
      if (!code || code === "PR1") {  // swap the morning reading for IPMA's latest hour
        liveSummit().then(function (w) { if (w) { d.weather = w; draw(d); } }).catch(function () {});
      }
    })
    .catch(function () { /* keep the static fallback already in the card */ });
})();
