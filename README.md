# OMEGA

OMEGA is a private-first personal AI assistant designed to grow from natural conversation into memory, voice, knowledge retrieval, smart-home control, robotics, and opt-in computer vision.

Version 0.1 provides a conversational core backed by a local Ollama model. It uses an original confident, candid, witty personality and keeps a small transparent conversation history on your computer.

## Requirements

- Python 3.10 or newer
- Ollama installed and running
- A local Ollama model (the default model name is `llama3.2`)

## Run

1. Install Ollama using its official installation instructions.
2. Download or run the model you want in Ollama.
3. From this project directory, run:

   ```bash
   python omega.py
   ```

To choose another installed model:

```bash
OMEGA_MODEL=your-model-name python omega.py
```

On Windows PowerShell:

```powershell
$env:OMEGA_MODEL = "your-model-name"
python omega.py
```

## Commands

- `/help` — display commands
- `/status` — show runtime status
- `/briefing` — preview the morning briefing now
- `/clear` — erase recent conversation history
- `/exit` — shut down OMEGA

Conversation history is stored locally in `data/conversation.json` and is excluded from Git. This is short-term context, not the complete long-term memory system planned for v0.2.


## Proactive morning briefing

While OMEGA is running, she can initiate one briefing each morning at 9:00 AM. It includes the local date and time, weather for the configured home location, and clothing advice. The daily delivery state is saved locally in `data/proactive.json`.

Preview it at any time:

```bash
/briefing
```

Optional environment settings:

```bash
OMEGA_BRIEFING_TIME=08:30 python3 omega.py
OMEGA_HOME_LOCATION="Newark, New Jersey" python3 omega.py
OMEGA_PROACTIVE=false python3 omega.py
OMEGA_SPEAK_BRIEFINGS=true python3 omega.py
```

On macOS, `OMEGA_SPEAK_BRIEFINGS=true` reads the proactive briefing aloud with the built-in `say` voice. OMEGA must currently be running for the internal scheduler to fire. A macOS LaunchAgent can be added later so the operating system starts OMEGA automatically before the briefing.

## Safety architecture

The language model never receives automatic authority over physical devices. Robots, smart-home devices, microphones, and cameras will connect through a deny-by-default Integration Hub. Physical and privacy-sensitive actions require permissions, confirmation, logging, and emergency-stop behavior.

See [the architecture document](docs/ARCHITECTURE.md) for the robotics hive, smart-home, voice satellite, and security-vision roadmap.
