"""Local test chat — the same flow as WhatsApp, in the terminal.

  python bot/chat.py            # interactive; /reset starts over as a brand-new visitor
  python bot/chat.py "msg" ...  # scripted: each argument is one message (a digit 1-5 answers the picker)
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
        else:
            print(f"\n🤖 {m['body']}")


def send(text):
    codes = [c for c, _ in brain.PICKER["options"]]
    u = store.get_user(USER)
    if text.isdigit() and 1 <= int(text) <= 5 and u and u.get("state") == "picking":
        return brain.handle(USER, choice=codes[int(text) - 1])
    return brain.handle(USER, text=text)


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
