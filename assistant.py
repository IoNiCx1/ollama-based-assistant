from router import handle

history = []
print("Local assistant ready. Type 'exit' to quit.")
while True:
    user = input("\nYou: ").strip()
    if user.lower() in ("exit", "quit"):
        break
    if not user:
        continue

    reply = handle(user, history)
    history.append({"role": "user", "content": user})
    history.append({"role": "assistant", "content": reply})
    history = history[-10:]  # keep the last 10 messages
    print(f"\nAssistant: {reply}")