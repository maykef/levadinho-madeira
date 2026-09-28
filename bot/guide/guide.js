/* Levadinho audio guide — follows the phone's GPS along a route and plays each stop's clip.
 *
 * URL: guide/?r=<route id>&l=<lang>&t=<token>   (the bot sends this link)
 *      &sim=1[&speed=8][&tick=1000][&auto=1]  simulated walk along the route (desk tests, meeting
 *                        demo): speed × 1.4 m per fix, one fix every `tick` ms, `auto` starts without a tap
 *      &debug=1          show the raw GPS numbers
 *
 * How stops fire:
 *  - Each fix is projected onto the route to get "progress" (metres walked). Progress only
 *    searches a window ahead of the last value, so a loop's start and finish (same spot)
 *    can't be confused; after 3 off-route fixes it re-acquires over the whole route.
 *  - A stop can fire only once, only when progress has nearly reached it, and only after
 *    2 consecutive fixes inside its radius with usable accuracy.
 *  - A stop left behind without firing (screen was off, GPS drift) is marked "missed" and
 *    keeps a ▶ button. Clips queue, so two close stops play in order.
 *  - OFFLINE: as soon as the page opens it stores the page, the route and every clip in the
 *    visitor's language in the Cache Storage, and sw.js serves them with no signal (open the
 *    link once with signal, e.g. at the trailhead). The server log queue is kept in
 *    localStorage, so events recorded without signal are sent later, even after a reload.
 *  - LOCK-SCREEN TEST (2026-09-28): with a bot token (&t=…) the page records every GPS fix,
 *    stop event, clip result and a 10 s heartbeat to the server (guide/log → bot/tracklog/).
 *    The Start tap also starts a looping silent track (keeps iOS's audio session alive) and
 *    an AudioContext; clips play through Web Audio, which iOS 17.5+ doesn't suspend in the
 *    background. The log shows whether the page kept running with the screen locked.
 *    Finding: the page keeps running when locked, but watchPosition stops. So while GPS is
 *    silent (>8 s) the guide (1) polls getCurrentPosition every 10 s, (2) dead-reckons along
 *    the one-way route (steps × step length if the motion sensor still reports, otherwise
 *    last speed × time) and plays the next stop when the estimate reaches it, and (3) logs
 *    motion-sensor activity. Real GPS takes over again on unlock.
 */
