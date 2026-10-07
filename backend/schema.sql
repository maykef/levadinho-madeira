-- Levadinho knowledge store (schema "kb") in the levadinho-db PostGIS container.
-- Applied by `python backend/load.py init` (idempotent). Kept apart from the visitor analytics in "public":
-- the MCP server connects as kb_reader, which can read kb and nothing else.
--
-- Every record carries source_id + checked_at: the bot cites the source, the site shows it (never the date:
-- owner rule, no visible dates). Loaders replace their own rows on each run (see load.py); nothing here is
-- edited by hand.

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE SCHEMA IF NOT EXISTS kb;
COMMENT ON SCHEMA kb IS 'Levadinho knowledge store: sourced facts about Madeira trails, fees, transport, weather and places. Read by the MCP server, the bot and the site generators. No visitor data.';

-- ------------------------------------------------------------------ sources
CREATE TABLE IF NOT EXISTS kb.source (
  id         text PRIMARY KEY,
  name       text NOT NULL,
  publisher  text,
  url        text,
  licence    text,
  kind       text NOT NULL CHECK (kind IN ('official', 'curated', 'site'))
);
COMMENT ON TABLE kb.source IS 'Where a record comes from. official = a public body (IFCN, IPMA, SIMplifica, Visit Madeira, the law, a bus operator); curated = Levadinho''s verified research notes; site = a levadinho-madeira.com page.';

