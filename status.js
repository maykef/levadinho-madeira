/* Levadinho — renders the live PR1 status card from /status.json.
   Language is taken from <html lang>. Data is language-neutral; all wording
   lives in LANGS below, so adding a language = adding one block here + the page.
   The daily GitHub Action writes /status.json; nothing else needs editing. */
(function () {
  "use strict";

  var LANGS = {
    en: {
      badge: { OPEN: "OPEN", PARTIAL: "PARTIAL", CLOSED: "CLOSED" },
      officialNote: "Official note:",
      defaultNote: {
        OPEN: "One-way only: Pico do Areeiro → Pico Ruivo. Book on SIMplifica before you go.",
        PARTIAL: "Access is restricted — read the official note above before planning.",
        CLOSED: "The trail is officially closed. See below for rescheduling your SIMplifica booking and open alternatives."
      },
      weather: function (w) {
        if (!w || !w.ok) return "Check the mountain forecast before you go — summit conditions differ sharply from Funchal.";
        var cloud = w.in_cloud ? ", likely in cloud/fog (humidity " + Math.round(w.humidity) + "%)" : "";
        var wind = w.wind_strong ? ", strong wind (" + Math.round(w.wind_kmh) + " km/h)" : "";
        return "Summit weather now: " + Math.round(w.temp_c) + "°C measured at the Pico do Areeiro station (~1,800 m)" + cloud + wind + " — expect it far colder and cloudier than Funchal.";
      },
      advisory: "The webcam shows you a snippet of the summit right now — don't assume conditions will stay that way. Pack a good anorak and fleece, carry enough water, and wear adequate footwear.",
      lastChecked: "Last checked:", madeiraTime: "(Madeira time)", source: "Source:"
    },
    fr: {
      badge: { OPEN: "OUVERT", PARTIAL: "PARTIEL", CLOSED: "FERMÉ" },
      officialNote: "Note officielle :",
      defaultNote: {
        OPEN: "Sens unique : Pico do Areeiro → Pico Ruivo. Réservez sur SIMplifica avant de partir.",
        PARTIAL: "Accès restreint — lisez la note officielle ci-dessus avant de planifier.",
        CLOSED: "Le sentier est officiellement fermé. Voir ci-dessous pour reprogrammer votre réservation SIMplifica et les alternatives ouvertes."
      },
      weather: function (w) {
        if (!w || !w.ok) return "Consultez la météo de montagne avant de partir — les conditions au sommet diffèrent fortement de Funchal.";
        var cloud = w.in_cloud ? ", probablement dans les nuages/le brouillard (humidité " + Math.round(w.humidity) + " %)" : "";
        var wind = w.wind_strong ? ", vent fort (" + Math.round(w.wind_kmh) + " km/h)" : "";
        return "Météo au sommet : " + Math.round(w.temp_c) + " °C mesurés à la station du Pico do Areeiro (~1 800 m)" + cloud + wind + " — attendez-vous à bien plus froid et nuageux qu'à Funchal.";
      },
      advisory: "La webcam ne montre qu'un aperçu du sommet à l'instant — ne supposez pas que les conditions resteront les mêmes. Emportez un bon anorak et une polaire, assez d'eau, et portez des chaussures adaptées.",
      lastChecked: "Dernière vérification :", madeiraTime: "(heure de Madère)", source: "Source :"
    },
    de: {
      badge: { OPEN: "OFFEN", PARTIAL: "TEILWEISE", CLOSED: "GESPERRT" },
      officialNote: "Offizieller Hinweis:",
      defaultNote: {
        OPEN: "Nur Einbahnrichtung: Pico do Areeiro → Pico Ruivo. Vor dem Start auf SIMplifica buchen.",
        PARTIAL: "Zugang eingeschränkt — lesen Sie den offiziellen Hinweis oben, bevor Sie planen.",
        CLOSED: "Der Weg ist offiziell gesperrt. Siehe unten zum Umbuchen Ihrer SIMplifica-Reservierung und zu offenen Alternativen."
      },
      weather: function (w) {
        if (!w || !w.ok) return "Prüfen Sie vor dem Aufbruch den Bergwetterbericht — die Bedingungen am Gipfel unterscheiden sich stark von Funchal.";
        var cloud = w.in_cloud ? ", wahrscheinlich in Wolken/Nebel (Luftfeuchte " + Math.round(w.humidity) + " %)" : "";
        var wind = w.wind_strong ? ", starker Wind (" + Math.round(w.wind_kmh) + " km/h)" : "";
        return "Gipfelwetter jetzt: " + Math.round(w.temp_c) + " °C gemessen an der Station Pico do Areeiro (~1.800 m)" + cloud + wind + " — rechnen Sie mit deutlich kälterem und wolkigerem Wetter als in Funchal.";
      },
      advisory: "Die Webcam zeigt nur einen Moment des Gipfels — gehen Sie nicht davon aus, dass die Bedingungen so bleiben. Nehmen Sie einen guten Anorak und Fleece mit, genügend Wasser und tragen Sie geeignetes Schuhwerk.",
      lastChecked: "Zuletzt geprüft:", madeiraTime: "(Madeira-Zeit)", source: "Quelle:"
    },
    pl: {
      badge: { OPEN: "OTWARTY", PARTIAL: "CZĘŚCIOWO", CLOSED: "ZAMKNIĘTY" },
      officialNote: "Uwaga oficjalna:",
      defaultNote: {
        OPEN: "Tylko w jedną stronę: Pico do Areeiro → Pico Ruivo. Zarezerwuj w SIMplifica przed wyjściem.",
        PARTIAL: "Dostęp ograniczony — przed planowaniem przeczytaj powyższą uwagę oficjalną.",
        CLOSED: "Szlak jest oficjalnie zamknięty. Poniżej znajdziesz informacje o zmianie rezerwacji SIMplifica i otwartych alternatywach."
      },
      weather: function (w) {
        if (!w || !w.ok) return "Przed wyjściem sprawdź górską prognozę — warunki na szczycie znacznie różnią się od Funchal.";
        var cloud = w.in_cloud ? ", prawdopodobnie w chmurze/mgle (wilgotność " + Math.round(w.humidity) + " %)" : "";
        var wind = w.wind_strong ? ", silny wiatr (" + Math.round(w.wind_kmh) + " km/h)" : "";
        return "Pogoda na szczycie: " + Math.round(w.temp_c) + " °C zmierzone na stacji Pico do Areeiro (~1800 m)" + cloud + wind + " — spodziewaj się znacznie zimniej i bardziej pochmurno niż w Funchal.";
      },
      advisory: "Kamera pokazuje tylko chwilowy widok szczytu — nie zakładaj, że warunki się nie zmienią. Zabierz dobrą kurtkę i polar, wystarczająco wody i włóż odpowiednie obuwie.",
      lastChecked: "Ostatnie sprawdzenie:", madeiraTime: "(czas Madery)", source: "Źródło:"
    }
  };

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  function render(d, L) {
    var st = (d.status === "OPEN" || d.status === "CLOSED") ? d.status : "PARTIAL";
    var body = "";
    if (d.note) body += "<p><b>" + L.officialNote + "</b> " + esc(d.note) + "</p>";
    body += "<p>" + L.defaultNote[st] + "</p>";
    if (d.manual_note) body += "<p>" + esc(d.manual_note) + "</p>";
    body += "<p>" + L.weather(d.weather) + "</p>";
    body += '<p class="advisory">' + L.advisory + "</p>";
    return (
      '<div class="status-head"><span class="status-dot ' + st + '"></span>' +
      '<span class="status-badge ' + st + '">' + L.badge[st] + "</span></div>" +
      '<div class="status-body">' + body + "</div>" +
      '<div class="stamp"><span>' + L.lastChecked + " <b>" + esc(d.stamp) + "</b> " + L.madeiraTime +
      "</span><span>" + L.source + " IFCN / Visit Madeira · IPMA</span></div>"
    );
  }

  var el = document.getElementById("statusCard");
  if (!el) return;
  var lang = (document.documentElement.lang || "en").slice(0, 2).toLowerCase();
  var L = LANGS[lang] || LANGS.en;
  fetch("/status.json", { cache: "no-cache" })
    .then(function (r) { return r.json(); })
    .then(function (d) { el.innerHTML = render(d, L); })
    .catch(function () { /* keep the static fallback already in the card */ });
})();