(function () {
  "use strict";

  const UI = {
    en: {
      stops: "{n} stops · {km} km", start: "Start the guide",
      how: "Keep this page open with the screen on while you walk. Each stop plays by itself when you reach it.",
      offDl: "Downloading for offline use… {n}/{N}", offOk: "✓ Ready offline ({mb} MB): the guide now works without signal.", offFail: "⚠ Couldn't download everything for offline use. Tap here to try again.",
      walk: "Pocket mode", walkExit: "Press and hold 2 seconds to exit", pocketHint: "⚠️ Don't lock your screen: when it's locked, the guide loses your position and the stops won't play. Use Pocket mode instead.", noLock: "🔒 Do not lock your screen",
      nowPlaying: "Now playing", lastPlayed: "Last stop",
      gpsWait: "Waiting for GPS…", gpsOk: "GPS ok (±{a} m)", gpsWeak: "Weak GPS signal (±{a} m): stops won't trigger until it improves",
      gpsDenied: "Location is blocked. Allow location for this page in your browser settings, then reload.",
      gpsNone: "This browser has no GPS access.", off: "You seem to be off the route ({d} m away)",
      missedToast: "You passed {n} stop(s) without hearing them: tap ▶ to play.", wakeNo: "Your phone may lock the screen: tap it now and then to keep it on.",
      bad: "This guide link isn't valid or has expired. Ask Levadinho on WhatsApp for a new one (type \"guide\").",
      away: "{d} away", here: "here", played: "played", missed: "missed, tap ▶",
    },
    pt: {
      stops: "{n} paragens · {km} km", start: "Começar o guia",
      how: "Mantenha esta página aberta com o ecrã ligado enquanto caminha. Cada paragem toca sozinha quando lá chegar.",
      offDl: "A descarregar para usar sem rede… {n}/{N}", offOk: "✓ Pronto sem rede ({mb} MB): o guia já funciona sem sinal.", offFail: "⚠ Não foi possível descarregar tudo. Toque aqui para tentar de novo.",
      walk: "Modo bolso", walkExit: "Mantenha premido 2 segundos para sair", pocketHint: "⚠️ Não bloqueie o ecrã: com o ecrã bloqueado, o guia perde a sua posição e as paragens não tocam. Use antes o Modo bolso.", noLock: "🔒 Não bloqueie o ecrã",
      nowPlaying: "A tocar", lastPlayed: "Última paragem",
      gpsWait: "À espera do GPS…", gpsOk: "GPS ok (±{a} m)", gpsWeak: "Sinal de GPS fraco (±{a} m): as paragens só disparam quando melhorar",
      gpsDenied: "A localização está bloqueada. Permita a localização para esta página nas definições do navegador e recarregue.",
      gpsNone: "Este navegador não tem acesso ao GPS.", off: "Parece estar fora do percurso (a {d} m)",
      missedToast: "Passou {n} paragem(ns) sem as ouvir: toque em ▶ para ouvir.", wakeNo: "O telemóvel pode bloquear o ecrã: toque-lhe de vez em quando para o manter ligado.",
      bad: "Este link do guia não é válido ou expirou. Peça um novo ao Levadinho no WhatsApp (escreva \"guia\").",
      away: "a {d}", here: "aqui", played: "ouvida", missed: "perdida, toque em ▶",
    },
    fr: {
      stops: "{n} étapes · {km} km", start: "Démarrer le guide",
      how: "Gardez cette page ouverte, écran allumé, pendant la marche. Chaque étape se lance toute seule quand vous y arrivez.",
      offDl: "Téléchargement hors ligne… {n}/{N}", offOk: "✓ Prêt hors ligne ({mb} Mo) : le guide fonctionne sans réseau.", offFail: "⚠ Téléchargement incomplet. Touchez ici pour réessayer.",
      walk: "Mode poche", walkExit: "Maintenez 2 secondes pour quitter", pocketHint: "⚠️ Ne verrouillez pas l'écran : écran verrouillé, le guide perd votre position et les étapes ne se lancent pas. Utilisez plutôt le Mode poche.", noLock: "🔒 Ne verrouillez pas l'écran",
      nowPlaying: "En cours", lastPlayed: "Dernière étape",
      gpsWait: "En attente du GPS…", gpsOk: "GPS ok (±{a} m)", gpsWeak: "Signal GPS faible (±{a} m) : les étapes attendront un meilleur signal",
      gpsDenied: "La localisation est bloquée. Autorisez-la pour cette page dans les réglages du navigateur, puis rechargez.",
      gpsNone: "Ce navigateur n'a pas accès au GPS.", off: "Vous semblez hors du parcours (à {d} m)",
      missedToast: "Vous avez passé {n} étape(s) sans les écouter : touchez ▶ pour les lire.", wakeNo: "Le téléphone peut verrouiller l'écran : touchez-le de temps en temps.",
      bad: "Ce lien de guide n'est pas valide ou a expiré. Demandez-en un nouveau à Levadinho sur WhatsApp (écrivez « guide audio »).",
      away: "à {d}", here: "ici", played: "écoutée", missed: "manquée, touchez ▶",
    },
    de: {
      stops: "{n} Halte · {km} km", start: "Guide starten",
      how: "Lass diese Seite beim Gehen mit eingeschaltetem Bildschirm offen. Jeder Halt spielt von selbst, sobald du ihn erreichst.",
      offDl: "Wird für offline geladen… {n}/{N}", offOk: "✓ Offline bereit ({mb} MB): Der Guide funktioniert jetzt ohne Netz.", offFail: "⚠ Nicht alles konnte geladen werden. Tippe hier, um es erneut zu versuchen.",
      walk: "Taschenmodus", walkExit: "2 Sekunden gedrückt halten zum Beenden", pocketHint: "⚠️ Sperr den Bildschirm nicht: Bei gesperrtem Bildschirm verliert der Guide deine Position und die Halte spielen nicht. Nutze stattdessen den Taschenmodus.", noLock: "🔒 Bildschirm nicht sperren",
      nowPlaying: "Läuft gerade", lastPlayed: "Letzter Halt",
      gpsWait: "Warte auf GPS…", gpsOk: "GPS ok (±{a} m)", gpsWeak: "Schwaches GPS (±{a} m): Halte starten erst bei besserem Signal",
      gpsDenied: "Standort ist blockiert. Erlaube ihn für diese Seite in den Browser-Einstellungen und lade neu.",
      gpsNone: "Dieser Browser hat keinen GPS-Zugriff.", off: "Du scheinst abseits der Route zu sein ({d} m)",
      missedToast: "Du hast {n} Halt(e) verpasst: tippe auf ▶ zum Abspielen.", wakeNo: "Dein Handy kann den Bildschirm sperren: tippe ab und zu darauf.",
      bad: "Dieser Guide-Link ist ungültig oder abgelaufen. Frag Levadinho auf WhatsApp nach einem neuen (schreib „Führer“).",
      away: "{d} entfernt", here: "hier", played: "gehört", missed: "verpasst, tippe ▶",
    },
    pl: {
      stops: "{n} przystanków · {km} km", start: "Uruchom przewodnik",
      how: "Podczas marszu trzymaj tę stronę otwartą i ekran włączony. Każdy przystanek odtworzy się sam, gdy do niego dotrzesz.",
      offDl: "Pobieranie do użytku offline… {n}/{N}", offOk: "✓ Gotowe offline ({mb} MB): przewodnik działa teraz bez zasięgu.", offFail: "⚠ Nie udało się pobrać wszystkiego. Dotknij tutaj, aby spróbować ponownie.",
      walk: "Tryb kieszonkowy", walkExit: "Przytrzymaj 2 sekundy, aby wyjść", pocketHint: "⚠️ Nie blokuj ekranu: przy zablokowanym ekranie przewodnik traci Twoją pozycję i przystanki się nie odtworzą. Zamiast tego użyj trybu kieszonkowego.", noLock: "🔒 Nie blokuj ekranu",
      nowPlaying: "Teraz gra", lastPlayed: "Ostatni przystanek",
      gpsWait: "Czekam na GPS…", gpsOk: "GPS ok (±{a} m)", gpsWeak: "Słaby sygnał GPS (±{a} m): przystanki poczekają na lepszy sygnał",
      gpsDenied: "Lokalizacja jest zablokowana. Zezwól na nią dla tej strony w ustawieniach przeglądarki i odśwież.",
      gpsNone: "Ta przeglądarka nie ma dostępu do GPS.", off: "Wygląda na to, że zszedłeś z trasy ({d} m)",
      missedToast: "Minąłeś {n} przystanek/przystanki bez odsłuchania: dotknij ▶.", wakeNo: "Telefon może zablokować ekran: dotykaj go od czasu do czasu.",
      bad: "Ten link do przewodnika jest nieważny lub wygasł. Poproś Levadinho na WhatsAppie o nowy (napisz „przewodnik”).",
      away: "{d} stąd", here: "tutaj", played: "odsłuchany", missed: "pominięty, dotknij ▶",
    },
  };

  // Step-by-step help when location is blocked. A web page can't open the phone's Settings,
  // so we show the exact path for this phone and re-ask as soon as it's changed.
  const HELP = {
    en: { title: "Location is blocked for this page", retry: "Try again",
      ios: ["In Safari, tap <b>aA</b> (or the ☰ icon) in the address bar → <b>Website Settings</b> → <b>Location</b> → <b>Allow</b>.",
            "Still blocked? Open the iPhone <b>Settings</b> app → <b>Privacy &amp; Security</b> → <b>Location Services</b>: turn it on, then tap <b>Safari Websites</b> → <b>While Using the App</b>.",
            "Come back here and tap <b>Try again</b>."],
      android: ["Tap the icon left of the web address → <b>Permissions</b> (or <b>Site settings</b>) → <b>Location</b> → <b>Allow</b>.",
                "Still blocked? Pull down from the top of the screen and turn <b>Location</b> on.",
                "Come back here and tap <b>Try again</b>."],
      other: ["Allow location for this website in your browser's site settings, and make sure the phone's Location is on.",
              "Then tap <b>Try again</b>."] },
    pt: { title: "A localização está bloqueada para esta página", retry: "Tentar de novo",
      ios: ["No Safari, toque em <b>aA</b> (ou no ícone ☰) na barra de endereço → <b>Definições do site</b> → <b>Localização</b> → <b>Permitir</b>.",
            "Continua bloqueada? Abra a app <b>Definições</b> do iPhone → <b>Privacidade e segurança</b> → <b>Serviços de localização</b>: ative-os e toque em <b>Sites do Safari</b> → <b>Durante a utilização da app</b>.",
            "Volte aqui e toque em <b>Tentar de novo</b>."],
      android: ["Toque no ícone à esquerda do endereço → <b>Autorizações</b> (ou <b>Definições do site</b>) → <b>Localização</b> → <b>Permitir</b>.",
                "Continua bloqueada? Deslize a partir do topo do ecrã e ative a <b>Localização</b>.",
                "Volte aqui e toque em <b>Tentar de novo</b>."],
      other: ["Permita a localização para este site nas definições do navegador e confirme que a Localização do telemóvel está ligada.",
              "Depois toque em <b>Tentar de novo</b>."] },
    fr: { title: "La localisation est bloquée pour cette page", retry: "Réessayer",
      ios: ["Dans Safari, touchez <b>aA</b> (ou l'icône ☰) dans la barre d'adresse → <b>Réglages du site web</b> → <b>Position</b> → <b>Autoriser</b>.",
            "Toujours bloquée ? Ouvrez <b>Réglages</b> → <b>Confidentialité et sécurité</b> → <b>Service de localisation</b> : activez-le, puis <b>Sites web Safari</b> → <b>Lorsque l'app est active</b>.",
            "Revenez ici et touchez <b>Réessayer</b>."],
      android: ["Touchez l'icône à gauche de l'adresse → <b>Autorisations</b> (ou <b>Paramètres du site</b>) → <b>Position</b> → <b>Autoriser</b>.",
                "Toujours bloquée ? Balayez depuis le haut de l'écran et activez la <b>Localisation</b>.",
                "Revenez ici et touchez <b>Réessayer</b>."],
      other: ["Autorisez la localisation pour ce site dans les réglages du navigateur et vérifiez que la localisation du téléphone est activée.",
              "Puis touchez <b>Réessayer</b>."] },
    de: { title: "Standort ist für diese Seite blockiert", retry: "Erneut versuchen",
      ios: ["Tippe in Safari in der Adressleiste auf <b>aA</b> (oder ☰) → <b>Website-Einstellungen</b> → <b>Standort</b> → <b>Erlauben</b>.",
            "Immer noch blockiert? Öffne <b>Einstellungen</b> → <b>Datenschutz &amp; Sicherheit</b> → <b>Ortungsdienste</b>: einschalten, dann <b>Safari-Websites</b> → <b>Beim Verwenden der App</b>.",
            "Komm zurück und tippe auf <b>Erneut versuchen</b>."],
      android: ["Tippe auf das Symbol links neben der Adresse → <b>Berechtigungen</b> (oder <b>Website-Einstellungen</b>) → <b>Standort</b> → <b>Zulassen</b>.",
                "Immer noch blockiert? Wische von oben nach unten und schalte <b>Standort</b> ein.",
                "Komm zurück und tippe auf <b>Erneut versuchen</b>."],
      other: ["Erlaube den Standort für diese Website in den Browser-Einstellungen und prüfe, dass der Standort des Handys an ist.",
              "Dann tippe auf <b>Erneut versuchen</b>."] },
    pl: { title: "Lokalizacja jest zablokowana dla tej strony", retry: "Spróbuj ponownie",
      ios: ["W Safari dotknij <b>aA</b> (lub ☰) na pasku adresu → <b>Ustawienia witryny</b> → <b>Lokalizacja</b> → <b>Pozwalaj</b>.",
            "Nadal zablokowana? Otwórz <b>Ustawienia</b> → <b>Prywatność i ochrona</b> → <b>Usługi lokalizacji</b>: włącz je, a potem <b>Witryny Safari</b> → <b>Podczas używania aplikacji</b>.",
            "Wróć tutaj i dotknij <b>Spróbuj ponownie</b>."],
      android: ["Dotknij ikony po lewej stronie adresu → <b>Uprawnienia</b> (lub <b>Ustawienia witryny</b>) → <b>Lokalizacja</b> → <b>Zezwól</b>.",
                "Nadal zablokowana? Przesuń palcem od góry ekranu i włącz <b>Lokalizację</b>.",
                "Wróć tutaj i dotknij <b>Spróbuj ponownie</b>."],
      other: ["Zezwól na lokalizację dla tej strony w ustawieniach przeglądarki i sprawdź, czy lokalizacja telefonu jest włączona.",
              "Następnie dotknij <b>Spróbuj ponownie</b>."] },
  };
  const PLATFORM = /iPhone|iPad|iPod/.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1)
    ? "ios" : /Android/.test(navigator.userAgent) ? "android" : "other";

  const MAX_ACC = 40;        // m — worse fixes move the dot but never trigger a stop
  const NEED_FIXES = 2;      // consecutive fixes inside a stop's radius
  const WINDOW_BACK = 150, WINDOW_AHEAD = 1200;   // progress search window (m)
  const OFF_ROUTE = 60;      // m from the line
  const MISS_AFTER = 80;     // m past a stop without firing → missed

  const P = new URLSearchParams(location.search);
  const rid = P.get("r") || "", tok = P.get("t") || "", sim = P.has("sim"), debug = P.has("debug");
  const lang = UI[P.get("l")] ? P.get("l") : "en";
  const T = UI[lang], H = HELP[lang];
  const $ = (id) => document.getElementById(id);
  const fmt = (s, o) => s.replace(/\{(\w+)\}/g, (_, k) => o[k]);
  const fmtDist = (m) => m < 1000 ? `${Math.max(10, Math.round(m / 10) * 10)} m`
    : `${(m / 1000).toFixed(1).replace(".", lang === "en" ? "." : ",")} km`;
  document.documentElement.lang = lang;

  let route, audioLang, xy, cum, stops;
  let prog = 0, offCount = 0, nextIdx = 0, lastFix = null, fixes = 0;
  let lastGpsAt = 0, speed = 1.4, stepsAtFix = 0;   // 1.4 m/s: brisk walking (owner walked 1.46)
  const progHist = [];                // [time, progress] from real GPS, for walking speed
  let steps = 0, motionEvents = 0, lastMotionAt = 0, stepLen = 0.72, stepHigh = false;
  const state = {};          // stop id → "played" | "missed"
  const inside = {};         // stop id → consecutive fixes inside the radius
  const clips = {};          // stop id → blob URL
  const queue = [];
  let playing = null, wakeLock = null, watchId = null;
  const audio = new Audio();          // fallback clip player
  const keep = new Audio();           // looping silent track: keeps the audio session alive
  keep.loop = true;
  let ctx = null, curSrc = null;      // Web Audio: clips play here (not suspended in background, iOS 17.5+)
  const buffers = {};                 // stop id → decoded AudioBuffer
  const blobs = {};                   // stop id → Blob (decoded once the AudioContext exists)
  const REC = !!tok && !sim;          // lock-screen test: record to the server

  // ------------------------------------------------------------ geometry (local metres)
  let lat0, lon0, kx;
  const KY = 110574;
  const toXY = (lat, lon) => [(lon - lon0) * kx, (lat - lat0) * KY];
  const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);

  function project(p, from, to) {
    let best = null;
    for (let i = 0; i < xy.length - 1; i++) {
      if (cum[i + 1] < from || cum[i] > to) continue;
      const a = xy[i], b = xy[i + 1], dx = b[0] - a[0], dy = b[1] - a[1];
      const L2 = dx * dx + dy * dy || 1;
      const f = Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2));
      const q = [a[0] + f * dx, a[1] + f * dy], off = dist(p, q), at = cum[i] + f * (cum[i + 1] - cum[i]);
      if (!best || off < best.off - 1 || (Math.abs(off - best.off) <= 1 && Math.abs(at - prog) < Math.abs(best.at - prog))) best = { at, off };
    }
    return best;
  }

  // ------------------------------------------------------------ load
  async function load() {
    try {
      const r = await fetch(`r/${encodeURIComponent(rid)}/route.json?t=${encodeURIComponent(tok)}`, { cache: "no-cache" });
      if (!r.ok) throw new Error(r.status);
      route = await r.json();
    } catch (e) {
      $("title").textContent = "Levadinho";
      $("how").textContent = T.bad;
      $("startBtn").classList.add("hidden");
      return;
    }
    audioLang = route.langs.includes(lang) ? lang : (route.langs.includes("en") ? "en" : route.langs[0]);
    stops = route.stops;
    [lat0, lon0] = route.line[0];
    kx = 111320 * Math.cos(lat0 * Math.PI / 180);
    xy = route.line.map(([a, b]) => toXY(a, b));
    cum = [0];
    for (let i = 1; i < xy.length; i++) cum.push(cum[i - 1] + dist(xy[i - 1], xy[i]));
    stops.forEach((s) => { s.xy = toXY(s.lat, s.lon); });
    document.title = `${route.title[lang] || route.title.en} · Levadinho`;
    $("title").textContent = route.title[lang] || route.title.en;
    $("meta").textContent = fmt(T.stops, { n: stops.length, km: (route.length_m / 1000).toFixed(1).replace(".", lang === "en" ? "." : ",") });
    $("how").textContent = T.how;
    $("startBtn").textContent = T.start;
    $("walkBtn").textContent = T.walk;
    $("walkX").textContent = T.walkExit;
    $("pocketHint").textContent = T.pocketHint;
    $("introWarn").textContent = T.pocketHint;
    $("walkWarn").textContent = T.noLock;
    $("walkK").textContent = T.next;
    drawMap();
    renderStops();
    preloadAudio();
    if (!sim) downloadPack();
  }

  async function preloadAudio() {
    for (const s of stops) {
      const rel = s.audio && s.audio[audioLang];
      if (!rel) continue;
      try {
        const r = await fetch(`r/${encodeURIComponent(rid)}/${rel}?t=${encodeURIComponent(tok)}`);
        if (r.ok) { blobs[s.id] = await r.blob(); clips[s.id] = URL.createObjectURL(blobs[s.id]); if (ctx) decode(s.id); }
      } catch (e) { /* the ▶ button retries by URL */ }
    }
  }

  // ------------------------------------------------------------ offline pack
  const CACHE = "levadinho-guide-v1";
  async function downloadPack() {
    const box = $("offline");
    if (!("caches" in window)) return;
    const q = `?t=${encodeURIComponent(tok)}`;
    const urls = [`r/${encodeURIComponent(rid)}/route.json${q}`]
      .concat(stops.filter((s) => s.audio && s.audio[audioLang]).map((s) => `r/${encodeURIComponent(rid)}/${s.audio[audioLang]}${q}`));
    const shell = [location.pathname, "guide.js"];
    box.classList.remove("hidden", "bad");
    let n = 0, bytes = 0, failed = 0;
    const show = () => { box.textContent = fmt(T.offDl, { n, N: urls.length }); };
    show();
    const c = await caches.open(CACHE);
    for (const u of shell) { try { const r = await fetch(u, { cache: "no-cache" }); if (r.ok) await c.put(new URL(u, location.href).href.split("?")[0], r); } catch (e) { failed++; } }
    for (const u of urls) {
      try {
        let r = await c.match(u);
        if (!r) { r = await fetch(u); if (!r.ok) throw new Error(r.status); await c.put(u, r.clone()); }
        bytes += (await r.blob()).size;
      } catch (e) { failed++; }
      n++; show();
    }
    if (failed) { box.textContent = T.offFail; box.classList.add("bad"); log("offline_fail", { failed }); return; }
    box.textContent = fmt(T.offOk, { mb: (bytes / 1048576).toFixed(1).replace(".", lang === "en" ? "." : ",") });
    try { if (navigator.storage && navigator.storage.persist) log("offline_ok", { bytes, persist: await navigator.storage.persist() }); } catch (e) { log("offline_ok", { bytes }); }
  }

  async function decode(id) {
    try { buffers[id] = await ctx.decodeAudioData(await blobs[id].arrayBuffer()); }
    catch (e) { log("decode_fail", { id, err: String(e) }); }
  }

  // ------------------------------------------------------------ server log (lock-screen test)
  const OUTBOX_KEY = `levadinho-outbox-${rid}-${tok}`;
  const outbox = (() => { try { return JSON.parse(localStorage.getItem(OUTBOX_KEY)) || []; } catch (e) { return []; } })();
  const saveOutbox = () => { try { localStorage.setItem(OUTBOX_KEY, JSON.stringify(outbox.slice(-5000))); } catch (e) {} };
  let flushing = false;
  function log(ev, data) {
    if (!REC) return;
    outbox.push(Object.assign({ ev, t: Date.now(), vis: document.visibilityState, online: navigator.onLine }, data || {}));
    saveOutbox();
    flush();
  }
  async function flush() {
    if (flushing || !outbox.length) return;
    flushing = true;
    const batch = outbox.splice(0, 50);
    try {
      const r = await fetch(`log?r=${encodeURIComponent(rid)}&t=${encodeURIComponent(tok)}`,
        { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(batch), keepalive: true });
      if (!r.ok) throw new Error(r.status);
    } catch (e) { outbox.unshift(...batch); }
    saveOutbox();
    flushing = false;
    if (outbox.length) setTimeout(flush, 3000);
  }
  setInterval(() => {
    if (!started) return;
    log("hb", { ctx: ctx && ctx.state, keep: keep.paused ? "paused" : "playing", fixes, motionEvents, steps, speed: +speed.toFixed(2),
                wake: !!(wakeLock && !wakeLock.released), pocket: $("walk").classList.contains("on") });
    motionEvents = 0;
    // (1) GPS silent → ask for a one-off position
    if (!sim && Date.now() - lastGpsAt > 8000 && navigator.geolocation) {
      const asked = Date.now();
      navigator.geolocation.getCurrentPosition(
        (p) => { log("poll_fix", { lat: +p.coords.latitude.toFixed(6), lon: +p.coords.longitude.toFixed(6), acc: Math.round(p.coords.accuracy), ms: Date.now() - asked }); onFix(p.coords.latitude, p.coords.longitude, p.coords.accuracy); },
        (e) => log("poll_err", { code: e.code, ms: Date.now() - asked }),
        { enableHighAccuracy: true, maximumAge: 0, timeout: 8000 });
    }
  }, 10000);

  // (2) Dead reckoning while GPS is silent: estimate progress along the one-way route and
  // play the next stop when the estimate reaches it.
  setInterval(() => {
    if (!started || sim || !lastGpsAt || Date.now() - lastGpsAt < 8000) return;
    const motionAlive = Date.now() - lastMotionAt < 5000;
    const walked = motionAlive ? (steps - stepsAtFix) * stepLen : speed * (Date.now() - lastGpsAt) / 1000;
    const est = prog + Math.min(walked, 800);
    const s = stops[nextIdx];
    if (s && !state[s.id] && est >= s.at_m - 15) {
      log("stop_fired_dr", { id: s.id, est: Math.round(est), via: motionAlive ? "steps" : "time", speed: +speed.toFixed(2), stepLen: +stepLen.toFixed(2), secs: Math.round((Date.now() - lastGpsAt) / 1000) });
      fire(nextIdx);
      while (nextIdx < stops.length && state[stops[nextIdx].id]) nextIdx++;
    }
  }, 2000);

  // (3) Motion sensor: count events and steps (peaks in acceleration magnitude)
  function onMotion(e) {
    const a = e.accelerationIncludingGravity;
    if (!a || a.x === null) return;
    motionEvents++; lastMotionAt = Date.now();
    const m = Math.hypot(a.x, a.y, a.z);
    if (!stepHigh && m > 11.2) { stepHigh = true; steps++; }
    else if (stepHigh && m < 9.8) stepHigh = false;
  }
  document.addEventListener("visibilitychange", () => { if (started) log("vis"); });

  // ------------------------------------------------------------ start (the tap that unlocks audio)
  let started = false;
  function silentWav() {
    const n = 8000, buf = new ArrayBuffer(44 + n * 2), v = new DataView(buf);
    const w = (o, s) => [...s].forEach((c, i) => v.setUint8(o + i, c.charCodeAt(0)));
    w(0, "RIFF"); v.setUint32(4, 36 + n * 2, true); w(8, "WAVE"); w(12, "fmt ");
    v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
    v.setUint32(24, 8000, true); v.setUint32(28, 16000, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true);
    w(36, "data"); v.setUint32(40, n * 2, true);
    return URL.createObjectURL(new Blob([buf], { type: "audio/wav" }));
  }

  async function start() {
    // Everything audio happens before the first await, inside the tap (iOS requires it).
    try { if (navigator.audioSession) navigator.audioSession.type = "playback"; } catch (e) {}
    try {                                          // motion permission must be asked inside the tap
      if (window.DeviceMotionEvent && DeviceMotionEvent.requestPermission) {
        DeviceMotionEvent.requestPermission().then((r) => { log("motion_perm", { r }); if (r === "granted") addEventListener("devicemotion", onMotion); })
          .catch((e) => log("motion_perm", { r: "error", err: String(e) }));
      } else if (window.DeviceMotionEvent) addEventListener("devicemotion", onMotion);
    } catch (e) {}
    keep.src = silentWav();
    keep.play().catch((e) => log("keep_fail", { err: String(e) }));
    try {
      ctx = new (window.AudioContext || window.webkitAudioContext)();
      ctx.resume();
      Object.keys(blobs).forEach(decode);
    } catch (e) { ctx = null; }
    audio.src = silentWav();
    audio.play().catch(() => {});
    started = true;
    log("start", { ua: navigator.userAgent, audioSession: !!navigator.audioSession, ctx: ctx && ctx.state, lang, audioLang });
    if (REC) $("testCard").classList.remove("hidden");
    $("intro").classList.add("hidden");
    $("guide").classList.remove("hidden");
    if (debug) $("dbg").style.display = "block";
    await keepAwake();
    setGps(T.gpsWait);
    if (sim) return simulate();
    if (!("geolocation" in navigator)) return setGps(T.gpsNone, true);
    watchGps();
  }

  function watchGps() {
    if (watchId !== null) navigator.geolocation.clearWatch(watchId);
    watchId = navigator.geolocation.watchPosition(
      (p) => {
        showHelp(false);
        const c = p.coords, r1 = (x) => (x === null || x === undefined || isNaN(x) ? null : Math.round(x * 10) / 10);
        log("fix", { lat: +c.latitude.toFixed(6), lon: +c.longitude.toFixed(6), acc: Math.round(c.accuracy), gt: p.timestamp,
                     alt: r1(c.altitude), altAcc: r1(c.altitudeAccuracy), speed: r1(c.speed), heading: r1(c.heading) });
        onFix(p.coords.latitude, p.coords.longitude, p.coords.accuracy);
      },
      (e) => {
        log("gps_err", { code: e.code });
        if (e.code === 1) { setGps(T.gpsDenied, true); showHelp(true); }
        else setGps(T.gpsWait);
      },
      { enableHighAccuracy: true, maximumAge: 0, timeout: 30000 });
  }

  // ------------------------------------------------------------ blocked-location help
  function showHelp(on) {
    const box = $("locHelp");
    if (!on) { box.classList.add("hidden"); return; }
    $("helpTitle").textContent = H.title;
    $("helpSteps").innerHTML = H[PLATFORM].map((x) => `<li>${x}</li>`).join("");
    $("helpRetry").textContent = H.retry;
    box.classList.remove("hidden");
    box.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  const guideOn = () => !$("guide").classList.contains("hidden");

  // "Try again" is a tap, so it may start the guide (audio can only be unlocked by a tap).
  function retryLocation() {
    showHelp(false);
    if (guideOn()) { setGps(T.gpsWait); watchGps(); } else start();
  }

  // No tap (permission changed, or back from Settings): re-check quietly, never start the guide.
  async function recheck() {
    if (guideOn()) { setGps(T.gpsWait); return watchGps(); }
    try {
      const st = await navigator.permissions.query({ name: "geolocation" });
      showHelp(st.state === "denied");
    } catch (e) { showHelp(false); }
  }

  // Check before the Start tap, so a blocked phone sees the fix straight away; and pick up the
  // change as soon as the visitor comes back from Settings.
  async function checkPermission() {
    try {
      const st = await navigator.permissions.query({ name: "geolocation" });
      if (st.state === "denied") showHelp(true);
      st.onchange = () => recheck();
    } catch (e) { /* no Permissions API: we find out on the first fix */ }
  }

  async function keepAwake() {
    if (wakeLock && !wakeLock.released) return;
    try {
      wakeLock = await navigator.wakeLock.request("screen");
      log("wake_on");
      wakeLock.addEventListener("release", () => log("wake_off"));
    } catch (e) {
      wakeLock = null;
      log("wake_fail", { err: String(e) });
      if (!sim) toast(T.wakeNo);
    }
  }

  // ------------------------------------------------------------ pocket mode
  // Black screen that keeps the phone awake (so GPS keeps flowing) and ignores touches;
  // leave it with a deliberate 2-second press-and-hold.
  let holdTimer = null;
  function pocketOn() {
    keepAwake();
    $("walk").classList.add("on");
    document.documentElement.style.overflow = "hidden";
    updateWalk();
    log("pocket_on");
  }
  function pocketOff() {
    $("walk").classList.remove("on", "holding");
    document.documentElement.style.overflow = "";
    log("pocket_off");
  }
  function holdStart(e) {
    e.preventDefault();
    $("walk").classList.add("holding");
    clearTimeout(holdTimer);
    holdTimer = setTimeout(pocketOff, 2000);
  }
  function holdEnd(e) {
    e.preventDefault();
    $("walk").classList.remove("holding");
    clearTimeout(holdTimer);
  }

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState !== "visible" || !route) return;
    if (!$("guide").classList.contains("hidden")) keepAwake();
    if (!$("locHelp").classList.contains("hidden")) recheck();   // back from Settings
  });

  // ------------------------------------------------------------ GPS
  function onFix(lat, lon, acc) {
    fixes++;
    const p = toXY(lat, lon);
    lastFix = { p, acc, at: Date.now() };
    let pr = project(p, prog - WINDOW_BACK, prog + WINDOW_AHEAD);
    if (!pr || pr.off > OFF_ROUTE) {
      offCount++;
      if (offCount >= 3) {           // lost: look over the whole route
        const g = project(p, -1, Infinity);
        if (g && g.off <= OFF_ROUTE) { pr = g; offCount = 0; }
      }
    } else offCount = 0;
    const onRoute = pr && pr.off <= OFF_ROUTE;
    if (onRoute && acc <= MAX_ACC) {                // walking speed from the last ~30 s of real GPS
      const now = Date.now();
      progHist.push([now, pr.at]);
      while (progHist.length > 2 && now - progHist[0][0] > 30000) progHist.shift();
      const [t0, p0] = progHist[0], dt = (now - t0) / 1000;
      if (dt >= 10) speed = Math.min(1.8, Math.max(0.8, (pr.at - p0) / dt));
      if (steps - stepsAtFix > 10 && pr.at > prog) stepLen = Math.min(0.95, Math.max(0.5, (pr.at - prog) / (steps - stepsAtFix)));
      lastGpsAt = now; stepsAtFix = steps;
    }
    if (onRoute) prog = Math.max(prog - WINDOW_BACK, pr.at);

    if (acc > MAX_ACC) setGps(fmt(T.gpsWeak, { a: Math.round(acc) }), true);
    else if (!onRoute && pr) setGps(fmt(T.off, { d: Math.round(pr.off) }), true);
    else setGps(fmt(T.gpsOk, { a: Math.round(acc) }));

    if (acc <= MAX_ACC) checkStops(p, onRoute);
    drawMe();
    renderStops();
    if (debug) $("dbg").textContent =
      `fix ${fixes}  ${lat.toFixed(6)}, ${lon.toFixed(6)}  ±${Math.round(acc)} m\n` +
      `progress ${Math.round(prog)} / ${Math.round(cum[cum.length - 1])} m  off ${pr ? Math.round(pr.off) : "-"} m  next #${nextIdx + 1}`;
  }

  // A phone standing still may stop sending fixes: re-check the last good one so a stop
  // reached with a single fix still fires.
  setInterval(() => {
    if (lastFix && lastFix.acc <= MAX_ACC && Date.now() - lastFix.at < 15000) { checkStops(lastFix.p, offCount === 0); drawMe(); renderStops(); }
  }, 4000);

  function checkStops(p, onRoute) {
    let newlyMissed = 0;
    stops.forEach((s, i) => {
      if (state[s.id]) return;
      const near = dist(p, s.xy) <= s.radius + 10 && s.at_m <= prog + WINDOW_BACK;
      inside[s.id] = near ? (inside[s.id] || 0) + 1 : 0;
      if (inside[s.id] >= NEED_FIXES) fire(i);
      else if (onRoute && prog > s.at_m + MISS_AFTER && i < stops.length - 1) { state[s.id] = "missed"; newlyMissed++; log("stop_missed", { id: s.id, prog: Math.round(prog) }); }
    });
    if (newlyMissed) toast(fmt(T.missedToast, { n: newlyMissed }));
    while (nextIdx < stops.length && state[stops[nextIdx].id]) nextIdx++;
  }

  function fire(i) {
    const s = stops[i];
    state[s.id] = "played";
    for (let j = 0; j < i; j++) if (!state[stops[j].id]) state[stops[j].id] = "missed";
    log("stop_fired", { id: s.id, prog: Math.round(prog) });
    enqueue(s);
  }

  // ------------------------------------------------------------ audio
  function enqueue(s) {
    queue.push(s);
    if (!playing) playNext();
  }

  function playNext() {
    const s = queue.shift();
    if (!s) { playing = null; showNow(null); return; }
    playing = s;
    showNow(s);
    if (ctx && buffers[s.id]) {                    // Web Audio path (works in background on iOS 17.5+)
      try {
        if (ctx.state !== "running") ctx.resume();
        const src = ctx.createBufferSource();
        src.buffer = buffers[s.id];
        src.connect(ctx.destination);
        src.onended = () => { log("clip_end", { id: s.id }); if (curSrc === src) { curSrc = null; if (playing === s) playNext(); } };
        curSrc = src;
        src.start();
        log("clip_play", { id: s.id, via: "webaudio", ctx: ctx.state });
        return;
      } catch (e) { log("clip_fail", { id: s.id, via: "webaudio", err: String(e) }); }
    }
    const src = clips[s.id] || (s.audio && s.audio[audioLang] ? `r/${encodeURIComponent(rid)}/${s.audio[audioLang]}?t=${encodeURIComponent(tok)}` : null);
    if (!src) return setTimeout(playNext, 4000);   // no clip: show the text for a moment
    audio.src = src;
    audio.play().then(() => log("clip_play", { id: s.id, via: "element" }))
      .catch((e) => { log("clip_fail", { id: s.id, via: "element", err: String(e) }); setTimeout(playNext, 4000); });
  }
  audio.addEventListener("ended", () => { if (playing) playNext(); });

  function playNow(i) {
    queue.length = 0;
    audio.pause();
    if (curSrc) { const c = curSrc; curSrc = null; try { c.stop(); } catch (e) {} }
    log("manual_play", { id: stops[i].id });
    if (!state[stops[i].id] || state[stops[i].id] === "missed") state[stops[i].id] = "played";
    playing = null;
    enqueue(stops[i]);
    renderStops();
  }

  function showNow(s) {
    const box = $("now");
    const w = $("walk");
    if (s) {
      box.classList.add("on");
      $("nowLbl").textContent = T.nowPlaying;
      $("nowName").textContent = `${s.n}. ${s.name[lang] || s.name[audioLang] || s.name.en}`;
      $("nowText").textContent = s.text[lang] || s.text[audioLang] || "";
      w.classList.add("playing");
    } else {
      $("nowLbl").textContent = T.lastPlayed;
      w.classList.remove("playing");
    }
    updateWalk();
  }

  // ------------------------------------------------------------ rendering
  const SVG = "http://www.w3.org/2000/svg";
  let meDot, meAcc, donePath;

  function el(tag, attrs, parent) {
    const e = document.createElementNS(SVG, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }

  function drawMap() {
    const svg = $("map");
    const xs = xy.map((p) => p[0]), ys = xy.map((p) => -p[1]);
    const pad = 60, minX = Math.min(...xs) - pad, minY = Math.min(...ys) - pad;
    const w = Math.max(...xs) + pad - minX, h = Math.max(...ys) + pad - minY;
    svg.setAttribute("viewBox", `${minX} ${minY} ${w} ${h}`);
    svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
    const u = Math.max(w, h) / 320;            // one "screen pixel" in metres, roughly
    svg.dataset.u = u;
    const pts = xy.map((p) => `${p[0].toFixed(1)},${(-p[1]).toFixed(1)}`).join(" ");
    el("polyline", { points: pts, fill: "none", stroke: "#BE3A2B", "stroke-width": 3 * u, "stroke-linejoin": "round", "stroke-linecap": "round", opacity: .55 }, svg);
    donePath = el("polyline", { points: "", fill: "none", stroke: "#1E7A45", "stroke-width": 4 * u, "stroke-linejoin": "round", "stroke-linecap": "round" }, svg);
    stops.forEach((s) => {
      const g = el("g", { "data-stop": s.id }, svg);
      el("circle", { cx: s.xy[0], cy: -s.xy[1], r: 8 * u, fill: "#fff", stroke: "#16342A", "stroke-width": 2 * u }, g);
      const t = el("text", { x: s.xy[0], y: -s.xy[1] + 3.5 * u, "text-anchor": "middle", "font-size": 10 * u, "font-weight": 700, fill: "#16342A" }, g);
      t.textContent = s.n;
    });
    meAcc = el("circle", { r: 0, fill: "#2B6CB0", opacity: .15 }, svg);
    meDot = el("circle", { r: 7 * u, fill: "#2B6CB0", stroke: "#fff", "stroke-width": 2.5 * u, display: "none" }, svg);
  }

  function drawMe() {
    if (!lastFix) return;
    const [x, y] = lastFix.p;
    meDot.setAttribute("display", "inline");
    meDot.setAttribute("cx", x); meDot.setAttribute("cy", -y);
    meAcc.setAttribute("cx", x); meAcc.setAttribute("cy", -y); meAcc.setAttribute("r", lastFix.acc);
    const done = [];
    for (let i = 0; i < xy.length && cum[i] <= prog; i++) done.push(`${xy[i][0].toFixed(1)},${(-xy[i][1]).toFixed(1)}`);
    donePath.setAttribute("points", done.join(" "));
    stops.forEach((s) => {
      const c = document.querySelector(`[data-stop="${s.id}"] circle`);
      const st = state[s.id];
      c.setAttribute("fill", st === "played" ? "#1E7A45" : st === "missed" ? "#C07A0A" : s === stops[nextIdx] ? "#E8B71A" : "#fff");
    });
  }

  function renderStops() {
    const ol = $("stops");
    ol.innerHTML = "";
    stops.forEach((s, i) => {
      const li = document.createElement("li");
      const st = state[s.id];
      li.className = st || (i === nextIdx ? "next" : "");
      let sub = "";
      if (st === "played") sub = T.played;
      else if (st === "missed") sub = T.missed;
      else if (lastFix) { const d = s.at_m - prog; sub = d <= s.radius ? T.here : fmt(T.away, { d: fmtDist(Math.max(0, d)) }); }
      li.innerHTML = `<span class="num">${s.n}</span><span class="sname"><b></b><small></small></span><button class="play" aria-label="Play">▶</button>`;
      li.querySelector("b").textContent = s.name[lang] || s.name[audioLang] || s.name.en;
      li.querySelector("small").textContent = sub;
      li.querySelector("button").addEventListener("click", () => playNow(i));
      ol.appendChild(li);
    });
    updateWalk();
  }

  function updateWalk() {
    if (!stops) return;
    if (playing) {
      $("walkK").textContent = T.nowPlaying;
      $("walkN").textContent = playing.name[lang] || playing.name[audioLang] || playing.name.en;
      $("walkD").textContent = "🔊";
      return;
    }
    const s = stops[nextIdx];
    $("walkK").textContent = s ? T.next : "";
    $("walkN").textContent = s ? (s.name[lang] || s.name[audioLang] || s.name.en) : T.finished;
    $("walkD").textContent = s && lastFix ? fmtDist(Math.max(0, s.at_m - prog)) : "";
  }

  function setGps(msg, warn) {
    const g = $("gps");
    g.textContent = msg;
    g.classList.toggle("warn", !!warn);
  }

  let toastTimer;
  function toast(msg) {
    const t = $("toast");
    t.textContent = msg;
    t.classList.add("on");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove("on"), 6000);
  }

  // ------------------------------------------------------------ simulated walk
  function simulate() {
    const speed = 1.4 * (parseFloat(P.get("speed")) || 8);   // m/s
    let at = 0;
    const step = () => {
      if (at > cum[cum.length - 1]) return;
      let i = 1;
      while (i < cum.length - 1 && cum[i] < at) i++;
      const f = (at - cum[i - 1]) / ((cum[i] - cum[i - 1]) || 1);
      const x = xy[i - 1][0] + f * (xy[i][0] - xy[i - 1][0]) + (Math.random() - .5) * 8;
      const y = xy[i - 1][1] + f * (xy[i][1] - xy[i - 1][1]) + (Math.random() - .5) * 8;
      onFix(lat0 + y / KY, lon0 + x / kx, 6 + Math.random() * 6);
      at += speed;
      setTimeout(step, parseInt(P.get("tick"), 10) || 1000);
    };
    step();
  }

  // ------------------------------------------------------------ wiring
  $("startBtn").addEventListener("click", start);
  $("helpRetry").addEventListener("click", retryLocation);
  $("offline").addEventListener("click", () => { if ($("offline").classList.contains("bad")) downloadPack(); });
  addEventListener("online", () => flush());
  if ("serviceWorker" in navigator && !sim) navigator.serviceWorker.register("sw.js").catch(() => {});
  $("walkBtn").addEventListener("click", pocketOn);
  const W = $("walk");
  ["touchstart", "mousedown"].forEach((ev) => W.addEventListener(ev, holdStart, { passive: false }));
  ["touchend", "touchcancel", "mouseup", "mouseleave"].forEach((ev) => W.addEventListener(ev, holdEnd, { passive: false }));
  ["touchmove", "click", "dblclick", "contextmenu", "gesturestart"].forEach((ev) => W.addEventListener(ev, (e) => e.preventDefault(), { passive: false }));
  load().then(() => {
    if (!route) return;
    if (sim && P.has("auto")) start();
    else if (!sim) checkPermission();
  });
})();