-- ------------------------------------------------------------------ trails
CREATE TABLE IF NOT EXISTS kb.trail (
  code          text PRIMARY KEY,
  name          text NOT NULL,
  region        text,
  route_type    text,
  start_name    text,
  end_name      text,
  distance_km   numeric(5,2),
  distance_txt  text,
  duration      text,
  difficulty    text,
  alt_min_m     integer,
  alt_max_m     integer,
  fee_eur       numeric(6,2),
  tunnels       boolean,
  torch         boolean,
  exposure      text,
  extras        jsonb,
  trailhead     geography(Point, 4326),
  page_url      text,
  official_url  text,
  source_id     text NOT NULL REFERENCES kb.source(id),
  checked_at    timestamptz NOT NULL
);
COMMENT ON TABLE kb.trail IS 'Static facts per official PR trail (Visit Madeira page + IFCN panels). Status lives in kb.trail_status.';
COMMENT ON COLUMN kb.trail.region IS 'summit | north | west | east | south: the IPMA station region used for weather.';
COMMENT ON COLUMN kb.trail.fee_eur IS 'Fee walking on your own (SIMplifica). NULL = no IFCN fee (e.g. PR3, PR3.1, PR4, run by Funchal council).';
COMMENT ON COLUMN kb.trail.tunnels IS 'true = has tunnels per the IFCN panel; NULL = no sourced data (never means "no tunnel").';
COMMENT ON COLUMN kb.trail.exposure IS 'Vertigo/exposure wording from the IFCN panel; NULL = no sourced data.';
COMMENT ON COLUMN kb.trail.trailhead IS 'Start point (WGS84) from the official Visit Madeira page.';
CREATE INDEX IF NOT EXISTS trail_name_trgm ON kb.trail USING gin (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS trail_geom ON kb.trail USING gist (trailhead);

CREATE TABLE IF NOT EXISTS kb.trail_status (
  code            text PRIMARY KEY REFERENCES kb.trail(code),
  status          text NOT NULL CHECK (status IN ('OPEN', 'PARTIAL', 'CLOSED')),
  note            jsonb,
  source_id       text NOT NULL REFERENCES kb.source(id),
  source_updated  text,
  checked_at      timestamptz NOT NULL
);
COMMENT ON TABLE kb.trail_status IS 'Today''s status per trail from the official IFCN warnings list (via status.json, refreshed daily).';
COMMENT ON COLUMN kb.trail_status.note IS 'IFCN''s note: {"pt": original, "en"/"fr"/"de"/"pl": machine translations}. NULL = no note.';
COMMENT ON COLUMN kb.trail_status.source_updated IS 'IFCN''s own "ATUALIZADO" date as printed. Data only: never shown to visitors.';

CREATE TABLE IF NOT EXISTS kb.status_day (
  day     date NOT NULL,
  code    text NOT NULL,
  status  text NOT NULL,
  source  text NOT NULL,
  PRIMARY KEY (day, code)
);
COMMENT ON TABLE kb.status_day IS 'Daily status history per trail (history/status-daily.jsonl; source IFCN, or Visit Madeira before 2026-09-30).';

-- ------------------------------------------------------------------ fees, rules, facts
CREATE TABLE IF NOT EXISTS kb.fee (
  item        text PRIMARY KEY,
  amount_eur  numeric(7,2),
  label       jsonb NOT NULL,
  applies_to  text,
  conditions  jsonb,
  source_id   text NOT NULL REFERENCES kb.source(id),
  checked_at  timestamptz NOT NULL
);
COMMENT ON TABLE kb.fee IS 'Exact amounts (trail fees, multi-day rates, fines, bus fares). Prices only come from here.';
COMMENT ON COLUMN kb.fee.amount_eur IS 'The amount; for a range (fines) the minimum, the maximum in conditions.max_eur.';
COMMENT ON COLUMN kb.fee.label IS 'What it is, per language, e.g. {"en": "PR1 full route, on your own"}.';

CREATE TABLE IF NOT EXISTS kb.fact (
  id          text PRIMARY KEY,
  topic       text NOT NULL,
  subject     text,
  text        jsonb NOT NULL,
  confirmed   boolean NOT NULL DEFAULT true,
  source_id   text NOT NULL REFERENCES kb.source(id),
  checked_at  timestamptz NOT NULL
);
COMMENT ON TABLE kb.fact IS 'One sourced statement (a bullet of a curated facts file, a bus note). confirmed=false rows are things NOT officially confirmed: the tools never return them as facts.';
COMMENT ON COLUMN kb.fact.topic IS 'trail, closures, one_way, transport, fees_booking, sold_out, refunds, sunrise, safety, bus, taxi, transfer…';
COMMENT ON COLUMN kb.fact.subject IS 'Trail code the fact is about (e.g. PR1), or NULL when general.';
CREATE INDEX IF NOT EXISTS fact_topic ON kb.fact (topic, subject);

CREATE TABLE IF NOT EXISTS kb.doc (
  id          text PRIMARY KEY,
  kind        text NOT NULL CHECK (kind IN ('facts', 'page')),
  subject     text,
  lang        text NOT NULL,
  title       text NOT NULL,
  url         text,
  body        text NOT NULL,
  cfg         regconfig NOT NULL,
  tsv         tsvector GENERATED ALWAYS AS (setweight(to_tsvector(cfg, title), 'A') || to_tsvector(cfg, body)) STORED,
  source_id   text NOT NULL REFERENCES kb.source(id),
  checked_at  timestamptz NOT NULL
);
COMMENT ON TABLE kb.doc IS 'Text chunks for full-text search: curated facts sections and site page sections.';
COMMENT ON COLUMN kb.doc.cfg IS 'Text-search configuration for lang (english, portuguese, french, german; simple for Polish).';
CREATE INDEX IF NOT EXISTS doc_tsv ON kb.doc USING gin (tsv);

-- ------------------------------------------------------------------ transport
CREATE TABLE IF NOT EXISTS kb.bus_trip (
  id          serial PRIMARY KEY,
  operator    text NOT NULL,
  line        text NOT NULL,
  new_line    text,
  from_stop   text NOT NULL,
  to_stop     text NOT NULL,
  dep         time NOT NULL,
  arr         time,
  days        text NOT NULL CHECK (days IN ('daily', 'mon_fri', 'sat', 'sun_hol', 'sat_sun', 'sat_sun_hol')),
  marks       text[] NOT NULL DEFAULT '{}',
  change_at   text,
  trail_code  text,
  leg         text CHECK (leg IN ('there', 'back')),
  valid_from  date,
  valid_to    date,
  source_id   text NOT NULL REFERENCES kb.source(id),
  checked_at  timestamptz NOT NULL
);
COMMENT ON TABLE kb.bus_trip IS 'One printed bus trip. Curated from the operators'' sheets on SIGA (scripts/gen_bus.py) and Horários do Funchal; every printed trip, no guessed times.';
COMMENT ON COLUMN kb.bus_trip.arr IS 'Arrival at to_stop; NULL when the sheet prints departures only.';
COMMENT ON COLUMN kb.bus_trip.marks IS 'T = change bus (at change_at); PE = school term only; PNE = school holidays only.';
COMMENT ON COLUMN kb.bus_trip.days IS 'sun_hol = Sundays and public holidays. No buses on 25 December.';
COMMENT ON COLUMN kb.bus_trip.valid_from IS 'Seasonal timetables (e.g. winter 25 Oct–27 Mar); NULL = all year.';
CREATE INDEX IF NOT EXISTS bus_trail ON kb.bus_trip (trail_code, leg);

CREATE TABLE IF NOT EXISTS kb.transport (
  id          text PRIMARY KEY,
  kind        text NOT NULL CHECK (kind IN ('taxi', 'taxi_island', 'booking')),
  town        text,
  name        text NOT NULL,
  phone       text[],
  url         text,
  trails      text[],
  source_id   text NOT NULL REFERENCES kb.source(id),
  checked_at  timestamptz NOT NULL
);
COMMENT ON TABLE kb.transport IS 'Taxi ranks and contacts as printed by official sources (IFCN panels, Visit Madeira). No prices, no private transfer companies (owner rule).';
COMMENT ON COLUMN kb.transport.trails IS 'Trails whose IFCN panel prints this rank.';

-- ------------------------------------------------------------------ weather
CREATE TABLE IF NOT EXISTS kb.weather_obs (
  region       text NOT NULL,
  place        text NOT NULL,
  observed_at  timestamptz NOT NULL,
  temp_c       numeric(4,1),
  wind_kmh     numeric(5,1),
  rain_mm      numeric(5,1),
  humidity     integer,
  in_cloud     boolean,
  source_id    text NOT NULL REFERENCES kb.source(id),
  PRIMARY KEY (region, observed_at)
);
COMMENT ON TABLE kb.weather_obs IS 'Measured IPMA station readings (the summit station and five regional ones), as read by the daily updater.';

CREATE TABLE IF NOT EXISTS kb.forecast (
  spot         text NOT NULL,
  run_date     date NOT NULL,
  lat          double precision,
  lon          double precision,
  elevation_m  integer,
  hourly       jsonb NOT NULL,
  source_id    text NOT NULL REFERENCES kb.source(id),
  PRIMARY KEY (spot, run_date)
);
COMMENT ON TABLE kb.forecast IS 'Multi-model hourly forecasts for summit spots (Open-Meteo, saved daily by the fog test in reports/camtest/forecasts/). Uncalibrated: a guide, not a promise.';

-- ------------------------------------------------------------------ places and notices (filled by the Funchal work)
CREATE TABLE IF NOT EXISTS kb.place (
  id             text PRIMARY KEY,
  name           text NOT NULL,
  category       text[] NOT NULL,
  neighbourhood  text,
  municipality   text,
  geom           geography(Point, 4326),
  hours          jsonb,
  price          jsonb,
  phone          text,
  website        text,
  description    jsonb,
  source_id      text NOT NULL REFERENCES kb.source(id),
  checked_at     timestamptz NOT NULL
);
COMMENT ON TABLE kb.place IS 'A place in Funchal / on the island (viewpoint, sea_pool, museum, cable_car, poncha, bolo_de_mel, garden, landmark, restaurant_street…).';
COMMENT ON COLUMN kb.place.description IS 'Short factual description per language {"en": …, "pt": …, …}.';
CREATE INDEX IF NOT EXISTS place_geom ON kb.place USING gist (geom);
CREATE INDEX IF NOT EXISTS place_cat ON kb.place USING gin (category);

CREATE TABLE IF NOT EXISTS kb.notice (
  id          text PRIMARY KEY,
  subject     text NOT NULL,
  kind        text NOT NULL CHECK (kind IN ('closure', 'restriction', 'works', 'event', 'cruise')),
  starts      timestamptz,
  ends        timestamptz,
  text        jsonb NOT NULL,
  source_id   text NOT NULL REFERENCES kb.source(id),
  checked_at  timestamptz NOT NULL
);
COMMENT ON TABLE kb.notice IS 'A dated notice about a trail code, promenade section or place id (closures, works, events, cruise days).';
CREATE INDEX IF NOT EXISTS notice_subject ON kb.notice (subject);

-- ------------------------------------------------------------------ load log
CREATE TABLE IF NOT EXISTS kb.load_run (
  loader     text NOT NULL,
  ran_at     timestamptz NOT NULL DEFAULT now(),
  rows       integer NOT NULL,
  detail     text
);
COMMENT ON TABLE kb.load_run IS 'One row per loader run (what was loaded, how many rows).';

-- ------------------------------------------------------------------ read-only role for the MCP server
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'kb_reader') THEN
    CREATE ROLE kb_reader LOGIN;
  END IF;
END $$;
-- PostGIS functions live in public, so kb_reader keeps USAGE there; it gets no table in public.
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM kb_reader;
GRANT USAGE ON SCHEMA kb TO kb_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA kb TO kb_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA kb GRANT SELECT ON TABLES TO kb_reader;
ALTER ROLE kb_reader SET default_transaction_read_only = on;
ALTER ROLE kb_reader SET statement_timeout = '5s';
