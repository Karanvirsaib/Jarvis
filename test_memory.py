from core.memory import MemoryManager

memory = MemoryManager()

memory.remember("name", "Karan")
memory.remember("favorite_language", "Python")

print("Name:", memory.recall("name"))
print("Language:", memory.recall("favorite_language"))
