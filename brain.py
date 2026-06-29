import ollama
import json
import ast

MEMORY_FILE = "memory.json"

# ---------------- MEMORY ----------------

def load_memory():
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f)

def build_context(memory):
    if not memory:
        return ""
    return "Memory:\n" + "\n".join([f"{k}: {v}" for k, v in memory.items()])

# ---------------- SAFE MATH ENGINE ----------------

def safe_eval(expr):
    """
    Safe math evaluator (no eval security risk)
    """
    return eval(compile(ast.parse(expr, mode='eval'), '<string>', 'eval'))

def is_math(text):
    allowed = set("0123456789+-*/(). %")
    return all(c in allowed for c in text.replace("**", "*"))

# ---------------- MAIN BRAIN ----------------

def get_response(user_input):
    memory = load_memory()
    user_lower = user_input.lower().strip()

    # ---------------- MEMORY COMMAND ----------------
    if user_lower.startswith("remember"):
        try:
            data = user_input.replace("remember", "").strip()
            key, value = data.split(" is ")
            memory[key.strip()] = value.strip()
            save_memory(memory)
            return f"I'll remember that {key.strip()} is {value.strip()}."
        except:
            return "Use: remember <thing> is <value>"

    if user_lower in ["what do you remember", "show memory"]:
        return str(memory) if memory else "Nothing stored yet."

    # ---------------- MATH TOOL ----------------
    if is_math(user_input):
        try:
            return f"Result: {safe_eval(user_input)}"
        except:
            pass

    # ---------------- CONTEXT ----------------
    context = build_context(memory)

    # ---------------- AGENT PROMPT ----------------
    prompt = f"""
You are Jarvis, an advanced AI assistant running locally.

You are intelligent, concise, and act like a personal AI agent.

You have:
- Memory system (user facts)
- Math tool (automatic detection)
- Local reasoning ability

Rules:
- Use memory when relevant
- Be direct and helpful
- Do not be verbose unless asked

Memory:
{context}

User: {user_input}

Jarvis:
"""

    # ---------------- OLLAMA CALL ----------------
    response = ollama.chat(
        model="qwen3:8b",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return response["message"]["content"]