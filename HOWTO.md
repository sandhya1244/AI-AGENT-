# How to Run the ReAct AI Agent

## What you need before starting

| Requirement | How to get it |
|---|---|
| Python 3.10+ | https://python.org/downloads |
| An Anthropic API key | https://console.anthropic.com/ (free trial available) |
| Docker (optional) | https://docs.docker.com/get-docker/ |

---

## Option A — Run locally with Python (fastest, no Docker needed)

### Step 1 — Download / clone the project

If you have Git:
```
git clone <your-repo-url>
cd ai-agent
```

Or just unzip the folder and open a terminal inside it.

### Step 2 — Create your .env file

```
cp .env.example .env
```

Open `.env` in any text editor and replace the placeholder with your real key:
```
ANTHROPIC_API_KEY=sk-ant-YOUR_REAL_KEY_HERE
```

### Step 3 — Install dependencies

```
pip install -r requirements.txt
```

> On some systems you may need `pip3` instead of `pip`.

### Step 4 — Open the web UI in your browser

```
python web_ui.py
```

You will see:
```
==================================================
  ReAct AI Agent — Web UI
==================================================
  Open in browser: http://localhost:5000
  Press Ctrl+C to stop
==================================================
```

Now open **http://localhost:5000** in your browser. Type any task and press Enter.

---

## Option B — Run with Docker (one command, no Python install needed)

### Step 1 — Create your .env file

```
cp .env.example .env
```

Edit `.env` and add your API key.

### Step 2 — Build and start

```
docker compose up --build
```

That's it. Open **http://localhost:5000** in your browser.

To stop: press `Ctrl+C`, then `docker compose down`.

---

## Option C — Command line (no browser)

### Single task
```
python main.py "What is sqrt(144) + 2^8?"
```

### Interactive mode (type tasks one by one)
```
python main.py
```

---

## Option D — Run the automated test suite

```
python tests/run_tests.py
```

This runs all 5 tasks (including 2 adversarial ones) and prints a summary.

With Docker:
```
docker compose run --rm agent-tests
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: anthropic` | Run `pip install -r requirements.txt` |
| `AuthenticationError` | Check your API key in `.env` |
| Port 5000 already in use | Change `PORT=5001` in `.env` and reopen `http://localhost:5001` |
| `python: command not found` | Use `python3` instead |
| Docker build fails | Make sure Docker Desktop is running |

---

## Project structure

```
ai-agent/
├── .env.example        ← copy to .env and add your API key
├── .env                ← your secrets (never commit this)
├── main.py             ← CLI entry point
├── web_ui.py           ← browser UI (http://localhost:5000)
├── requirements.txt    ← pip dependencies
├── Dockerfile          ← container definition
├── docker-compose.yml  ← one-command startup
├── README.md           ← full technical docs
├── decisions.md        ← engineering decision log
├── HOWTO.md            ← this file
├── src/
│   ├── agent.py        ← ReAct planning loop + budget enforcement
│   └── tools.py        ← web_search, execute_code, calculator
└── tests/
    └── run_tests.py    ← 5 tasks (2 adversarial)
```
