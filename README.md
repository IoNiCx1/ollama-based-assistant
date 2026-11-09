# Local Assistant

Runs offline on Windows using a local model through Ollama.

## Setup (one time)

1. Install Python 3.10+ from python.org (tick "Add Python to PATH").
2. Install Ollama from ollama.com.
3. In PowerShell, in this folder:

    py -m pip install requests
    ollama pull qwen2.5:3b-instruct

## Run

1. Start Ollama (Start menu, or `ollama serve`).
2. py assistant.py   (type "exit" to quit)

## Notes

- Internet is needed only for the first model download.
- Stop Ollama from the tray icon to free RAM.