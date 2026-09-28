-- Levadinho analytics database (PostgreSQL 16 + PostGIS).
-- Applied by `python bot/analytics.py init` (idempotent). Every table and column carries a
-- COMMENT so people and LLM agents can read the meaning straight from the catalogue.
--
-- Pseudonymisation (GDPR, decision D5): no phone numbers or IP addresses are stored here.
-- A visitor is `visitor_id` = HMAC-SHA256(secret key, phone number); the key is kept apart
-- from the data (bot/.visitor_key). Access/erasure requests: recompute the id from the phone.

CREATE EXTENSION IF NOT EXISTS postgis;

-- ------------------------------------------------------------------ lookups
CREATE TABLE IF NOT EXISTS route (
  route_id     text PRIMARY KEY,
  title        jsonb NOT NULL,
  is_private   boolean NOT NULL DEFAULT false,
  length_m     integer,
  line         geography(LineString, 4326),
  updated_at   timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE route IS 'A walking route the audio guide covers (e.g. PR1 Vereda do Areeiro, or a private test route). Synced from bot/routes*/<id>/route.json.';
COMMENT ON COLUMN route.route_id IS 'Short route identifier used everywhere else (e.g. "pr1", "ely-test").';
COMMENT ON COLUMN route.title IS 'Route name per language code, e.g. {"en": "...", "pt": "..."}.';
COMMENT ON COLUMN route.is_private IS 'True for owner test routes that are not offered to the public.';
COMMENT ON COLUMN route.length_m IS 'Route length in metres along the track.';
COMMENT ON COLUMN route.line IS 'The route track as a WGS84 line (from the GPX).';
COMMENT ON COLUMN route.updated_at IS 'When this row was last synced from route.json.';

CREATE TABLE IF NOT EXISTS stop (
  route_id     text NOT NULL REFERENCES route(route_id) ON DELETE CASCADE,
  stop_id      text NOT NULL,
  seq          integer NOT NULL,
  name         jsonb NOT NULL,
  at_m         integer NOT NULL,
  radius_m     integer NOT NULL,
  geom         geography(Point, 4326) NOT NULL,
  PRIMARY KEY (route_id, stop_id)
);
COMMENT ON TABLE stop IS 'An audio-guide stop (point of interest) on a route; the guide plays its clip when the visitor reaches it.';
COMMENT ON COLUMN stop.route_id IS 'Route this stop belongs to.';
COMMENT ON COLUMN stop.stop_id IS 'Stop identifier, unique within the route (e.g. "s3").';
COMMENT ON COLUMN stop.seq IS 'Order of the stop along the route, starting at 1.';
COMMENT ON COLUMN stop.name IS 'Stop name per language code.';
COMMENT ON COLUMN stop.at_m IS 'Distance from the route start to this stop, in metres along the track.';
COMMENT ON COLUMN stop.radius_m IS 'Trigger radius in metres: the clip plays when the visitor is this close.';
COMMENT ON COLUMN stop.geom IS 'Stop location (WGS84 point).';

CREATE TABLE IF NOT EXISTS campaign (
  campaign_id  text PRIMARY KEY,
  route_id     text REFERENCES route(route_id),
  description  text,
  created_at   timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE campaign IS 'A QR code campaign: the tag in the QR''s pre-filled WhatsApp text (e.g. "#areeiro") tells where the visitor scanned it.';
COMMENT ON COLUMN campaign.campaign_id IS 'The tag without "#", e.g. "areeiro", "ely".';
COMMENT ON COLUMN campaign.route_id IS 'The guide route this QR code opens.';
COMMENT ON COLUMN campaign.description IS 'Where the QR code is placed and what it is for.';
COMMENT ON COLUMN campaign.created_at IS 'When the campaign was registered.';

CREATE TABLE IF NOT EXISTS event_type (
  event_type        text PRIMARY KEY,
  channel           text NOT NULL,
  description       text NOT NULL,
  attributes_schema jsonb NOT NULL DEFAULT '{}'::jsonb
);
COMMENT ON TABLE event_type IS 'Catalogue of every event type that can appear in event.event_type, with its meaning and the JSON Schema of its attributes.';
COMMENT ON COLUMN event_type.event_type IS 'Event name, verb-style (e.g. "question_asked", "stop_fired").';
COMMENT ON COLUMN event_type.channel IS 'Where it happens: "whatsapp" (the bot) or "guide" (the audio-guide web app).';
COMMENT ON COLUMN event_type.description IS 'Plain-English meaning of the event.';
COMMENT ON COLUMN event_type.attributes_schema IS 'JSON Schema describing event.attributes for this event type.';

-- ------------------------------------------------------------------ people (pseudonymous)
CREATE TABLE IF NOT EXISTS visitor (
  visitor_id   text PRIMARY KEY,
  first_seen   timestamptz NOT NULL DEFAULT now(),
  last_seen    timestamptz NOT NULL DEFAULT now(),
  country      text,
  lang         text
);
COMMENT ON TABLE visitor IS 'One row per visitor. Pseudonymous: no phone number is stored, only a keyed hash of it.';
COMMENT ON COLUMN visitor.visitor_id IS 'HMAC-SHA256 of the WhatsApp phone number with a secret key kept outside the database (32 hex chars). Stable across days.';
COMMENT ON COLUMN visitor.first_seen IS 'First interaction with the bot or guide.';
COMMENT ON COLUMN visitor.last_seen IS 'Most recent interaction.';
COMMENT ON COLUMN visitor.country IS 'ISO 3166-1 alpha-2 country of the phone number''s dialling code (source market), e.g. "GB", "PT", "DE".';
COMMENT ON COLUMN visitor.lang IS 'Language the visitor chose or last wrote in: pt, en, fr, de, pl.';
ALTER TABLE visitor ADD COLUMN IF NOT EXISTS consent text;
ALTER TABLE visitor ADD COLUMN IF NOT EXISTS consent_version text;
ALTER TABLE visitor ADD COLUMN IF NOT EXISTS consent_at timestamptz;
COMMENT ON COLUMN visitor.consent IS 'Privacy notice: "given" (accepted) or "withdrawn" (declined later, which also stops the service). Rows exist only for visitors who accepted at least once; nothing is recorded while withdrawn. Legal basis of the record: legitimate interest (the notice must be accepted to use the assistant); guide GPS is a separate opt-in.';
COMMENT ON COLUMN visitor.consent_version IS 'Date of the privacy policy whose notice the visitor accepted (e.g. "2026-09-28").';
COMMENT ON COLUMN visitor.consent_at IS 'When consent was last given or withdrawn.';

-- ------------------------------------------------------------------ facts
CREATE TABLE IF NOT EXISTS event (
  event_id     bigserial PRIMARY KEY,
  occurred_at  timestamptz NOT NULL,
  received_at  timestamptz NOT NULL DEFAULT now(),
  channel      text NOT NULL,
  event_type   text NOT NULL REFERENCES event_type(event_type),
  visitor_id   text REFERENCES visitor(visitor_id),
  session_id   text,
  route_id     text,
  stop_id      text,
  campaign_id  text,
  lang         text,
  country      text,
  geom         geography(Point, 4326),
  attributes   jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS event_time_idx ON event (occurred_at);
CREATE INDEX IF NOT EXISTS event_type_idx ON event (event_type, occurred_at);
CREATE INDEX IF NOT EXISTS event_visitor_idx ON event (visitor_id, occurred_at);
CREATE INDEX IF NOT EXISTS event_route_idx ON event (route_id, occurred_at);
CREATE INDEX IF NOT EXISTS event_geom_idx ON event USING gist (geom);
COMMENT ON TABLE event IS 'Append-only log of every interaction: one row per thing that happened, in WhatsApp or in the audio guide.';
COMMENT ON COLUMN event.event_id IS 'Sequential id.';
COMMENT ON COLUMN event.occurred_at IS 'When it happened (phone clock for guide events, server clock for WhatsApp).';
COMMENT ON COLUMN event.received_at IS 'When the server stored it (guide events recorded offline arrive later).';
COMMENT ON COLUMN event.channel IS '"whatsapp" (the bot) or "guide" (the audio-guide web app).';
COMMENT ON COLUMN event.event_type IS 'What happened; see the event_type catalogue.';
COMMENT ON COLUMN event.visitor_id IS 'Pseudonymous visitor (see visitor).';
COMMENT ON COLUMN event.session_id IS 'Guide session: the random token of the guide link the bot sent (nothing in it derives from the phone number).';
COMMENT ON COLUMN event.route_id IS 'Route involved, if any.';
COMMENT ON COLUMN event.stop_id IS 'Stop involved, if any.';
COMMENT ON COLUMN event.campaign_id IS 'QR campaign that brought the visitor, if known.';
COMMENT ON COLUMN event.lang IS 'Language of the interaction.';
COMMENT ON COLUMN event.country IS 'Visitor''s source-market country (copied from visitor for easy grouping).';
COMMENT ON COLUMN event.geom IS 'Where it happened, if known (WGS84 point).';
COMMENT ON COLUMN event.attributes IS 'Event-specific details; shape documented in event_type.attributes_schema.';

CREATE TABLE IF NOT EXISTS conversation_turn (
  turn_id        bigserial PRIMARY KEY,
  occurred_at    timestamptz NOT NULL DEFAULT now(),
  visitor_id     text REFERENCES visitor(visitor_id),
  direction      text NOT NULL CHECK (direction IN ('in', 'out')),
  msg_kind       text NOT NULL,
  text_scrubbed  text,
  scrub_method   text,
  lang           text,
  is_question    boolean,
  intent         text,
  topic          text,
  trail_code     text,
  campaign_id    text,
  latency_ms     integer,
  model          text
);
CREATE INDEX IF NOT EXISTS turn_time_idx ON conversation_turn (occurred_at);
CREATE INDEX IF NOT EXISTS turn_visitor_idx ON conversation_turn (visitor_id, occurred_at);
CREATE INDEX IF NOT EXISTS turn_intent_idx ON conversation_turn (intent);
COMMENT ON TABLE conversation_turn IS 'Every WhatsApp message to and from the bot, kept permanently (decision D1) with personal details scrubbed out.';
COMMENT ON COLUMN conversation_turn.turn_id IS 'Sequential id.';
COMMENT ON COLUMN conversation_turn.occurred_at IS 'When the message was received (in) or sent (out).';
COMMENT ON COLUMN conversation_turn.visitor_id IS 'Pseudonymous visitor (see visitor).';
COMMENT ON COLUMN conversation_turn.direction IS '"in" = from the visitor, "out" = from the bot.';
COMMENT ON COLUMN conversation_turn.msg_kind IS 'WhatsApp message kind: text, location, language_choice, location_request, list, picker, welcome, voice, image, etc.';
COMMENT ON COLUMN conversation_turn.text_scrubbed IS 'Message text with personal data replaced by tags such as [NAME], [PHONE], [EMAIL], [CODE], [LINK].';
COMMENT ON COLUMN conversation_turn.scrub_method IS 'How it was scrubbed: "rules" (patterns only) or "rules+llm" (patterns plus the local model removing names).';
COMMENT ON COLUMN conversation_turn.lang IS 'Language of this message.';
COMMENT ON COLUMN conversation_turn.is_question IS 'For incoming text: did the visitor ask something (vs greeting/thanks)?';
COMMENT ON COLUMN conversation_turn.intent IS 'For questions: what it is about (status, booking, fees, transport, weather, safety, route_info, alternatives, facilities, other).';
COMMENT ON COLUMN conversation_turn.topic IS 'Short free-text topic label from the model, e.g. "sunrise timing", "parking at Areeiro".';
COMMENT ON COLUMN conversation_turn.trail_code IS 'Trail the question is about, if any (e.g. "PR1").';
COMMENT ON COLUMN conversation_turn.campaign_id IS 'QR campaign active for the visitor at the time, if any.';
COMMENT ON COLUMN conversation_turn.latency_ms IS 'For bot answers: time taken to produce the reply, in milliseconds.';
COMMENT ON COLUMN conversation_turn.model IS 'For bot answers produced by the language model: the model name.';

CREATE TABLE IF NOT EXISTS location_fix (
  fix_id       bigserial PRIMARY KEY,
  occurred_at  timestamptz NOT NULL,
  received_at  timestamptz NOT NULL DEFAULT now(),
  visitor_id   text REFERENCES visitor(visitor_id),
  session_id   text,
  route_id     text,
  source       text NOT NULL,
  geom         geography(Point, 4326) NOT NULL,
  accuracy_m   real,
  altitude_m   real,
  altitude_accuracy_m real,
  speed_ms     real,
  heading_deg  real,
  screen       text,
  online       boolean
);
CREATE INDEX IF NOT EXISTS fix_time_idx ON location_fix (occurred_at);
CREATE INDEX IF NOT EXISTS fix_session_idx ON location_fix (session_id, occurred_at);
CREATE INDEX IF NOT EXISTS fix_geom_idx ON location_fix USING gist (geom);
COMMENT ON TABLE location_fix IS 'Individual position signals (decision D5: each kept separately, not aggregated): GPS fixes from the audio guide and location pins shared in WhatsApp.';
COMMENT ON COLUMN location_fix.fix_id IS 'Sequential id.';
COMMENT ON COLUMN location_fix.occurred_at IS 'When the position was measured (phone clock).';
COMMENT ON COLUMN location_fix.received_at IS 'When the server stored it (fixes recorded without signal arrive later).';
COMMENT ON COLUMN location_fix.visitor_id IS 'Pseudonymous visitor (see visitor).';
COMMENT ON COLUMN location_fix.session_id IS 'Guide session token, for guide fixes.';
COMMENT ON COLUMN location_fix.route_id IS 'Route being walked, for guide fixes.';
COMMENT ON COLUMN location_fix.source IS '"guide_gps" (continuous GPS in the guide), "guide_poll" (one-off request while GPS was silent) or "whatsapp_pin" (location shared in WhatsApp).';
COMMENT ON COLUMN location_fix.geom IS 'Measured position (WGS84 point).';
COMMENT ON COLUMN location_fix.accuracy_m IS 'Horizontal accuracy radius in metres (smaller is better).';
COMMENT ON COLUMN location_fix.altitude_m IS 'Altitude in metres, if the phone reported it.';
COMMENT ON COLUMN location_fix.altitude_accuracy_m IS 'Altitude accuracy in metres.';
COMMENT ON COLUMN location_fix.speed_ms IS 'Ground speed in metres per second, if reported (empty until moving).';
COMMENT ON COLUMN location_fix.heading_deg IS 'Direction of travel in degrees from north, if reported.';
COMMENT ON COLUMN location_fix.screen IS 'Page visibility when measured: "visible" or "hidden".';
COMMENT ON COLUMN location_fix.online IS 'Whether the phone had a network connection at the time.';

-- ------------------------------------------------------------------ event catalogue
INSERT INTO event_type (event_type, channel, description, attributes_schema) VALUES
 ('conversation_started', 'whatsapp', 'A visitor messaged the bot for the first time (or again after the history expired).', '{"type":"object","properties":{"first_text_kind":{"type":"string"}}}'),
 ('qr_scanned', 'whatsapp', 'The visitor sent the pre-filled greeting of a QR code (campaign_id tells which QR).', '{"type":"object","properties":{}}'),
 ('language_selected', 'whatsapp', 'The visitor picked a language in the 5-language picker.', '{"type":"object","properties":{"lang":{"type":"string"}}}'),
 ('question_asked', 'whatsapp', 'The visitor asked a question (details in conversation_turn).', '{"type":"object","properties":{"intent":{"type":"string"},"topic":{"type":"string"},"trail_code":{"type":["string","null"]},"trail_status":{"type":"string"}}}'),
 ('answer_sent', 'whatsapp', 'The bot answered a question with the language model.', '{"type":"object","properties":{"latency_ms":{"type":"integer"}}}'),
 ('location_shared', 'whatsapp', 'The visitor shared a location pin (the point itself is in location_fix and event.geom).', '{"type":"object","properties":{"nearest_route":{"type":"string"},"distance_m":{"type":"integer"}}}'),
 ('location_requested', 'whatsapp', 'The bot sent WhatsApp''s "Send location" button (visitor typed guide/guia).', '{"type":"object","properties":{}}'),
 ('guide_link_sent', 'whatsapp', 'The bot sent a personal audio-guide link (session_id = its token).', '{"type":"object","properties":{"via":{"type":"string","enum":["campaign","location"]}}}'),
 ('non_text_received', 'whatsapp', 'The visitor sent something the bot cannot read (voice, photo, sticker…).', '{"type":"object","properties":{"kind":{"type":"string"}}}'),
 ('guide_started', 'guide', 'The visitor tapped Start in the audio guide.', '{"type":"object","properties":{"ua":{"type":"string"},"audio_lang":{"type":"string"}}}'),
 ('stop_fired', 'guide', 'A stop was reached by GPS and its clip queued.', '{"type":"object","properties":{"progress_m":{"type":"integer"}}}'),
 ('stop_fired_estimate', 'guide', 'A stop was triggered by the position estimate while GPS was silent (screen locked).', '{"type":"object","properties":{"est_m":{"type":"integer"},"via":{"type":"string"},"secs":{"type":"integer"}}}'),
 ('stop_missed', 'guide', 'The visitor passed a stop without it firing (e.g. screen off); it can still be played by hand.', '{"type":"object","properties":{"progress_m":{"type":"integer"}}}'),
 ('clip_played', 'guide', 'A stop clip started playing.', '{"type":"object","properties":{"via":{"type":"string"}}}'),
 ('clip_ended', 'guide', 'A stop clip finished playing.', '{"type":"object","properties":{}}'),
 ('clip_failed', 'guide', 'A stop clip could not play.', '{"type":"object","properties":{"err":{"type":"string"}}}'),
 ('clip_manual', 'guide', 'The visitor tapped ▶ to play a stop by hand.', '{"type":"object","properties":{}}'),
 ('pocket_mode', 'guide', 'Pocket mode switched on or off.', '{"type":"object","properties":{"on":{"type":"boolean"}}}'),
 ('screen_state', 'guide', 'The guide page became visible or hidden (e.g. phone locked).', '{"type":"object","properties":{"state":{"type":"string"}}}'),
 ('wake_lock', 'guide', 'Screen wake lock acquired, released or refused.', '{"type":"object","properties":{"state":{"type":"string"}}}'),
 ('offline_pack', 'guide', 'Offline download finished or failed.', '{"type":"object","properties":{"ok":{"type":"boolean"},"bytes":{"type":"integer"}}}'),
 ('gps_error', 'guide', 'The phone refused or failed to give a position.', '{"type":"object","properties":{"code":{"type":"integer"},"poll":{"type":"boolean"}}}'),
 ('heartbeat', 'guide', 'Guide alive signal every 10 s (diagnostics: audio state, fix count, steps).', '{"type":"object"}'),
 ('guide_other', 'guide', 'Any other guide diagnostic event (original name in attributes.ev).', '{"type":"object","properties":{"ev":{"type":"string"}}}'),
 ('consent_given', 'whatsapp', 'The visitor accepted the privacy notice (WhatsApp; count these for "how many accepted"), or chose "share my walk" in the guide (event row channel "guide").', '{"type":"object","properties":{"version":{"type":"string"}}}'),
 ('consent_withdrawn', 'whatsapp', 'A visitor who had accepted tapped "Don''t accept" (after typing "privacy"). Service stops and nothing more is recorded until they accept again.', '{"type":"object","properties":{"version":{"type":"string"}}}'),
 ('consent_declined', 'whatsapp', 'ANONYMOUS: a visitor did not accept the privacy notice (count these for "how many did not accept"). No visitor_id, only time and language.', '{"type":"object","properties":{}}'),
 ('message_unrecorded', 'whatsapp', 'ANONYMOUS: a message from a visitor who has not accepted the notice (yet). No visitor_id, no text, only time and language.', '{"type":"object","properties":{"kind":{"type":"string"}}}')
ON CONFLICT (event_type) DO UPDATE SET channel = EXCLUDED.channel, description = EXCLUDED.description, attributes_schema = EXCLUDED.attributes_schema;
