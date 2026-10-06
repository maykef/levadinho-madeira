"""Twilio Content templates for the WhatsApp menus (since 2026-10-04, when the bot moved to its own WhatsApp
sender +44 7455 718697 on Twilio): the tappable language list and the Accept / Don't accept buttons.

Inside a conversation the visitor started (the 24-hour window) WhatsApp needs no approval for these, so they
work as soon as they exist. The texts come from brain.py (PICKER, CONSENT_BUTTONS); the notice text itself is a
variable, so changing CONSENT_ASK needs no new template. Changing a menu's labels does: bump VERSION and re-run.

  python3 bot/twilio_content.py        # create what's missing (idempotent), write bot/twilio_content.json

twilio_wa.py reads twilio_content.json at start-up; without it the menus fall back to typed replies.
Needs TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN in the environment (bot/.env).
"""
import base64
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import brain  # noqa: E402

OUT = os.path.join(HERE, "twilio_content.json")
API = "https://content.twilio.com/v1/Content"
VERSION = "v3"


def _req(method, url, body=None):
    auth = base64.b64encode(f"{os.environ['TWILIO_ACCOUNT_SID']}:{os.environ['TWILIO_AUTH_TOKEN']}".encode()).decode()
    req = urllib.request.Request(url, json.dumps(body).encode() if body else None, method=method,
                                 headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def existing():
    out, url = {}, API + "?PageSize=500"
    while url:
        d = _req("GET", url)
        out.update({c["friendly_name"]: c["sid"] for c in d.get("contents", [])})
        url = (d.get("meta") or {}).get("next_page_url")
    return out


def wanted():
    p = brain.PICKER
    yield f"levadinho_lang_picker_{VERSION}", {
        "language": "en",
        "types": {"twilio/list-picker": {"body": p["body"], "button": p["button"],
                                         "items": [{"id": f"lang_{code}", "item": label, "description": p["notes"][code]}
                                                   for code, label in p["options"]]
                                                  + [{"id": p["decline"][0], "item": p["decline"][1],
                                                      "description": p["decline"][2]}]},
                  "twilio/text": {"body": p["body"]}}}
    for lang, (yes, no) in brain.CONSENT_BUTTONS.items():
        yield f"levadinho_consent_{lang}_{VERSION}", {
            "language": {"pt": "pt_PT"}.get(lang, lang), "variables": {"1": "notice"},
            "types": {"twilio/quick-reply": {"body": "{{1}}", "actions": [{"title": yes, "id": "consent_yes"},
                                                                          {"title": no, "id": "consent_no"}]},
                      "twilio/text": {"body": "{{1}}"}}}


def main():
    have = existing()
    sids = {}
    for name, spec in wanted():
        if name not in have:
            have[name] = _req("POST", API, {"friendly_name": name, **spec})["sid"]
            print("created", name, have[name])
        sids[name.removesuffix(f"_{VERSION}")] = have[name]
    json.dump(sids, open(OUT, "w"), indent=1)
    print(f"wrote {OUT}: {sids}")


if __name__ == "__main__":
    main()
