def calculator(expression):
    try:
        return str(eval(expression))
    except:
        return "Invalid calculation"


def remember(user_input, memory, save_memory):
    try:
        data = user_input.replace("remember", "").strip()
        key, value = data.split(" is ")
        memory[key.strip()] = value.strip()
        save_memory(memory)
        return f"Got it. I will remember that {key.strip()} is {value.strip()}"
    except:
        return "Format: remember [thing] is [value]"


def recall(memory):
    if not memory:
        return "I don't remember anything yet."
    return str(memory)
