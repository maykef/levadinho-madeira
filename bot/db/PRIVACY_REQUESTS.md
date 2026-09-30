# Privacy requests: runbook

What to do when someone emails hello@levadinho-madeira.com about their data. The policy
(levadinho-madeira.com/privacy/) promises a reply **within one month**, and that backups forget
deleted data **within 30 days**.

## 1. Get the phone number

The analytics database never stores phone numbers, so we can only find someone by recomputing
their visitor code from the number they used (with the country code). Ask for it if the email
doesn't include it. Reply from the same address the request came from; don't ask for ID
documents unless something looks wrong.

## 2. Access ("what do you have about me?")

```
python bot/privacy_request.py access +351912345678
```

This writes `bot/privacy_exports/access-<code>-<date>.json` (git-ignored) with the visitor row,
the scrubbed conversation, events and positions, plus what the working store holds. Send it as
an attachment, then delete the file.

## 3. Erasure ("delete my data")

```
python bot/privacy_request.py erase +351912345678
```

It shows the counts and asks for `yes`, then deletes:
- the analytics rows (`event`, `conversation_turn`, `location_fix`, `visitor`);
- the working store (language, consent, last 24 h of chat, guide links, messages queued while the
  model was asleep, and the time of the last incoming message);
- the raw guide log files of that person's guide links (`bot/tracklog/`).

Anonymous rows (`consent_declined`, `message_unrecorded`: no visitor id) can't be linked to anyone
and stay. Nightly backups (`/mnt/tank/levadinho_backup/db`) roll off after 30 days. Reply that it's
done and that backups clear within 30 days.

The containerised stack (`levadinho-stack`) doesn't have this script or the consent flow yet;
port both before it goes live.

## 4. Withdrawn consent, no deletion asked

Nothing to do: typing "privacy" and tapping "No thanks" already stops all recording
(`visitor.consent = 'withdrawn'`). Past data stays unless they ask for erasure.

## 5. Correction

Only the scrubbed conversation text could be "wrong", and it records what was said. If someone
asks, erase instead, or edit the row by hand in `conversation_turn`.

## 6. Keep a note

Log each request (date received, type, date answered) in a private note, not in this repository.
It shows the one-month deadline was met if a data protection authority ever asks.
