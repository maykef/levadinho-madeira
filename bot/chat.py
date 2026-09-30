"""Local test chat — the same flow as WhatsApp, in the terminal.

  python bot/chat.py            # interactive; /reset starts over as a brand-new visitor
  python bot/chat.py "msg" ...  # scripted: each argument is one message (a digit 1-5 answers the picker,
                                #   "/yes" and "/no" tap the consent buttons)

With wake-on-demand the model may be asleep. The chat doesn't queue anything or start the model:
it shows the notice the WhatsApp bot would send ("[model down — …]") and carries on.
LEVADINHO_DB=/some/scratch.db keeps the test visitor out of the live store.
"""
import sys
import time

import brain
import store

USER = "local-test"


def show(msgs):
    for m in msgs:
        if m["type"] == "list":
            print(f"\n🤖 {m['body']}")
            for i, (_, label) in enumerate(m["options"], 1):
                print(f"   {i}. {label}")
        elif m["type"] == "buttons":
            print(f"\n🤖 {m['body']}\n   [/yes {m['buttons'][0][1]}]  [/no {m['buttons'][1][1]}]")
        else:
            print(f"\n🤖 {m['body']}")


def model_down(text):
    """What app.py would do (dry): queue the message and send WAKING / BUSY. Here: just say so."""
    lang = brain.notice_lang(USER, text)
    return {"type": "text", "body": f"[model down — would queue this message and send the waking-up message:]\n"
                                    f"{brain.WAKING[lang]}"}


def send(text):
    meta = {"events": []}
    try:
        if text in ("/yes", "/no"):
            out = brain.handle_consent(USER, text == "/yes", meta=meta)
        else:
            codes = [c for c, _ in brain.PICKER["options"]]
            u = store.get_user(USER)
            if text.isdigit() and 1 <= int(text) <= 5 and u and (u.get("state") or "").startswith("picking"):
                out = brain.handle(USER, choice=codes[int(text) - 1], meta=meta)
            else:
                out = brain.handle(USER, text=text, meta=meta)
    except brain.LLMDown:
        return [model_down(text)]
    if meta.get("deferred_question"):  # accepted while the model sleeps: the waiting question would be queued
        out = out + [model_down(meta["deferred_question"])]
    return out


def main():
    store.reset(USER)
    if len(sys.argv) > 1:
        for text in sys.argv[1:]:
            print(f"\n👤 {text}")
            t = time.time()
            show(send(text))
            print(f"   ({time.time() - t:.1f}s)")
        return
    print("Levadinho local chat — /reset to start over, Ctrl-D to quit.")
    while True:
        try:
            text = input("\n👤 ").strip()
        except EOFError:
            break
        if text == "/reset":
            store.reset(USER)
            print("(new visitor)")
            continue
        show(send(text))


if __name__ == "__main__":
    main()
