import json
from pathlib import Path
from core.brain.claude_adapter import ClaudeCodeAdapter
from core.agents.executive import HermesExecutiveAgent
from core.memory.honcho_client import LocalMemoryStore
from apps.jarvis.config import config

class JarvisOrchestrator:
    def __init__(self, root_dir: str):
        self.root = Path(root_dir)
        model_config = config.get("models", "routing", {})
        openrouter_config = config.get("models", "openrouter", {})
        ollama_config = config.get("models", "ollama", {})
        self.executive = HermesExecutiveAgent(
            provider=model_config.get("executive_agent", "openrouter"),
            model=model_config.get("executive_model", "openrouter/free"),
            fallback_provider=model_config.get("fallback_agent", "ollama"),
            fallback_model=model_config.get("fallback_model", "qwen3.5:4b"),
            openrouter_url=openrouter_config.get(
                "chat_completions_url", "https://openrouter.ai/api/v1/chat/completions"
            ),
            ollama_url=ollama_config.get(
                "generate_url", "http://localhost:11434/api/generate"
            ),
            openrouter_timeout=int(openrouter_config.get("timeout_seconds", 120)),
            ollama_timeout=int(ollama_config.get("timeout_seconds", 180)),
            context_length=int(ollama_config.get("context_length", 8192)),
        )
        allowed_dirs = config.get("permissions", "defaults", {}).get("allowed_directories", [])
        self.coding_brain = ClaudeCodeAdapter(allowed_dirs=allowed_dirs)
        self.memory = LocalMemoryStore(self.root / "memory" / "jarvis_memory.db")

        # Load system personality
        self.system_prompt = (
            "You are JARVIS, a highly capable personal AI assistant for Karanvir Singh Saib.\n"
            "Style: concise, calm, professional, precise, action-oriented.\n"
            "You orchestrate tasks by determining whether to answer directly, ask for confirmation, "
            "or delegate to specialized tools like Claude Code."
        )

    def route_request(self, user_input: str) -> str:
        """Route the task dynamically to the right tool/agent."""
        self.memory.add_message("user", user_input)

        # Basic text processing heuristics (can be replaced by an LLM classification step)
        command = user_input.lower()
        if "code" in command or "program" in command or "repo" in command:
            print("JARVIS: Delegating complex coding task to Claude Code...")
            return self.coding_brain.execute_task(user_input, str(self.root))
        elif "remember" in command:
            fact = user_input.split("remember", 1)[-1].strip()
            self.memory.add_fact("Preferences", fact)
            return "Saved to long-term memory, sir."
        else:
            # General reasoning
            context = self.memory.get_recent_context(limit=5)
            # Flatten context
            flat_ctx = "\n".join([f"{role}: {msg}" for role, msg in context])
            full_prompt = f"Recent History:\n{flat_ctx}\n\nUser Request: {user_input}"

            response = self.executive.think(full_prompt, system=self.system_prompt)
            self.memory.add_message("assistant", response)
            return response
