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
- `/clear` — erase recent conversation history
- `/exit` — shut down OMEGA

Conversation history is stored locally in `data/conversation.json` and is excluded from Git. This is short-term context, not the complete long-term memory system planned for v0.2.

## Safety architecture

The language model never receives automatic authority over physical devices. Robots, smart-home devices, microphones, and cameras will connect through a deny-by-default Integration Hub. Physical and privacy-sensitive actions require permissions, confirmation, logging, and emergency-stop behavior.

See [the architecture document](docs/ARCHITECTURE.md) for the robotics hive, smart-home, voice satellite, and security-vision roadmap.
