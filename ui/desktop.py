"""Cinematic CustomTkinter command center for Jarvis."""

from __future__ import annotations

from datetime import datetime
import math
from pathlib import Path
import platform
import threading
from tkinter import Canvas, filedialog

import customtkinter as ctk
from PIL import Image

from config import settings
from core.assistant import JarvisAssistant


BG = "#02070D"
PANEL = "#07131D"
PANEL_2 = "#091A26"
CYAN = "#38E8FF"
CYAN_SOFT = "#159CB4"
BLUE = "#1677FF"
TEXT = "#D9F8FF"
MUTED = "#6E9BA8"
GREEN = "#5CFFB0"
AMBER = "#FFC857"
BORDER = "#103847"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class ArcCore(Canvas):
    """Lightweight animated reactor/status visual built with Tk primitives."""

    def __init__(self, master, size: int = 250, command=None) -> None:
        super().__init__(master, width=size, height=size, bg=BG, highlightthickness=0, cursor="hand2")
        self.size = size
        self.phase = 0
        self.state = "ONLINE"
        self.command = command
        self.hovered = False
        self.bind("<Enter>", lambda _event: setattr(self, "hovered", True))
        self.bind("<Leave>", lambda _event: setattr(self, "hovered", False))
        self.bind("<Button-1>", lambda _event: self.command() if self.command else None)
        self._animate()

    def set_state(self, state: str) -> None:
        self.state = state.upper()

    def _animate(self) -> None:
        self.delete("all")
        c = self.size / 2
        pulse = (4 if self.hovered else 2.5) * math.sin(self.phase / 8)
        glow = "#64F4FF" if self.hovered else CYAN

        # Crosshair, scan field, and fine circuit markers.
        self.create_line(9, c, self.size-9, c, fill="#082A36", width=1)
        self.create_line(c, 9, c, self.size-9, fill="#082A36", width=1)
        scan_y = 34 + ((self.phase * 1.7) % (self.size - 68))
        self.create_line(29, scan_y, self.size-29, scan_y, fill="#0E4655", width=1)
        for x, y, label in ((22, 44, "SYS.01"), (self.size-22, 47, "LINK"),
                            (20, self.size-39, "LOCAL"), (self.size-20, self.size-36, "100%")):
            self.create_text(x, y, text=label, fill="#286575", font=("Consolas", 7),
                             anchor="w" if x < c else "e")
        for radius, color, width in (
            (104 + pulse, "#092C39", 1),
            (91 - pulse, CYAN_SOFT, 2),
            (71 + pulse, glow, 2),
            (48, "#8CF7FF", 2),
        ):
            self.create_oval(c-radius, c-radius, c+radius, c+radius, outline=color, width=width)

        # Counter-rotating broken rings create the holographic turbine effect.
        for i in range(8):
            start = self.phase * 1.4 + i * 45
            self.create_arc(c-99, c-99, c+99, c+99, start=start, extent=19,
                            style="arc", outline="#1A7184", width=3)
            self.create_arc(c-81, c-81, c+81, c+81, start=-start-12, extent=27,
                            style="arc", outline=glow, width=2)
        for i in range(16):
            angle = math.radians(i * 22.5 + self.phase * 1.3)
            inner, outer = 75, 88
            x1, y1 = c + inner * math.cos(angle), c + inner * math.sin(angle)
            x2, y2 = c + outer * math.cos(angle), c + outer * math.sin(angle)
            self.create_line(x1, y1, x2, y2, fill=glow, width=2)
        for i in range(3):
            angle = math.radians(self.phase * 2.2 + i * 120)
            x, y = c + 60 * math.cos(angle), c + 60 * math.sin(angle)
            self.create_oval(x-4, y-4, x+4, y+4, fill="#C9FCFF", outline="")
        self.create_oval(c-34, c-34, c+34, c+34, fill="#052C3A", outline=glow, width=2)
        self.create_oval(c-25, c-25, c+25, c+25, outline="#A8FBFF", width=1)
        self.create_text(c, c-5, text="J", fill="#E8FEFF", font=("Segoe UI", 28, "bold"))
        state_color = AMBER if self.state in {"THINKING", "LISTENING"} else GREEN
        self.create_text(c, c+115, text=f"●  {self.state}", fill=state_color, font=("Consolas", 9, "bold"))
        if self.hovered:
            self.create_text(c, c+15, text="CLICK TO SPEAK", fill="#8EEAF3", font=("Consolas", 7, "bold"))
        self.phase = (self.phase + 1) % 360
        self.after(45, self._animate)


