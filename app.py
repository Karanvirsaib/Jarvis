from core.llm import ask_llm
from core.memory import MemoryManager

memory = MemoryManager()

print("=" * 50)
print("🤖 JARVIS v0.4")
print("=" * 50)

while True:
    user_input = input("\nYou > ")

    # 1. Auto memory extraction
    memory_result = memory.extract_and_store(user_input)

    if memory_result:
        print("JARVIS (memory):", memory_result)

    # 2. Build context from memory
    name = memory.recall("name")

    context = ""
    if name:
        context = f"User name is {name}."

    # 3. Call LLM
    response = ask_llm(user_input, context)

    print("\nJARVIS >", response)
