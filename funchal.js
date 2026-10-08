/* Funchal page renderer (owner, 2026-10-08): "what's on in the city while I'm in it".
   Reads /funchal.json (scripts/update_funchal.py, daily) and fills:
     #now        the Levadinho panel at the top: what Levadinho would answer this visitor at this moment.
                 It is picked from three signals: the Madeira time (slot + weekday/holiday), the landing page
                 (data-page on #now) and whether the visitor scanned a Levadinho QR code (window.LEVADINHO_QR,
                 set by /qr.js from the #qr=<code> the /q/<code>/ link adds). Same for everyone at the same
                 moment, so the page's fixed core (title, H1, FAQ, the sections below) is what search engines index.
     #fxOpen     status column of the opening-hours table ("open now / opens at / closed today")
     #fxLidos    today's lido hours
     #fxEvents   the events list, with Today / Tomorrow / weekday labels (no dates on the page, owner's rule)
   Everything degrades to the static HTML the generator and the updater wrote. No cookies, nothing stored. */
(function () {
  "use strict";
  var LANG = (document.documentElement.lang || "en").slice(0, 2);
  var TZ = "Atlantic/Madeira";
  var DOW = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];

  var T = {
    en: {
      until: "until", ongoing: "On now", museums: "{n} museums",
      hi: { morning: "Good morning.", day: "Good afternoon.", evening: "Good evening.", night: "Planning tomorrow?" },
      qrhi: "You're in Funchal. Here's what matters right now.",
      today: "Today", tomorrow: "Tomorrow", tonight: "Tonight",
      wx: "{when} in Funchal: {min}–{max} °C, {sky}{rain}.", rain: " ({p}% chance of rain)",
      uv: " UV {uv}: sun cream at midday.",
      marketOpen: "The Mercado dos Lavradores is open until {to}.", marketLater: "The Mercado dos Lavradores opens at {at}.",
      marketClosed: "The Mercado dos Lavradores is closed {when}.", marketDone: "The Mercado dos Lavradores has closed for today.",
      fair: "{when} the market's top floor has the {theme} fair, {from}–{to}.",
      cable: "The cable car up to Monte runs {from}–{to}.", cableLeft: "Last cable car: {to}. Going down later? Bus {line} from Monte to the centre until {bus}, or walk down.",
      cableGone: "The cable car has stopped for today. From Monte: bus {line} to the centre until {bus}, or walk down.",
      openNow: "Open right now: {list}.", noneOpen: "Most museums and sights have closed for today.",
      sunClosed: "{when} is a {kind}: the market and most museums are closed. Open: {list}.",
      kind: { sunday: "Sunday", holiday: "public holiday" }, parking: " Street parking is free.",
      lido: "The lidos are open until {to} (adults €6). Sea {sst} °C, waves {w} m.",
      seaWarn: "IPMA has a {level} warning for the south coast ({type}): keep away from the sea front.",
      sunset: "Sunset {at}.", sunrise: "Sunrise {at}.",
      ev: "{when}: {list}.", noEv: "No events listed {when} by the city's or the Region's events guides.",
      lastBus: "Last buses to the centre: from the Lido {lido} (line {lline}), from Praia Formosa {formosa} (line {fline}).",
      tmrClosed: "Tomorrow is a {kind}: the market and most museums will be closed.",
      ask: "Ask Levadinho anything else", level: { yellow: "yellow", orange: "orange", red: "red" },
      st: { open: "Open now", until: "until {t}", opens: "Opens at {t}", closed: "Closed now", closedToday: "Closed today", check: "Check the hours" },
      lidoToday: "Open today {from}–{to}", lidoNone: "Hours for today not published yet",
      and: " and ", more: " and {n} more"
    },
    pt: {
      until: "até", ongoing: "A decorrer", museums: "{n} museus",
      hi: { morning: "Bom dia.", day: "Boa tarde.", evening: "Boa noite.", night: "A planear o dia de amanhã?" },
      qrhi: "Está no Funchal. Isto é o que interessa agora.",
      today: "Hoje", tomorrow: "Amanhã", tonight: "Esta noite",
      wx: "{when} no Funchal: {min}–{max} °C, {sky}{rain}.", rain: " ({p}% de probabilidade de chuva)",
      uv: " UV {uv}: protetor solar ao meio-dia.",
      marketOpen: "O Mercado dos Lavradores está aberto até às {to}.", marketLater: "O Mercado dos Lavradores abre às {at}.",
      marketClosed: "O Mercado dos Lavradores está fechado {when}.", marketDone: "O Mercado dos Lavradores já fechou hoje.",
      fair: "{when} há a feira de {theme} no último piso do mercado, {from}–{to}.",
      cable: "O teleférico para o Monte funciona das {from} às {to}.", cableLeft: "Último teleférico: {to}. Vai descer mais tarde? Autocarro {line} do Monte para o centro até às {bus}, ou a pé.",
      cableGone: "O teleférico já parou hoje. Do Monte: autocarro {line} para o centro até às {bus}, ou a pé.",
      openNow: "Aberto agora: {list}.", noneOpen: "A maioria dos museus e atrações já fechou hoje.",
      sunClosed: "{when} é {kind}: o mercado e a maioria dos museus estão fechados. Abertos: {list}.",
      kind: { sunday: "domingo", holiday: "feriado" }, parking: " O estacionamento na rua é gratuito.",
      lido: "Os complexos balneares estão abertos até às {to} (adultos 6 €). Mar a {sst} °C, ondas de {w} m.",
      seaWarn: "O IPMA tem aviso {level} para a costa sul ({type}): mantenha-se afastado da frente de mar.",
      sunset: "Pôr do sol às {at}.", sunrise: "Nascer do sol às {at}.",
      ev: "{when}: {list}.", noEv: "Os guias de eventos da Câmara e da Região não listam eventos para {when}.",
      lastBus: "Últimos autocarros para o centro: do Lido às {lido} (linha {lline}), da Praia Formosa às {formosa} (linha {fline}).",
      tmrClosed: "Amanhã é {kind}: o mercado e a maioria dos museus estarão fechados.",
      ask: "Pergunte mais ao Levadinho", level: { yellow: "amarelo", orange: "laranja", red: "vermelho" },
      st: { open: "Aberto agora", until: "até às {t}", opens: "Abre às {t}", closed: "Fechado agora", closedToday: "Fechado hoje", check: "Confirme o horário" },
      lidoToday: "Aberto hoje {from}–{to}", lidoNone: "Horário de hoje ainda não publicado",
      and: " e ", more: " e mais {n}"
    },
    fr: {
      until: "jusqu'à", ongoing: "En cours", museums: "{n} musées",
      hi: { morning: "Bonjour.", day: "Bon après-midi.", evening: "Bonsoir.", night: "Vous préparez demain ?" },
      qrhi: "Vous êtes à Funchal. Voici ce qui compte maintenant.",
      today: "Aujourd'hui", tomorrow: "Demain", tonight: "Ce soir",
      wx: "{when} à Funchal : {min}–{max} °C, {sky}{rain}.", rain: " ({p} % de risque de pluie)",
      uv: " UV {uv} : crème solaire à midi.",
      marketOpen: "Le Mercado dos Lavradores est ouvert jusqu'à {to}.", marketLater: "Le Mercado dos Lavradores ouvre à {at}.",
      marketClosed: "Le Mercado dos Lavradores est fermé {when}.", marketDone: "Le Mercado dos Lavradores a fermé pour aujourd'hui.",
      fair: "{when}, foire « {theme} » au dernier étage du marché, {from}–{to}.",
      cable: "Le téléphérique du Monte fonctionne de {from} à {to}.", cableLeft: "Dernier téléphérique : {to}. Vous redescendez plus tard ? Bus {line} du Monte au centre jusqu'à {bus}, ou à pied.",
      cableGone: "Le téléphérique est arrêté pour aujourd'hui. Depuis le Monte : bus {line} jusqu'au centre jusqu'à {bus}, ou à pied.",
      openNow: "Ouvert en ce moment : {list}.", noneOpen: "La plupart des musées et des sites ont fermé pour aujourd'hui.",
      sunClosed: "{when}, c'est {kind} : le marché et la plupart des musées sont fermés. Ouverts : {list}.",
      kind: { sunday: "dimanche", holiday: "jour férié" }, parking: " Le stationnement dans la rue est gratuit.",
      lido: "Les complexes balnéaires sont ouverts jusqu'à {to} (adultes 6 €). Mer à {sst} °C, vagues de {w} m.",
      seaWarn: "L'IPMA a émis une alerte {level} pour la côte sud ({type}) : restez à l'écart du front de mer.",
      sunset: "Coucher du soleil à {at}.", sunrise: "Lever du soleil à {at}.",
      ev: "{when} : {list}.", noEv: "Les agendas de la ville et de la Région n'annoncent aucun événement {when}.",
      lastBus: "Derniers bus vers le centre : depuis le Lido à {lido} (ligne {lline}), depuis Praia Formosa à {formosa} (ligne {fline}).",
      tmrClosed: "Demain, c'est {kind} : le marché et la plupart des musées seront fermés.",
      ask: "Posez une autre question à Levadinho", level: { yellow: "jaune", orange: "orange", red: "rouge" },
      st: { open: "Ouvert", until: "jusqu'à {t}", opens: "Ouvre à {t}", closed: "Fermé", closedToday: "Fermé aujourd'hui", check: "Vérifiez les horaires" },
      lidoToday: "Ouvert aujourd'hui {from}–{to}", lidoNone: "Horaires du jour pas encore publiés",
      and: " et ", more: " et {n} autres"
    },
    de: {
      until: "bis", ongoing: "Laufend", museums: "{n} Museen",
      hi: { morning: "Guten Morgen.", day: "Guten Tag.", evening: "Guten Abend.", night: "Sie planen morgen?" },
      qrhi: "Sie sind in Funchal. Das ist jetzt wichtig.",
      today: "Heute", tomorrow: "Morgen", tonight: "Heute Abend",
      wx: "{when} in Funchal: {min}–{max} °C, {sky}{rain}.", rain: " ({p} % Regenwahrscheinlichkeit)",
      uv: " UV {uv}: mittags Sonnencreme.",
      marketOpen: "Der Mercado dos Lavradores hat bis {to} Uhr geöffnet.", marketLater: "Der Mercado dos Lavradores öffnet um {at} Uhr.",
      marketClosed: "Der Mercado dos Lavradores ist {when} geschlossen.", marketDone: "Der Mercado dos Lavradores hat für heute geschlossen.",
      fair: "{when} findet im obersten Stock der Markthalle der Themenmarkt „{theme}“ statt, {from}–{to} Uhr.",
      cable: "Die Seilbahn zum Monte fährt von {from} bis {to} Uhr.", cableLeft: "Letzte Seilbahn: {to} Uhr. Später hinunter? Bus {line} vom Monte ins Zentrum bis {bus} Uhr, oder zu Fuß.",
      cableGone: "Die Seilbahn fährt heute nicht mehr. Vom Monte: Bus {line} ins Zentrum bis {bus} Uhr, oder zu Fuß.",
      openNow: "Jetzt geöffnet: {list}.", noneOpen: "Die meisten Museen und Sehenswürdigkeiten haben für heute geschlossen.",
      sunClosed: "{when} ist {kind}: Markthalle und die meisten Museen sind geschlossen. Geöffnet: {list}.",
      kind: { sunday: "Sonntag", holiday: "Feiertag" }, parking: " Parken an der Straße ist kostenlos.",
      lido: "Die Badeanlagen haben bis {to} Uhr geöffnet (Erwachsene 6 €). Meer {sst} °C, Wellen {w} m.",
      seaWarn: "Das IPMA hat für die Südküste eine {level} Warnung ({type}): Halten Sie Abstand zur Uferfront.",
      sunset: "Sonnenuntergang um {at} Uhr.", sunrise: "Sonnenaufgang um {at} Uhr.",
      ev: "{when}: {list}.", noEv: "Die Veranstaltungskalender der Stadt und der Region nennen {when} keine Termine.",
      lastBus: "Letzte Busse ins Zentrum: ab Lido {lido} Uhr (Linie {lline}), ab Praia Formosa {formosa} Uhr (Linie {fline}).",
      tmrClosed: "Morgen ist {kind}: Markthalle und die meisten Museen sind geschlossen.",
      ask: "Fragen Sie Levadinho noch etwas", level: { yellow: "gelbe", orange: "orange", red: "rote" },
      st: { open: "Jetzt geöffnet", until: "bis {t} Uhr", opens: "Öffnet um {t} Uhr", closed: "Jetzt geschlossen", closedToday: "Heute geschlossen", check: "Öffnungszeiten prüfen" },
      lidoToday: "Heute geöffnet {from}–{to} Uhr", lidoNone: "Öffnungszeiten für heute noch nicht veröffentlicht",
      and: " und ", more: " und {n} weitere"
    },
    pl: {
      until: "do", ongoing: "Trwa", museums: "muzea: {n}",
      hi: { morning: "Dzień dobry.", day: "Dzień dobry.", evening: "Dobry wieczór.", night: "Planujesz jutro?" },
      qrhi: "Jesteś w Funchal. Oto, co ważne teraz.",
      today: "Dziś", tomorrow: "Jutro", tonight: "Dziś wieczorem",
      wx: "{when} w Funchal: {min}–{max} °C, {sky}{rain}.", rain: " ({p}% szans na deszcz)",
      uv: " UV {uv}: w południe krem z filtrem.",
      marketOpen: "Mercado dos Lavradores jest otwarty do {to}.", marketLater: "Mercado dos Lavradores otwiera się o {at}.",
      marketClosed: "Mercado dos Lavradores jest {when} zamknięty.", marketDone: "Mercado dos Lavradores jest już dziś zamknięty.",
      fair: "{when} na najwyższym piętrze targu jarmark „{theme}”, {from}–{to}.",
      cable: "Kolejka linowa na Monte kursuje {from}–{to}.", cableLeft: "Ostatnia kolejka: {to}. Schodzisz później? Autobus {line} z Monte do centrum do {bus} albo pieszo.",
      cableGone: "Kolejka już dziś nie kursuje. Z Monte: autobus {line} do centrum do {bus} albo pieszo.",
      openNow: "Teraz otwarte: {list}.", noneOpen: "Większość muzeów i atrakcji jest już dziś zamknięta.",
      sunClosed: "{when} jest {kind}: targ i większość muzeów są zamknięte. Otwarte: {list}.",
      kind: { sunday: "niedziela", holiday: "święto" }, parking: " Parkowanie na ulicy jest bezpłatne.",
      lido: "Kąpieliska są otwarte do {to} (dorośli 6 €). Morze {sst} °C, fale {w} m.",
      seaWarn: "IPMA wydało {level} ostrzeżenie dla południowego wybrzeża ({type}): trzymaj się z dala od nabrzeża.",
      sunset: "Zachód słońca o {at}.", sunrise: "Wschód słońca o {at}.",
      ev: "{when}: {list}.", noEv: "Kalendarze miasta i regionu nie podają wydarzeń na {when}.",
      lastBus: "Ostatnie autobusy do centrum: z Lido o {lido} (linia {lline}), z Praia Formosa o {formosa} (linia {fline}).",
      tmrClosed: "Jutro jest {kind}: targ i większość muzeów będą zamknięte.",
      ask: "Zapytaj Levadinho o coś jeszcze", level: { yellow: "żółte", orange: "pomarańczowe", red: "czerwone" },
      st: { open: "Teraz otwarte", until: "do {t}", opens: "Otwiera o {t}", closed: "Teraz zamknięte", closedToday: "Dziś zamknięte", check: "Sprawdź godziny" },
      lidoToday: "Dziś otwarte {from}–{to}", lidoNone: "Godziny na dziś jeszcze nieopublikowane",
      and: " i ", more: " i {n} innych"
    }
  };
  var L = T[LANG] || T.en;
  var WEEKDAY = {
    en: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    pt: ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"],
    fr: ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"],
    de: ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"],
    pl: ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
  }[LANG] || [];
  var FAIR = {
    antiques: { en: "antiques and second-hand books", pt: "antiguidades e alfarrabista", fr: "antiquités et livres anciens", de: "Antiquitäten und Antiquariat", pl: "antyków i starych książek" },
    handcraft: { en: "handcraft", pt: "artesanato", fr: "artisanat", de: "Kunsthandwerk", pl: "rękodzieła" },
    gastronomy: { en: "gastronomy", pt: "gastronomia", fr: "gastronomie", de: "Gastronomie", pl: "gastronomii" },
    fashion: { en: "fashion, jewellery and decoration", pt: "moda, bijuteria e decoração", fr: "mode, bijoux et décoration", de: "Mode, Schmuck und Deko", pl: "mody, biżuterii i dekoracji" }
  };
  // IPMA weather types (weather-type-classe.json), grouped
  var SKY = {
    en: ["no forecast", "clear sky", "partly cloudy", "sunny intervals", "cloudy", "high cloud", "showers", "light showers", "heavy showers", "rain", "light rain", "heavy rain", "intermittent rain", "intermittent light rain", "intermittent heavy rain", "drizzle", "mist", "fog", "snow", "thunderstorms", "showers and thunder", "hail", "frost", "rain and thunder", "convective clouds", "partly cloudy", "fog", "cloudy", "snow showers", "rain and snow", "rain and snow"],
    pt: ["sem previsão", "céu limpo", "céu pouco nublado", "períodos de céu nublado", "céu nublado", "nuvens altas", "aguaceiros", "aguaceiros fracos", "aguaceiros fortes", "chuva", "chuva fraca", "chuva forte", "períodos de chuva", "períodos de chuva fraca", "períodos de chuva forte", "chuvisco", "neblina", "nevoeiro", "neve", "trovoada", "aguaceiros e trovoada", "granizo", "geada", "chuva e trovoada", "nebulosidade convectiva", "céu pouco nublado", "nevoeiro", "céu nublado", "aguaceiros de neve", "chuva e neve", "chuva e neve"],
    fr: ["pas de prévision", "ciel dégagé", "peu nuageux", "éclaircies", "nuageux", "nuages élevés", "averses", "faibles averses", "fortes averses", "pluie", "pluie faible", "forte pluie", "pluie intermittente", "pluie faible intermittente", "forte pluie intermittente", "bruine", "brume", "brouillard", "neige", "orages", "averses orageuses", "grêle", "gel", "pluie et orage", "nuages convectifs", "peu nuageux", "brouillard", "nuageux", "averses de neige", "pluie et neige", "pluie et neige"],
    de: ["keine Vorhersage", "klar", "leicht bewölkt", "teils sonnig", "bewölkt", "hohe Wolken", "Schauer", "leichte Schauer", "starke Schauer", "Regen", "leichter Regen", "starker Regen", "zeitweise Regen", "zeitweise leichter Regen", "zeitweise starker Regen", "Nieselregen", "Dunst", "Nebel", "Schnee", "Gewitter", "Schauer und Gewitter", "Hagel", "Frost", "Regen und Gewitter", "Quellwolken", "leicht bewölkt", "Nebel", "bewölkt", "Schneeschauer", "Regen und Schnee", "Regen und Schnee"],
    pl: ["brak prognozy", "bezchmurnie", "małe zachmurzenie", "przejaśnienia", "pochmurno", "chmury wysokie", "przelotne opady", "słabe przelotne opady", "silne przelotne opady", "deszcz", "słaby deszcz", "silny deszcz", "przelotny deszcz", "przelotny słaby deszcz", "przelotny silny deszcz", "mżawka", "zamglenie", "mgła", "śnieg", "burze", "przelotne opady z burzą", "grad", "przymrozek", "deszcz z burzą", "chmury konwekcyjne", "małe zachmurzenie", "mgła", "pochmurno", "przelotny śnieg", "deszcz ze śniegiem", "deszcz ze śniegiem"]
  };

  function num(x) { return typeof x === "number" ? x.toLocaleString(LANG === "en" ? "en-GB" : LANG) : x; }
  function fmt(s, o) { return s.replace(/\{(\w+)\}/g, function (_, k) { return o[k] == null ? "" : o[k]; }); }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function list(a, max) {
    max = max || 4;
    if (a.length <= max) return a.length > 1 ? a.slice(0, -1).join(", ") + L.and + a[a.length - 1] : a.join("");
    return a.slice(0, max).join(", ") + fmt(L.more, { n: a.length - max });
  }

  // Madeira clock
  function madeiraNow() {
    var p = {};
    new Intl.DateTimeFormat("en-GB", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23" })
      .formatToParts(new Date()).forEach(function (x) { p[x.type] = x.value; });
    return { date: p.year + "-" + p.month + "-" + p.day, hm: p.hour + ":" + p.minute, h: +p.hour + (+p.minute) / 60 };
  }
  function dow(iso) { var d = new Date(iso + "T12:00:00Z"); return (d.getUTCDay() + 6) % 7; }
  function addDays(iso, n) { var d = new Date(iso + "T12:00:00Z"); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); }
  function slot(h) { return h >= 5 && h < 12 ? "morning" : h >= 12 && h < 17 ? "day" : h >= 17 && h < 21.5 ? "evening" : "night"; }

  // Opening rules: hours[key] = [[from, to], ...]; key = mon..sun or hol
  function dayInfo(data, iso) {
    var rec = (data.days || []).filter(function (d) { return d.date === iso; })[0] || null;
    var type = rec ? rec.type : (dow(iso) === 5 ? "saturday" : dow(iso) === 6 ? "sunday" : "weekday");
    return { rec: rec, type: type, key: type === "holiday" ? "hol" : DOW[dow(iso)] };
  }
  function spans(p, iso, di) {
    if (p.months && p.months.indexOf(+iso.slice(5, 7)) < 0) return null;          // hours not known this month
    if (p.closed && p.closed.indexOf(iso.slice(5)) >= 0) return [];
    return p.hours[di.key] || [];
  }
  function state(p, iso, di, hm) {
    var s = spans(p, iso, di);
    if (s === null) return { k: "check" };
    if (!s.length) return { k: "closedToday" };
    for (var i = 0; i < s.length; i++) {
      if (hm >= s[i][0] && hm < s[i][1]) return { k: "open", to: s[i][1] };
      if (hm < s[i][0]) return { k: "opens", at: s[i][0] };
    }
    return { k: "closed" };
  }
  function place(data, id) { return (data.places || []).filter(function (p) { return p.id === id; })[0]; }
  var SHORT = { cablecar: { en: "the Monte cable car", pt: "o teleférico do Monte", fr: "le téléphérique du Monte", de: "die Seilbahn zum Monte", pl: "kolejka na Monte" },
                gardencable: { en: "the Botanical Garden cable car", pt: "o teleférico do Jardim Botânico", fr: "le téléphérique du Jardin botanique", de: "die Seilbahn zum Botanischen Garten", pl: "kolejka do Ogrodu Botanicznego" },
                toboggan: { en: "the Monte toboggans", pt: "os carros de cesto do Monte", fr: "les luges du Monte", de: "die Korbschlitten am Monte", pl: "sanie z Monte" },
                botanical: { en: "the Botanical Garden", pt: "o Jardim Botânico", fr: "le Jardin botanique", de: "der Botanische Garten", pl: "Ogród Botaniczny" } };
  function pname(p) { return (SHORT[p.id] && (SHORT[p.id][LANG] || SHORT[p.id].en)) || p.name; }

  function eventsOn(data, iso, fromHm) {
    return (data.events || []).filter(function (e) {
      if (e.start.slice(0, 10) !== iso) return false;                              // multi-day events only on their first day
      return !fromHm || e.all_day || e.start.length <= 10 || e.start.slice(11, 16) >= fromHm;
    });
  }
  function evLabel(e) { return (e.all_day || e.start.length <= 10 ? "" : e.start.slice(11, 16) + " ") + e.title; }

  // ------------------------------------------------------------------ the Levadinho panel
  function panel(data, qr) {
    var now = madeiraNow(), iso = now.date, hm = now.hm, sl = slot(now.h);
    var tmr = addDays(iso, 1), di = dayInfo(data, iso), dt = dayInfo(data, tmr);
    var rec = di.rec || {}, trec = dt.rec || {};
    var out = [];
    var planTomorrow = sl === "night";
    var when = planTomorrow ? L.tomorrow : L.today;
    var wrec = planTomorrow ? trec : rec, wdi = planTomorrow ? dt : di;

    function weather() {
      var w = wrec.weather;
      if (!w) return;
      var sky = (SKY[LANG] || SKY.en)[w.wtype] || "";
      out.push(fmt(L.wx, { when: when, min: w.tmin, max: w.tmax, sky: sky, rain: w.rain >= 30 ? fmt(L.rain, { p: w.rain }) : "" }) +
               (w.uv >= 6 && !planTomorrow && sl !== "evening" ? fmt(L.uv, { uv: Math.round(w.uv) }) : ""));
    }
    function seaWarning() {
      var ws = (data.sea && data.sea.warnings) || [];
      var w = ws.filter(function (x) { return x.start.slice(0, 10) <= (planTomorrow ? tmr : iso) && x.end.slice(0, 10) >= iso; })[0];
      if (w) out.push(fmt(L.seaWarn, { level: L.level[w.level] || w.level, type: w.type }));
    }
    function market() {
      var m = place(data, "market");
      if (!m) return;
      if (planTomorrow) {
        if (!(spans(m, tmr, dt) || []).length) out.push(fmt(L.marketClosed, { when: L.tomorrow.toLowerCase() }));
        return;
      }
      var s = state(m, iso, di, hm);
      if (s.k === "open") out.push(fmt(L.marketOpen, { to: s.to }));
      else if (s.k === "opens") out.push(fmt(L.marketLater, { at: s.at }));
      else if (s.k === "closed") out.push(L.marketDone);
    }
    function fair() {
      var f = wrec.fair;
      if (!f || !f.hours || (!planTomorrow && hm >= f.hours[1])) return;
      var th = (FAIR[f.theme] && (FAIR[f.theme][LANG] || FAIR[f.theme].en)) || f.pt;
      out.push(fmt(L.fair, { when: when, theme: th, from: f.hours[0], to: f.hours[1] }));
    }
    function sundayClosed() {     // Sunday / holiday: what is open instead
      if (wdi.type !== "sunday" && wdi.type !== "holiday") return false;
      var d = planTomorrow ? tmr : iso, dI = planTomorrow ? dt : di;
      var open = (data.places || []).filter(function (p) { return (spans(p, d, dI) || []).length; }).map(pname);
      out.push(fmt(L.sunClosed, { when: when, kind: L.kind[wdi.type], list: list(open, 5) }) + L.parking);
      return true;
    }
    function cable() {
      var c = place(data, "cablecar");
      if (!c) return;
      var mb = data.last_bus && data.last_bus.monte && data.last_bus.monte[rec.bus || "weekday"];
      var s = state(c, iso, di, hm);
      if (s.k === "open" && sl !== "morning" && mb) out.push(fmt(L.cableLeft, { to: s.to, line: mb[1], bus: mb[0] }));
      else if (s.k === "open" || s.k === "opens") { var sp = spans(c, iso, di); out.push(fmt(L.cable, { from: sp[0][0], to: sp[sp.length - 1][1] })); }
      else if (s.k === "closed" && mb && hm < "23:59" && (hm <= mb[0] || mb[0] < "04:00")) out.push(fmt(L.cableGone, { line: mb[1], bus: mb[0] }));
    }
    function openNow() {
      var open = (data.places || []).filter(function (p) { return p.id !== "market" && state(p, iso, di, hm).k === "open"; });
      var top = open.filter(function (p) { return p.kind !== "museum"; })
        .map(function (p) { return pname(p) + " (" + fmt(L.st.until, { t: state(p, iso, di, hm).to }) + ")"; });
      var mus = open.filter(function (p) { return p.kind === "museum"; }).length;
      if (mus) top.push(fmt(L.museums, { n: mus }));
      if (top.length) out.push(fmt(L.openNow, { list: list(top, 6) }));
      else if (hm >= "18:00") out.push(L.noneOpen);
    }
    function lidos() {
      var ls = (data.lidos || []).filter(function (l) { return l.hours && l.window && l.window[0] <= iso && iso <= l.window[1]; });
      if (!ls.length || hm >= ls[0].hours[1] || hm < "08:00") return;
      var sea = data.sea && data.sea.date === iso ? data.sea : null;
      var t = fmt(L.lido, { to: ls[0].hours[1], sst: sea ? sea.sst : "", w: sea ? sea.wave.map(num).join("–") : "" });
      out.push(sea ? t : t.replace(/\)\..*$/, ")."));
    }
    function events(label, d, from) {
      var all = eventsOn(data, d, from), ev;
      if (from) {   // evening: timed events still to come; events without a time are "today"
        var timed = all.filter(function (e) { return !(e.all_day || e.start.length <= 10); }).map(evLabel);
        var untimed = all.filter(function (e) { return e.all_day || e.start.length <= 10; }).map(evLabel);
        if (timed.length) out.push(fmt(L.ev, { when: label, list: list(timed, 3) }));
        if (untimed.length) out.push(fmt(L.ev, { when: L.today, list: list(untimed, 3) }));
        if (!timed.length && !untimed.length) out.push(fmt(L.noEv, { when: label.toLowerCase() }));
        return;
      }
      ev = all.map(evLabel);
      out.push(ev.length ? fmt(L.ev, { when: label, list: list(ev, 3) }) : fmt(L.noEv, { when: label.toLowerCase() }));
    }
    function sun() { if (rec.sunset && hm < rec.sunset) out.push(fmt(L.sunset, { at: rec.sunset })); }
    function lastBus() {
      var lb = data.last_bus, k = rec.bus || "weekday";
      if (lb && lb.lido && lb.lido[k] && lb.formosa && lb.formosa[k])
        out.push(fmt(L.lastBus, { lido: lb.lido[k][0], lline: lb.lido[k][1], formosa: lb.formosa[k][0], fline: lb.formosa[k][1] }));
    }
    function tomorrowClosed() { if (dt.type === "sunday" || dt.type === "holiday") out.push(fmt(L.tmrClosed, { kind: L.kind[dt.type] })); }

    // what leads depends on the slot; a QR scan means the visitor is in the city now, so "now" comes first
    if (sl === "morning") {
      seaWarning(); if (!sundayClosed()) market(); fair(); cable(); events(L.today, iso); weather();
    } else if (sl === "day") {
      seaWarning(); if (!sundayClosed()) { openNow(); market(); } else { cable(); } fair(); lidos(); events(L.today, iso); if (!qr) weather();
    } else if (sl === "evening") {
      if (qr) { cable(); events(L.tonight, iso, hm); sun(); lastBus(); }
      else { events(L.tonight, iso, hm); sun(); cable(); lastBus(); tomorrowClosed(); }
    } else {
      if (qr && now.h >= 21.5) { cable(); lastBus(); }
      weather(); if (!sundayClosed()) market(); fair(); events(L.tomorrow, tmr); seaWarning();
      if (trec.sunrise && !qr) out.push(fmt(L.sunrise, { at: trec.sunrise }));
    }
    var hi = qr ? L.qrhi : L.hi[sl];
    return { hi: hi, lines: out.slice(0, 6) };
  }

  function renderPanel(data) {
    var box = document.getElementById("now");
    if (!box) return;
    var qr = window.LEVADINHO_QR || null;
    var p = panel(data, qr);
    var txt = box.querySelector(".now-text");
    if (!txt || !p.lines.length) return;
    txt.innerHTML = "<p class=\"now-hi\">" + esc(p.hi) + "</p><ul>" +
      p.lines.map(function (l) { return "<li>" + esc(l) + "</li>"; }).join("") + "</ul>";
    var a = box.querySelector(".now-ask");
    if (a) { a.textContent = L.ask; a.removeAttribute("hidden"); }
    box.setAttribute("data-slot", slot(madeiraNow().h));
    if (qr) box.setAttribute("data-qr", qr);
  }

  // ------------------------------------------------------------------ open-now column, lidos, events
  function renderOpen(data) {
    var now = madeiraNow(), di = dayInfo(data, now.date);
    document.querySelectorAll("[data-place]").forEach(function (el) {
      var p = place(data, el.getAttribute("data-place"));
      if (!p) return;
      var s = state(p, now.date, di, now.hm), t;
      if (s.k === "open") t = L.st.open + ", " + fmt(L.st.until, { t: s.to });
      else if (s.k === "opens") t = fmt(L.st.opens, { t: s.at });
      else t = L.st[s.k];
      el.textContent = t;
      el.className = "fx-st " + (s.k === "open" ? "OPEN" : s.k === "opens" ? "PARTIAL" : s.k === "check" ? "" : "CLOSED");
    });
  }
  function renderLidos(data) {
    var iso = madeiraNow().date;
    document.querySelectorAll("[data-lido]").forEach(function (el) {
      var l = (data.lidos || []).filter(function (x) { return x.id === el.getAttribute("data-lido"); })[0];
      if (!l) return;
      el.textContent = l.hours && l.window && l.window[0] <= iso && iso <= l.window[1]
        ? fmt(L.lidoToday, { from: l.hours[0], to: l.hours[1] }) : L.lidoNone;
    });
  }
  function renderEvents(data) {
    var box = document.getElementById("fxEvents");
    if (!box) return;
    var iso = madeiraNow().date, last = addDays(iso, 6);
    var ev = (data.events || []).filter(function (e) { return e.start.slice(0, 10) <= last && e.end.slice(0, 10) >= iso; });
    if (!ev.length) return;   // keep the static "no events" sentence
    function label(d) { return d === iso ? L.today : d === addDays(iso, 1) ? L.tomorrow : WEEKDAY[dow(d)]; }
    box.innerHTML = "<ul class=\"fx-events\">" + ev.slice(0, 14).map(function (e) {
      var s = e.start.slice(0, 10), w = s < iso ? "" : label(s);
      if (!(e.all_day || e.start.length <= 10)) w += " " + e.start.slice(11, 16);
      var en = e.end.slice(0, 10);
      if (en > s && en <= last) w += (w ? " " : "") + L.until + " " + label(en).toLowerCase();
      if (!w.trim()) w = L.ongoing;
      return "<li><b>" + esc(w.trim()) + "</b> · <a class=\"plain\" href=\"" + esc(e.url) + "\" target=\"_blank\" rel=\"noopener\">" +
        esc(e.title) + "</a>" + (e.venue ? " · " + esc(e.venue) : "") + "</li>";
    }).join("") + "</ul>";
  }

  function go() {
    fetch("/funchal.json", { cache: "no-cache" }).then(function (r) { return r.json(); }).then(function (data) {
      renderPanel(data); renderOpen(data); renderLidos(data); renderEvents(data);
    }).catch(function () {});
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", go); else go();
})();