class TelemetryGraph(Canvas):
    """Animated decorative signal graph for the live-system rail."""

    def __init__(self, master) -> None:
        super().__init__(master, height=82, bg=PANEL, highlightthickness=0)
        self.phase = 0
        self._animate()

    def _animate(self) -> None:
        self.delete("all")
        width = max(self.winfo_width(), 220)
        for y in (18, 40, 62):
            self.create_line(0, y, width, y, fill="#0A2C38")
        points = []
        for x in range(0, width + 4, 4):
            y = 41 + math.sin((x + self.phase * 4) / 17) * 10
            y += math.sin((x + self.phase * 2) / 6) * 3
            points.extend((x, y))
        self.create_line(*points, fill=CYAN, width=2, smooth=True)
        sweep = (self.phase * 5) % width
        self.create_line(sweep, 7, sweep, 73, fill="#9AFAFF", width=1)
        self.create_text(4, 7, text="LIVE SIGNAL / 98.7%", anchor="nw",
                         fill="#4B8391", font=("Consolas", 7, "bold"))
        self.phase = (self.phase + 1) % 720
        self.after(70, self._animate)


class JarvisDesktop(ctk.CTk):
    def __init__(self, assistant: JarvisAssistant) -> None:
        super().__init__(fg_color=BG)
        self.assistant = assistant
        self.voice = None
        self.busy = False
        self.last_shown_chart: Path | None = None
        self.speak_answers = ctk.BooleanVar(value=False)
        self.title("J.A.R.V.I.S. // Command Interface")
        self.geometry("1380x860")
        self.minsize(1060, 680)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_topbar()
        self._build_left_rail()
        self._build_center()
        self._build_right_rail()
        self._build_composer()
        self._append("JARVIS", "All systems online. How may I assist you today?")
        self._tick_clock()
        self.after(150, self.input.focus_set)

    def _label(self, master, text: str, size=11, color=MUTED, weight="normal", **kwargs):
        return ctk.CTkLabel(master, text=text, text_color=color,
                            font=ctk.CTkFont(family="Segoe UI", size=size, weight=weight), **kwargs)

    def _build_topbar(self) -> None:
        top = ctk.CTkFrame(self, height=76, corner_radius=0, fg_color="#04101A", border_width=1, border_color=BORDER)
        top.grid(row=0, column=0, columnspan=3, sticky="ew")
        top.grid_columnconfigure(1, weight=1)
        brand = ctk.CTkFrame(top, fg_color="transparent")
        brand.grid(row=0, column=0, padx=24, pady=12, sticky="w")
        self._label(brand, "J.A.R.V.I.S.", 26, TEXT, "bold").pack(anchor="w")
        self._label(brand, "JUST A RATHER VERY INTELLIGENT SYSTEM", 9, CYAN_SOFT, "bold").pack(anchor="w")
        center = ctk.CTkFrame(top, fg_color="transparent")
        center.grid(row=0, column=1)
        self._label(center, "◈  STARK SYSTEMS / PRIVATE NETWORK", 11, CYAN, "bold").pack()
        self._label(center, "LOCAL INTELLIGENCE CORE", 9, MUTED).pack(pady=(3, 0))
        right = ctk.CTkFrame(top, fg_color="transparent")
        right.grid(row=0, column=2, padx=24, sticky="e")
        self.clock = self._label(right, "", 17, TEXT, "bold")
        self.clock.pack(anchor="e")
        self.date_label = self._label(right, "", 9, MUTED)
        self.date_label.pack(anchor="e")

    def _build_left_rail(self) -> None:
        rail = ctk.CTkFrame(self, width=230, corner_radius=0, fg_color=PANEL, border_width=1, border_color=BORDER)
        rail.grid(row=1, column=0, rowspan=2, sticky="nsew")
        rail.grid_propagate(False)
        self._section_title(rail, "CORE MODULES").pack(fill="x", padx=16, pady=(20, 8))
        modules = (
            ("⌁", "CONVERSATION", "help"),
            ("◉", "MEMORY BANK", "show memory"),
            ("⌗", "DATA ANALYSIS", "data help"),
            ("</>", "CODE FORGE", "code help"),
            ("◇", "LEARNING", "learning stats"),
            ("☼", "DAILY BRIEFING", "morning briefing"),
        )
        for icon, label, command in modules:
            ctk.CTkButton(
                rail, text=f"{icon:>3}   {label}", anchor="w", height=42,
                fg_color="transparent", hover_color="#0D2C3A", text_color=TEXT,
                border_width=0, font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
                command=lambda value=command: self._quick_command(value),
            ).pack(fill="x", padx=10, pady=2)
        self._section_title(rail, "INTELLIGENCE").pack(fill="x", padx=16, pady=(28, 10))
        self.mode_control = ctk.CTkSegmentedButton(
            rail, values=["FAST", "DEEP"], command=self._change_intelligence,
            selected_color=CYAN_SOFT, selected_hover_color=CYAN_SOFT,
            unselected_color="#06111A", unselected_hover_color="#0D2C3A",
        )
        self.mode_control.set("FAST")
        self.mode_control.pack(fill="x", padx=16)
        voice_card = ctk.CTkFrame(rail, fg_color=PANEL_2, border_width=1, border_color=BORDER, corner_radius=8)
        voice_card.pack(fill="x", side="bottom", padx=14, pady=18)
        self._label(voice_card, "VOICE SYNTHESIS", 9, MUTED, "bold").pack(anchor="w", padx=12, pady=(12, 2))
        ctk.CTkSwitch(voice_card, text="Spoken responses", variable=self.speak_answers,
                      progress_color=CYAN_SOFT, button_color=CYAN,
                      font=ctk.CTkFont(size=11)).pack(anchor="w", padx=12, pady=(2, 12))

    def _build_center(self) -> None:
        center = ctk.CTkFrame(self, corner_radius=0, fg_color=BG)
        center.grid(row=1, column=1, sticky="nsew", padx=14, pady=(14, 0))
        center.grid_columnconfigure(0, weight=1)
        center.grid_rowconfigure(2, weight=1)
        core_frame = ctk.CTkFrame(center, fg_color=BG, height=270)
        core_frame.grid(row=0, column=0, sticky="ew")
        core_frame.grid_columnconfigure(0, weight=1)
        self.core = ArcCore(core_frame, command=self._listen)
        self.core.grid(row=0, column=0, pady=(0, 2))
        chips = ctk.CTkFrame(center, fg_color="transparent")
        chips.grid(row=1, column=0, pady=(0, 10))
        for label, command in (("MORNING BRIEF", "morning briefing"),
                               ("SYSTEM SCAN", "system status"),
                               ("MEMORY", "show memory"),
                               ("CAPABILITIES", "capabilities")):
            ctk.CTkButton(chips, text=label, width=115, height=27, corner_radius=13,
                          fg_color="#071923", hover_color="#104255", border_width=1,
                          border_color="#14556A", text_color="#8FDCE7",
                          font=ctk.CTkFont(family="Consolas", size=8, weight="bold"),
                          command=lambda value=command: self._quick_command(value)).pack(side="left", padx=4)
        self.transcript = ctk.CTkTextbox(
            center, wrap="word", fg_color=PANEL, border_width=1, border_color=BORDER,
            corner_radius=10, text_color=TEXT, scrollbar_button_color="#174455",
            font=ctk.CTkFont(family="Segoe UI", size=14), spacing3=7,
        )
        self.transcript.grid(row=2, column=0, sticky="nsew")
        self.transcript.configure(state="disabled")
        self.transcript._textbox.tag_configure("jarvis", foreground=CYAN, font=("Consolas", 10, "bold"))
        self.transcript._textbox.tag_configure("user", foreground=GREEN, font=("Consolas", 10, "bold"))
        self.transcript._textbox.tag_configure("body", foreground=TEXT, lmargin1=18, lmargin2=18, rmargin=18)
        self.transcript._textbox.tag_configure("rule", foreground="#174455")

    def _build_right_rail(self) -> None:
        rail = ctk.CTkFrame(self, width=255, corner_radius=0, fg_color=PANEL, border_width=1, border_color=BORDER)
        rail.grid(row=1, column=2, rowspan=2, sticky="nsew")
        rail.grid_propagate(False)
        self._section_title(rail, "SYSTEM TELEMETRY").pack(fill="x", padx=16, pady=(20, 10))
        TelemetryGraph(rail).pack(fill="x", padx=14, pady=(0, 7))
        for label, value, color in (
            ("INTELLIGENCE", "QWEN3 / LOCAL", CYAN),
            ("MEMORY", "PERSISTENT", GREEN),
            ("VOICE LINK", "STANDBY", AMBER),
            ("DATA ENGINE", "READY", GREEN),
            ("SECURITY", "LOCAL-FIRST", CYAN),
        ):
            card = ctk.CTkFrame(rail, height=49, fg_color=PANEL_2, corner_radius=6, border_width=1, border_color="#0D303D")
            card.pack(fill="x", padx=14, pady=4)
            card.grid_columnconfigure(0, weight=1)
            self._label(card, label, 9, MUTED, "bold").grid(row=0, column=0, padx=10, pady=(8, 0), sticky="w")
            self._label(card, value, 10, color, "bold").grid(row=1, column=0, padx=10, pady=(0, 8), sticky="w")
        self._section_title(rail, "QUICK ACTIONS").pack(fill="x", padx=16, pady=(24, 10))
        for text, command in (
            ("＋  LOAD DATASET", self._choose_file),
            ("◎  START VOICE LINK", self._listen),
            ("◫  MEMORY STATUS", lambda: self._quick_command("learning stats")),
        ):
            ctk.CTkButton(rail, text=text, command=command, anchor="w", height=38,
                          fg_color="#0A2633", hover_color="#104255", border_width=1,
                          border_color="#176077", text_color=TEXT,
                          font=ctk.CTkFont(family="Consolas", size=10, weight="bold")).pack(fill="x", padx=14, pady=4)
        info = f"HOST  {platform.node() or 'LOCAL'}\nOS    {platform.system().upper()}\nLINK  ENCRYPTED / LOOPBACK"
        self._label(rail, info, 9, MUTED, justify="left").pack(side="bottom", anchor="w", padx=18, pady=18)

    def _build_composer(self) -> None:
        composer = ctk.CTkFrame(self, height=96, fg_color=BG, corner_radius=0)
        composer.grid(row=2, column=1, sticky="ew", padx=14, pady=14)
        composer.grid_columnconfigure(1, weight=1)
        self.file_button = ctk.CTkButton(composer, text="＋", width=48, height=48, command=self._choose_file,
                                         fg_color="#0A2633", hover_color="#104255", border_width=1, border_color=CYAN_SOFT)
        self.file_button.grid(row=0, column=0, padx=(0, 8))
        self.input = ctk.CTkEntry(composer, height=48, placeholder_text="Enter directive…", fg_color=PANEL,
                                  border_color="#176077", text_color=TEXT, placeholder_text_color=MUTED,
                                  font=ctk.CTkFont(family="Segoe UI", size=14))
        self.input.grid(row=0, column=1, sticky="ew")
        self.input.bind("<Return>", self._submit)
        self.mic_button = ctk.CTkButton(composer, text="◉  TALK", width=92, height=48, command=self._listen,
                                        fg_color="#0A2633", hover_color="#104255", border_width=1, border_color=CYAN_SOFT)
        self.mic_button.grid(row=0, column=2, padx=8)
        self.send_button = ctk.CTkButton(composer, text="EXECUTE  ›", width=112, height=48, command=self._submit,
                                         fg_color=CYAN_SOFT, hover_color="#20BBD2", text_color="#001017",
                                         font=ctk.CTkFont(size=11, weight="bold"))
        self.send_button.grid(row=0, column=3)
        self.status = self._label(composer, "●  SYSTEM READY", 9, GREEN, "bold")
        self.status.grid(row=1, column=0, columnspan=4, pady=(6, 0), sticky="w")

    def _section_title(self, master, text: str):
        return self._label(master, f"── {text}", 10, CYAN_SOFT, "bold")

    def _tick_clock(self) -> None:
        now = datetime.now()
        self.clock.configure(text=now.strftime("%H:%M:%S"))
        self.date_label.configure(text=now.strftime("%A  ·  %d %B %Y").upper())
        self.after(1000, self._tick_clock)

    def _append(self, speaker: str, message: str) -> None:
        tag = "user" if speaker.upper() in {"YOU", "USER"} else "jarvis"
        stamp = datetime.now().strftime("%H:%M:%S")
        box = self.transcript._textbox
        self.transcript.configure(state="normal")
        box.insert("end", f"\n  {speaker.upper()}  //  {stamp}\n", tag)
        box.insert("end", f"  {message.strip()}\n", "body")
        box.insert("end", "  ────────────────────────────────────────────────────────────\n", "rule")
        self.transcript.configure(state="disabled")
        self.transcript.see("end")

    def _quick_command(self, command: str) -> None:
        if str(self.input.cget("state")) == "disabled":
            return
        self._append("YOU", command)
        self._run_command(command)

    def _submit(self, _event: object = None) -> None:
        text = self.input.get().strip()
        if not text:
            return
        self.input.delete(0, "end")
        self._append("YOU", text)
        self._run_command(text)

    def _run_command(self, command: str) -> None:
        self.core.set_state("THINKING")
        self._set_busy(True, "◈  PROCESSING DIRECTIVE…", AMBER)
        threading.Thread(target=self._respond_worker, args=(command,), daemon=True).start()

    def _respond_worker(self, command: str) -> None:
        try:
            response = self.assistant.respond(command)
        except Exception as exc:
            response = f"I couldn't complete that request: {exc}"
        self.after(0, self._finish_response, response)

    def _finish_response(self, response: str) -> None:
        self._append("JARVIS", response)
        self.core.set_state("ONLINE")
        self._set_busy(False, "●  SYSTEM READY", GREEN)
        if self.speak_answers.get():
            threading.Thread(target=self._speak_worker, args=(response,), daemon=True).start()
        chart = self.assistant.analyst.last_chart
        if chart and chart != self.last_shown_chart:
            self._show_chart(chart)

    def _choose_file(self) -> None:
        selected = filedialog.askopenfilename(
            title="JARVIS // Load data source",
            filetypes=(("Data files", "*.csv *.xlsx *.xlsm"), ("CSV files", "*.csv"),
                       ("Excel workbooks", "*.xlsx *.xlsm"), ("All files", "*.*")),
        )
        if selected:
            self._append("YOU", f"Analyze {Path(selected).name}")
            self._run_command(f'analyze "{Path(selected)}"')

    def _listen(self) -> None:
        if self.busy:
            return
        self.core.set_state("LISTENING")
        self._set_busy(True, "◉  VOICE LINK ACTIVE — LISTENING…", AMBER)
        threading.Thread(target=self._listen_worker, daemon=True).start()

    def _listen_worker(self) -> None:
        try:
            text = self._voice_interface().listen(settings.listen_timeout, settings.phrase_time_limit)
            error = None if text else "I didn't catch that. Please try again."
        except Exception as exc:
            text, error = "", str(exc)
        self.after(0, self._finish_listening, text, error)

    def _finish_listening(self, text: str, error: str | None) -> None:
        if error:
            self._append("JARVIS", error)
            self.core.set_state("ONLINE")
            self._set_busy(False, "●  SYSTEM READY", GREEN)
            return
        self._append("YOU", text)
        self._run_command(text)

    def _speak_worker(self, response: str) -> None:
        try:
            self._voice_interface().speak(response)
        except Exception as exc:
            self.after(0, lambda: self.status.configure(text=f"VOICE ERROR // {exc}", text_color=AMBER))

    def _voice_interface(self):
        if self.voice is None:
            from voice.speech import VoiceInterface
            self.voice = VoiceInterface(settings.speech_rate, settings.neural_voice,
                                        settings.neural_voice_rate, settings.neural_voice_pitch)
        return self.voice

    def _change_intelligence(self, selected: str) -> None:
        message = self.assistant.set_intelligence_mode(selected.lower())
        self.status.configure(text=f"◈  {message.upper()}", text_color=CYAN)

    def _show_chart(self, path: Path) -> None:
        window = ctk.CTkToplevel(self, fg_color=BG)
        window.title(f"JARVIS // {path.stem}")
        window.geometry("980x680")
        image = Image.open(path)
        image.thumbnail((930, 610))
        chart_image = ctk.CTkImage(light_image=image, dark_image=image, size=image.size)
        label = ctk.CTkLabel(window, text="", image=chart_image)
        label.image = chart_image
        label.pack(expand=True, fill="both", padx=20, pady=20)
        self.last_shown_chart = path

    def _set_busy(self, busy: bool, status: str, color: str) -> None:
        self.busy = busy
        state = "disabled" if busy else "normal"
        for widget in (self.send_button, self.mic_button, self.file_button, self.input):
            widget.configure(state=state)
        self.status.configure(text=status, text_color=color)
        if not busy:
            self.input.focus_set()


def run_desktop(assistant: JarvisAssistant) -> None:
    JarvisDesktop(assistant).mainloop()
