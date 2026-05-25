# How to Run the AI Agent

This agent runs completely free on your computer using Ollama. No API key needed, no internet required after setup.

---

## Before you start, install these two things

**1. Python** — download and install from https://python.org/downloads
Pick the latest version. During install, tick the box that says "Add Python to PATH".

**2. Ollama** — download and install from https://ollama.com/download
Click Windows, run the installer. This is what runs the AI on your computer for free.

---

## First time setup (do this once)

Open Command Prompt and run these one by one:

**Download the AI model (about 2GB, takes a few minutes):**
```
ollama pull llama3.2
```

**Go into the project folder:**
```
cd C:\Users\sandhya\Downloads\ai-agent-fixed\ai-agent
```

**Install the Python packages the project needs:**
```
pip install -r requirements.txt
```

**Set up your settings file** — open the file called `.env` in Notepad and make sure it contains exactly this:
```
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
PORT=5000
```
Save and close.

---

## Every time you want to use it

You need two Command Prompt windows open at the same time.

**Window 1 — start the AI engine:**
```
ollama serve
```
Leave this running. Don't close it.

**Window 2 — start the website:**
```
cd C:\Users\sandhya\Downloads\ai-agent-fixed\ai-agent
python web_ui.py
```

Now open your browser and go to:
```
http://localhost:5000
```

Type anything in the box and press Enter. The agent will think, search, run code, or calculate — whatever the task needs.

---

## To stop everything

In Window 2, press `Ctrl + C`.
In Window 1, press `Ctrl + C`.
Done.

---

## Something not working?

**"ollama is not recognized"**
Restart your computer after installing Ollama, then try again.

**"pip is not recognized"**
Try `pip3` instead of `pip`. Or reinstall Python and tick "Add to PATH".

**"Cannot connect to Ollama"**
You forgot to start Window 1. Run `ollama serve` first.

**Port 5000 already in use**
Open `.env` and change `PORT=5000` to `PORT=5001`, then visit `http://localhost:5001`.

**The model is slow**
That's normal the first time — it's loading into memory. After the first response it gets faster.

---

## What's inside the project

```
ai-agent/
├── .env              ← your settings (Ollama URL, model name, port)
├── web_ui.py         ← the website you open at localhost:5000
├── main.py           ← if you prefer typing tasks in the terminal instead
├── src/
│   ├── agent.py      ← the brain — plans, reflects, decides what to do
│   └── tools.py      ← the hands — web search, run code, calculator
└── tests/
    └── run_tests.py  ← runs 5 test tasks automatically to check everything works
```

---

## Want to use a different AI model?

If llama3.2 is too slow on your computer, try a smaller one:

```
ollama pull phi3
```

Then open `.env` and change `OLLAMA_MODEL=llama3.2` to `OLLAMA_MODEL=phi3`. Restart Window 2.

| Model | Size | Good for |
|---|---|---|
| llama3.2 | 2 GB | Best quality (recommended) |
| phi3 | 2 GB | Fast, good for simple tasks |
| llama3.2:1b | 1 GB | Very low RAM computers |
