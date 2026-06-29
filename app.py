from core.llm import ask_llm


def banner():
    print("=" * 60)
    print("🤖 JARVIS v1.0")
    print("=" * 60)


def main():
    banner()

    while True:
        user = input("\nYou > ").strip()

        if user.lower() in {"exit", "quit"}:
            print("JARVIS > Goodbye!")
            break

        if not user:
            continue

        print("\nJARVIS >")
        print(ask_llm(user))


if __name__ == "__main__":
    main()
