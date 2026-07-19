# J.A.R.V.I.S.

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Ollama](https://img.shields.io/badge/AI-Local%20Ollama-111111)](https://ollama.com/)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D4?logo=windows11&logoColor=white)](#requirements)
[![Tests](https://img.shields.io/badge/tests-42%20passing-3AA76D)](#testing)

> A local-first personal AI assistant with voice, memory, data analysis, code generation, and a cinematic desktop command center.

Jarvis is a Windows-focused Python assistant powered by local Ollama models. It combines natural conversation with persistent memory, microphone input, human-friendly speech, spreadsheet analysis, safe code generation, and an animated science-fiction interface.

The project is designed around a simple principle: personal assistance should remain on your machine whenever possible.

![Jarvis Obsidian command center](docs/screenshots/jarvis-dashboard.png)

## Highlights

- **Local intelligence** — conversations run through an Ollama model on your computer.
- **Cinematic desktop UI** — animated reactor core, telemetry, quick actions, voice states, and Fast/Deep modes.
- **Natural voice output** — neural speech with an offline fallback and formatting-aware pronunciation.
- **Persistent memory** — remembers facts, successful answers, feedback, and custom phrases in SQLite.
- **CSV and Excel analysis** — summaries, grouped calculations, correlations, charts, and worksheet selection.
- **Read-only SQL** — query the active dataset locally without permitting database writes.
- **Code generation** — generate Python and SQL without automatically executing untrusted code.
- **Intent interpretation** — understands informal, incomplete, and misspelled analysis requests.
- **Local learning** — teach Jarvis phrases and mark answers as helpful or incorrect.
- **ATS resume tailoring** — match a real resume to a job description, report unsupported requirements as gaps, and export Word or PDF without changing official titles or inventing achievements.
- **Grounded web research** — searches public sources, extracts evidence, and returns linked citations instead of guessing.

## Interface

<p align="center">
  <img src="docs/screenshots/jarvis-conversation.png" alt="Jarvis conversation workspace" width="92%">
</p>

The Version 1 desktop experience includes:

- a hover-reactive animated intelligence core;
- one-click voice activation from the reactor;
- live signal and system telemetry;
- shortcuts for memory, analysis, coding, diagnostics, and briefings;
- a structured conversation console;
- optional spoken responses; and
- separate previews for generated charts.

## Architecture

```mermaid
flowchart LR
    UI["Desktop, CLI, or Voice"] --> Assistant["Jarvis Assistant"]
    Assistant --> Intent["Intent Interpreter"]
    Assistant --> LLM["Local Ollama Model"]
    Assistant --> Memory["SQLite Memory"]
    Intent --> Analysis["Data Analysis Engine"]
    Intent --> Code["Safe Code Generator"]
    Analysis --> Files["CSV and Excel Files"]
    Assistant --> Research["Grounded Web Research"]
    Assistant --> Resume["ATS Resume Tailor"]
    Resume --> Documents["Word and PDF"]
    Assistant --> Speech["Neural or Offline Speech"]
```

## Requirements

- Windows 10 or Windows 11
- Python 3.11 or newer
- [Ollama](https://ollama.com/) running locally
- A microphone for voice input
- Internet access only for Google speech recognition and the optional neural voice

Typed chat, Ollama reasoning, memory, and dataset analysis remain local.
Resume source files and job descriptions are processed locally by the configured Ollama model. Tailored files are written under `output/resumes` for Word and `output/pdf` for PDF.

### Tailor a resume

1. Open **Resume** in the desktop navigation and select the current `.docx`, `.pdf`, or `.txt` resume.
2. Paste the complete posting as `tailor resume: <job description>`.
3. Review Jarvis's matched keywords and honest gaps.
4. Use `export resume word` or `export resume pdf`.

The source resume is the factual boundary: Jarvis may reorganize and rephrase supported experience, but it blocks unsupported employer names, employment titles, and dates. Personal projects remain projects. Always review the final document before submitting it.

## Installation

Clone the repository and enter the project directory:

```powershell
git clone https://github.com/Karanvirsaib/Jarvis.git
cd Jarvis
```

Create a virtual environment and install the dependencies:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Install the default local model:

```powershell
ollama pull qwen3:8b
```

Ensure Ollama is running before starting Jarvis.

## Running Jarvis

### Desktop command center

```powershell
.\venv\Scripts\python.exe .\main.py --mode desktop
```

### Typed terminal chat

```powershell
.\venv\Scripts\python.exe .\main.py
```

### Typed chat with spoken answers

```powershell
.\venv\Scripts\python.exe .\main.py --speak
```

### Continuous voice mode

```powershell
.\venv\Scripts\python.exe .\main.py --mode voice
```

You can also run `launch_jarvis.py` to open the desktop interface using the project virtual environment.

## Example Commands

### Conversation and intelligence

```text
What can you do?
system status
morning briefing
deep mode
think deeply: explain how neural networks learn
search web: latest RBI repo rate
verify online: current WHO guidance on hypertension
```

Jarvis automatically invokes web research for explicitly current questions and when
the local model declares that it lacks reliable knowledge. Research answers are
restricted to retrieved evidence, include numbered source links, and report when a
claim cannot be verified. Web access improves freshness but cannot guarantee that
every published source is correct; primary and official sources are ranked first.

### Memory and learning

```text
remember project is Jarvis
show memory
forget project
learn phrase: show me the cash => sum revenue by region
good answer
that's wrong
learning stats
```

### Data analysis

```text
analyze C:\path\to\sales.csv
analyze C:\path\to\workbook.xlsx
list sheets
use sheet Sales
data summary
describe column revenue
sum revenue by region
average revenue by product
bar chart revenue by region
correlations
```

### SQL and code generation

```text
sql SELECT region, SUM(revenue) FROM data GROUP BY region
write sql: calculate total revenue by region
write python: clean missing values in a CSV and save a new file
```

The loaded dataset is exposed to SQL as a table named `data`. Only `SELECT` and `WITH` queries are accepted, and displayed results are limited to 200 rows. Generated Python and SQL are shown to the user but never executed automatically.

## Natural-Language Data Requests

Jarvis uses a local intent interpreter to map informal requests to safe, deterministic tools. For example:

```text
show me da money by place
make a grapf of sales for each product
```

When the intended columns are clear, Jarvis performs the corresponding grouped calculation or chart. Low-confidence interpretations fall back to ordinary conversation instead of running a tool.

## Local Memory and Privacy

Jarvis stores personal facts, interaction feedback, and learned phrases in `data/jarvis.db`. This database is excluded from Git and should remain private to each installation.

Jarvis does not:

- upload its SQLite memory to this repository;
- rewrite its own source code;
- automatically execute generated code; or
- allow write operations through its dataset SQL interface.

Speech-to-text currently uses Google Speech Recognition. Neural speech uses Microsoft Edge TTS when available and falls back to offline Windows speech if the neural service cannot be reached.

## Configuration

Jarvis is configured with environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `JARVIS_MODEL` | `qwen3:8b` | Ollama model used for conversation |
| `JARVIS_DATABASE` | `data/jarvis.db` | Local SQLite memory location |
| `JARVIS_SPEECH_RATE` | `175` | Offline speech rate |
| `JARVIS_LISTEN_TIMEOUT` | `5` | Seconds to wait for microphone input |
| `JARVIS_PHRASE_TIME_LIMIT` | `15` | Maximum spoken-command duration |
| `JARVIS_OLLAMA_KEEP_ALIVE` | `30m` | Time Ollama keeps the model loaded |
| `JARVIS_MAX_RESPONSE_TOKENS` | `192` | Fast-mode response budget; lower values return sooner |
| `JARVIS_NEURAL_VOICE` | `en-GB-RyanNeural` | Edge TTS voice |
| `JARVIS_NEURAL_VOICE_RATE` | `+0%` | Neural speech speed adjustment |
| `JARVIS_NEURAL_VOICE_PITCH` | `-2Hz` | Neural speech pitch adjustment |

Example:

```powershell
$env:JARVIS_MODEL = "qwen3:14b"
$env:JARVIS_MAX_RESPONSE_TOKENS = "512"
.\venv\Scripts\python.exe .\main.py --mode desktop
```

## Project Structure

```text
Jarvis/
├── core/                 Assistant routing, memory, LLM, analysis, and coding
├── ui/                   Cinematic CustomTkinter desktop interface
├── voice/                Speech recognition and natural speech output
├── data/                 Local runtime data, excluded from Git
├── main.py               CLI, voice, and desktop entry point
├── launch_jarvis.py      Windows desktop launcher
├── config.py             Environment-based configuration
└── test_*.py             Automated test suite
```

## Tests

Run the complete test suite:

```powershell
.\venv\Scripts\python.exe -m unittest discover -v
```

Version 1 currently includes tests for memory, intent interpretation, LLM options, safe code generation, dataset analysis, read-only SQL, assistant routing, and natural speech formatting.

## Version 1 Roadmap

Potential next steps include:

- wake-word detection;
- email and calendar briefings;
- scheduled and continuous monitoring;
- deeper local-document research with citations;
- installable skill modules;
- configurable UI themes;
- streaming responses and speech; and
- packaged Windows releases.

## Acknowledgements

The project takes architectural inspiration from [OpenJarvis](https://github.com/open-jarvis/OpenJarvis), particularly its local-first approach, agent modes, briefings, monitoring, and extensible skills philosophy.

Jarvis and the cinematic interface are an independent fan-inspired project and are not affiliated with Marvel Studios or Stark Industries.

---

Built as a personal, local-first AI command center.
