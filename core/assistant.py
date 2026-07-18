"""Jarvis command router and conversation service."""

from core.analysis import DataAnalyst
from core.coding import LocalCoder
from core.llm import LLMClient
from core.memory import MemoryManager
from core.intent import Intent, IntentInterpreter
from datetime import datetime
import re


class JarvisAssistant:
    def __init__(self, memory: MemoryManager, llm: LLMClient) -> None:
        self.memory = memory
        self.llm = llm
        self.analyst = DataAnalyst()
        self.coder = LocalCoder(llm)
        self.interpreter = IntentInterpreter(llm)
        self.history: list[dict[str, str]] = []
        self.intelligence_mode = "fast"
        self.last_interaction_id: int | None = None

    def set_intelligence_mode(self, mode: str) -> str:
        normalized = mode.strip().lower()
        if normalized not in {"fast", "deep"}:
            raise ValueError("Intelligence mode must be 'fast' or 'deep'.")
        self.intelligence_mode = normalized
        return f"{normalized.title()} intelligence mode enabled."

    def respond(self, user_input: str) -> str:
        response = self._respond(user_input)
        interaction_id = self.memory.record_interaction(user_input, response)
        if user_input.strip().casefold() not in {
            "good answer",
            "that was helpful",
            "that's wrong",
            "that was wrong",
            "bad answer",
        }:
            self.last_interaction_id = interaction_id
        return response

    def _respond(self, user_input: str) -> str:
        text = user_input.strip()
        lowered = text.lower()
        if not text:
            return "I didn't receive a command."

        if lowered in {"good answer", "that was helpful"}:
            if self.last_interaction_id and self.memory.rate_interaction(self.last_interaction_id, 1):
                return "Thanks. I'll use that successful answer as a future example."
            return "There isn't a previous answer to rate yet."
        if lowered in {"that's wrong", "that was wrong", "bad answer"}:
            if self.last_interaction_id and self.memory.rate_interaction(self.last_interaction_id, -1):
                return "Understood. I marked that answer as unsuccessful. Tell me what you meant so I can learn it."
            return "There isn't a previous answer to rate yet."
        if lowered.startswith("learn phrase:"):
            lesson = text[len("learn phrase:") :]
            if "=>" not in lesson:
                return "Use: learn phrase: <what I say> => <Jarvis command>"
            phrase, command = lesson.split("=>", 1)
            try:
                self.memory.learn_command(phrase, command)
            except ValueError as exc:
                return str(exc)
            return f"Learned: '{phrase.strip()}' means '{command.strip()}'."
        if lowered == "learning stats":
            stats = self.memory.learning_stats()
            return (
                f"Learning memory: {stats['interactions']} interactions, "
                f"{stats['positive']} successful examples, and "
                f"{stats['learned_commands']} learned phrases."
            )
        if lowered == "clear learning memory":
            self.memory.clear_learning()
            self.last_interaction_id = None
            return "Learning history and learned phrases were cleared. Saved personal facts were kept."

        learned_command = self.memory.recall_learned_command(text)
        if learned_command and learned_command.casefold() != lowered:
            result = self._respond(learned_command)
            return f"Using what you taught me: {learned_command}\n\n{result}"

        try:
            data_response = self.analyst.handle(text)
        except (FileNotFoundError, ValueError) as exc:
            return str(exc)
        if data_response is not None:
            return data_response

        if lowered in {"help", "commands"}:
            return (
                "Core systems: conversation, persistent memory, local learning, voice, "
                "CSV/Excel analysis, charts, read-only SQL, and Python/SQL generation.\n"
                "Try 'morning briefing', 'system status', 'show memory', 'data help', "
                "'code help', or 'capabilities'."
            )
        if lowered in {"capabilities", "show capabilities", "what can you do"}:
            return (
                "ACTIVE MODULES\n"
                "- Local conversation through Ollama (Fast and Deep modes)\n"
                "- Persistent facts, learned phrases, and answer feedback\n"
                "- Voice input plus offline/neural spoken responses\n"
                "- CSV and Excel analysis, charts, correlations, and read-only SQL\n"
                "- Safe Python and SQL code generation (never auto-executed)\n"
                "- Local morning briefings and system status\n\n"
                "PLANNED / REQUIRES CONNECTIONS\n"
                "- Calendar and email digest, scheduled monitors, deep web research, "
                "document indexing, and a broader installable skills catalog."
            )
        if lowered in {"system status", "status report", "diagnostic"}:
            stats = self.memory.learning_stats()
            dataset = self.analyst.dataset
            data_status = (
                f"loaded ({len(dataset.frame):,} rows, {len(dataset.columns)} columns)"
                if dataset else "standby"
            )
            return (
                f"SYSTEM STATUS // {datetime.now():%H:%M:%S}\n"
                f"Intelligence: {self.intelligence_mode.title()} / {self.llm.model}\n"
                f"Memory: online ({stats['interactions']} interactions, "
                f"{stats['learned_commands']} learned phrases)\n"
                f"Data engine: {data_status}\n"
                "Code execution: locked (generation only)\n"
                "Network posture: local-first"
            )
        if lowered in {"morning briefing", "daily briefing", "brief me"}:
            stats = self.memory.learning_stats()
            remembered = self.memory.all()
            facts = ", ".join(f"{key}: {value}" for key, value in list(remembered.items())[:3])
            return (
                f"Good {self._day_period()}. It is {datetime.now():%A, %d %B %Y at %H:%M}.\n"
                f"Jarvis is online in {self.intelligence_mode.title()} mode. "
                f"The learning core contains {stats['interactions']} interactions.\n"
                f"Priority memory: {facts or 'No priority facts have been stored yet.'}\n"
                "Email, calendar, news, and weather are not connected yet, so they were "
                "excluded from this local briefing."
            )
        if lowered in {"code help", "coding help"}:
            return (
                "Local coding commands:\n"
                "- write python: <what the program should do>\n"
                "- write sql: <what the query should calculate>\n"
                "- sql SELECT ... FROM data (runs read-only SQL on loaded data)"
            )
        if lowered.startswith("write python:") or lowered.startswith("python code:"):
            request = text.split(":", 1)[1].strip()
            if not request:
                return "Describe the Python code you want after the colon."
            return self.coder.generate_python(request)
        if lowered.startswith("write sql:") or lowered.startswith("sql code:"):
            request = text.split(":", 1)[1].strip()
            if not request:
                return "Describe the SQL query you want after the colon."
            columns = self.analyst.dataset.columns if self.analyst.dataset else None
            return self.coder.generate_sql(request, columns)
        if lowered in {"fast mode", "use fast mode"}:
            return self.set_intelligence_mode("fast")
        if lowered in {"deep mode", "use deep mode"}:
            return self.set_intelligence_mode("deep")
        if lowered in {"show memory", "what do you remember"}:
            memories = self.memory.all()
            return "\n".join(f"{k}: {v}" for k, v in memories.items()) or "Nothing stored yet."
        if lowered.startswith("forget "):
            key = text[len("forget ") :]
            return f"Forgot {key}." if self.memory.forget(key) else f"I didn't have a memory named {key}."
        if lowered.startswith("remember "):
            statement = text[len("remember ") :]
            parts = statement.split(" is ", 1)
            if len(parts) != 2:
                return "Use: remember <thing> is <value>"
            self.memory.remember(parts[0], parts[1])
            return f"I'll remember that {parts[0].strip()} is {parts[1].strip()}."

        stored = self.memory.extract_and_store(text)
        if stored:
            return stored

        if self._should_interpret(text):
            intent = self.interpreter.interpret(
                text,
                self.analyst.dataset.columns if self.analyst.dataset else None,
            )
            interpreted = self._execute_intent(intent, text)
            if interpreted is not None:
                return interpreted

        one_time_deep = lowered.startswith("think deeply:")
        prompt = text.split(":", 1)[1].strip() if one_time_deep else text
        successful_examples = self.memory.relevant_successes(prompt)
        learning_context = self.memory.context()
        if successful_examples:
            examples = "\n".join(
                f"User: {past_user}\nHelpful answer: {past_response}"
                for past_user, past_response in successful_examples
            )
            learning_context += f"\n\nPreviously successful related examples:\n{examples}"
        response = self.llm.ask(
            prompt,
            learning_context,
            self.history[-8:],
            deep_reasoning=one_time_deep or self.intelligence_mode == "deep",
        )
        self.history.extend(
            [
                {"role": "user", "content": text},
                {"role": "assistant", "content": response},
            ]
        )
        return response

    @staticmethod
    def _day_period() -> str:
        hour = datetime.now().hour
        if hour < 12:
            return "morning"
        if hour < 17:
            return "afternoon"
        return "evening"

    def _should_interpret(self, text: str) -> bool:
        signals = r"\b(data|dataset|csv|excel|sheet|column|sales?|revenue|total|average|count|chart|graph|plot|python|sql|code|script| by )\b"
        return bool(re.search(signals, text, flags=re.IGNORECASE))

    def _execute_intent(self, intent: Intent, original: str) -> str | None:
        if intent.action == "chat" or intent.confidence < 0.58:
            return None
        try:
            if intent.action == "data_summary":
                result = self.analyst.handle("data summary")
            elif intent.action == "describe_column" and intent.value:
                result = self.analyst.handle(f"describe column {intent.value}")
            elif intent.action == "grouped_analysis" and intent.value and intent.group:
                operation = intent.operation if intent.operation in {"sum", "average", "count"} else "sum"
                result = self.analyst.handle(f"{operation} {intent.value} by {intent.group}")
            elif intent.action == "chart" and intent.value and intent.group:
                chart_type = intent.chart_type if intent.chart_type in {"bar", "line", "pie"} else "bar"
                result = self.analyst.handle(f"{chart_type} chart {intent.value} by {intent.group}")
            elif intent.action == "correlations":
                result = self.analyst.handle("correlations")
            elif intent.action == "generate_python":
                result = self.coder.generate_python(intent.request or original)
            elif intent.action == "generate_sql":
                columns = self.analyst.dataset.columns if self.analyst.dataset else None
                result = self.coder.generate_sql(intent.request or original, columns)
            else:
                return None
        except (FileNotFoundError, ValueError) as exc:
            return f"I interpreted that as {intent.action.replace('_', ' ')}, but {exc}"
        if result is None:
            return None
        understood = intent.action.replace("_", " ")
        return f"I understood that as: {understood}.\n\n{result}"
