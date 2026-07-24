"""Jarvis command router and conversation service."""

from core.analysis import DataAnalyst
from core.coding import LocalCoder
from core.llm import LLMClient
from core.memory import MemoryManager
from core.intent import Intent, IntentInterpreter
from core.research import WebResearcher
from core.resume import ResumeTailor
from core.actions import ActionManager
from core.tasks import (
    InvalidTaskTransitionError,
    IntelligentPlanner,
    JsonTaskStore,
    TaskNotFoundError,
    TaskService,
)
from core.tasks.integrations import create_jarvis_registry
from datetime import datetime
from pathlib import Path
import re


class JarvisAssistant:
    def __init__(
        self,
        memory: MemoryManager,
        llm: LLMClient,
        task_path: str | Path | None = None,
    ) -> None:
        self.memory = memory
        self.llm = llm
        self.analyst = DataAnalyst()
        self.coder = LocalCoder(llm)
        self.interpreter = IntentInterpreter(llm)
        self.researcher = WebResearcher(llm)
        self.resume = ResumeTailor(memory, llm)
        self.actions = ActionManager(memory)
        resolved_task_path = Path(task_path) if task_path else memory.database_path.with_name("tasks.json")
        task_tools = create_jarvis_registry(self)
        task_planner = IntelligentPlanner(llm, task_tools)
        self.tasks = TaskService(
            JsonTaskStore(resolved_task_path),
            tools=task_tools,
            planner=task_planner,
        )
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

        task_response = self._task_command(text)
        if task_response is not None:
            return task_response

        if lowered.startswith("confirm action"):
            action_id = text[len("confirm action"):].strip() or None
            return self.actions.confirm(action_id)
        if lowered in {"cancel action", "reject action", "do not run it"}:
            return self.actions.cancel()
        if lowered in {"action preview", "pending action"}:
            return self.actions.preview()
        if lowered in {"action history", "recent actions"}:
            actions = self.memory.recent_actions()
            if not actions:
                return "No actions have been requested yet."
            return "ACTION HISTORY\n" + "\n".join(
                f"- {item['created_at']} | {item['action']} | {item['status']} | {item['id']}"
                for item in actions
            )
        action_name = self._requested_action(lowered)
        if action_name:
            return self.actions.execute(action_name)
        app_match = re.fullmatch(r"(?:open|launch)(?: the)? (.+)", text, flags=re.IGNORECASE)
        if app_match:
            try:
                return self.actions.execute_application(app_match.group(1).strip())
            except ValueError as exc:
                return str(exc)

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
                "'code help', 'resume help', 'action help', or 'capabilities'."
            )
        if lowered == "action help":
            return (
                "Desktop actions:\n"
                "- open calculator\n- open notepad\n- open file explorer\n- open calendar\n"
                "Application launches run immediately and are recorded locally.\n"
                "Use 'action history' to inspect the local audit trail."
            )
        if lowered in {"resume help", "cv help"}:
            return (
                "ATS RESUME WORKFLOW\n"
                "1. Attach your current .docx, .pdf, or .txt resume, or use: load resume \"C:\\path\\resume.docx\"\n"
                "2. Paste the full role posting with: tailor resume: <job description>\n"
                "3. Review the matched keywords and honest gaps.\n"
                "4. Say: export resume word — or — export resume pdf\n"
                "Jarvis preserves official titles and source facts; unsupported requirements are reported as gaps, never invented."
            )
        if lowered == "resume status":
            return self.resume.status()
        if lowered.startswith("load resume "):
            path = text[len("load resume "):].strip().strip('"')
            try:
                return self.resume.load(path)
            except (FileNotFoundError, ValueError, RuntimeError) as exc:
                return str(exc)
        if lowered.startswith("tailor resume:") or lowered.startswith("tailor cv:"):
            description = text.split(":", 1)[1].strip()
            try:
                return self.resume.tailor(description)
            except (ValueError, RuntimeError) as exc:
                return str(exc)
        if lowered in {"export resume word", "export resume docx", "create resume word"}:
            try:
                path = self.resume.export("word")
                return f"ATS-friendly Word resume created: {path}"
            except (ValueError, RuntimeError) as exc:
                return str(exc)
        if lowered in {"export resume pdf", "create resume pdf"}:
            try:
                path = self.resume.export("pdf")
                return f"ATS-friendly PDF resume created: {path}"
            except (ValueError, RuntimeError) as exc:
                return str(exc)
        if lowered in {"capabilities", "show capabilities", "what can you do"}:
            return (
                "ACTIVE MODULES\n"
                "- Local conversation through Ollama (Fast and Deep modes)\n"
                "- Persistent facts, learned phrases, and answer feedback\n"
                "- Voice input plus offline/neural spoken responses\n"
                "- CSV and Excel analysis, charts, correlations, and read-only SQL\n"
                "- Safe Python and SQL code generation (never auto-executed)\n"
                "- Local morning briefings and system status\n"
                "- Evidence-grounded web research with source links\n\n"
                "- Confirmed Windows actions with previews and a local audit trail\n"
                "- Truth-constrained ATS resume tailoring with Word and PDF export\n\n"
                "PLANNED / REQUIRES CONNECTIONS\n"
                "- Calendar and email digest, scheduled monitors, "
                "document indexing, and a broader installable skills catalog."
            )
        web_query = self._web_query(text)
        if web_query:
            return self.researcher.research(web_query)
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
        if response.strip().upper().startswith("NEEDS_WEB:"):
            query = response.split(":", 1)[1].strip() or prompt
            response = self.researcher.research(query)
        self.history.extend(
            [
                {"role": "user", "content": text},
                {"role": "assistant", "content": response},
            ]
        )
        return response

    def _task_command(self, text: str) -> str | None:
        lowered = text.casefold().strip()
        try:
            if lowered in {"task help", "tasks help"}:
                return (
                    "TASK COMMANDS\n"
                    "- create task: <step one; step two>\n"
                    "- task status [task ID]\n- show tasks\n"
                    "- resume task [task ID]\n- approve step <step ID>\n"
                    "- retry step <step ID>\n- cancel task [task ID]"
                )
            if lowered.startswith("create task:"):
                goal = text.split(":", 1)[1].strip()
                return self.tasks.format(self.tasks.create(goal))
            if lowered in {"show tasks", "task history", "list tasks"}:
                return self.tasks.format_list()
            if lowered == "task status" or lowered.startswith("task status "):
                task_id = text[len("task status"):].strip() or None
                return self.tasks.format(self.tasks.get(task_id))
            if lowered == "resume task" or lowered.startswith("resume task "):
                task_id = text[len("resume task"):].strip() or None
                return self.tasks.format(self.tasks.resume(task_id))
            if lowered.startswith("approve step "):
                step_id = text[len("approve step "):].strip()
                return self.tasks.format(self.tasks.approve(step_id))
            if lowered.startswith("retry step "):
                step_id = text[len("retry step "):].strip()
                return self.tasks.format(self.tasks.retry(step_id))
            if lowered == "cancel task" or lowered.startswith("cancel task "):
                task_id = text[len("cancel task"):].strip() or None
                return self.tasks.format(self.tasks.cancel(task_id))
        except (TaskNotFoundError, LookupError, InvalidTaskTransitionError, ValueError) as exc:
            return f"Task request could not be completed: {exc}"
        return None

    @staticmethod
    def _web_query(text: str) -> str | None:
        lowered = text.casefold().strip()
        for prefix in ("search web:", "web search:", "research:", "look up:", "verify online:"):
            if lowered.startswith(prefix):
                return text[len(prefix):].strip()
        current_signals = (
            "latest", "today", "currently", "current price", "current rate", "recent news",
            "this week", "this month", "as of now", "live score", "weather forecast",
        )
        if any(signal in lowered for signal in current_signals):
            return text
        return None

    @staticmethod
    def _requested_action(lowered: str) -> str | None:
        exact_commands = {
            "open calculator": "calculator",
            "launch calculator": "calculator",
            "open notepad": "notepad",
            "launch notepad": "notepad",
            "open file explorer": "file_explorer",
            "launch file explorer": "file_explorer",
            "open explorer": "file_explorer",
            "open calendar": "calendar",
            "launch calendar": "calendar",
            "open calender": "calendar",
            "launch calender": "calendar",
        }
        return exact_commands.get(lowered.strip())

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
