# AI Agent — Powered by Ollama (Free & Local)

A smart AI agent that runs completely free on your own computer. It can search the web, run code, and do maths — all by itself. No API key, no internet subscription, no cost.

---

## How it works

The agent thinks like a person solving a problem:

```
THINK → decide what to do next
ACT   → use a tool (search, code, or calculator)
LOOK  → read what the tool returned
CHECK → did that help? if not, try something else
REPEAT until done
```

For example, if you ask "what is the square root of 144 plus 2 to the power of 8", it will:
1. Think: "this is a maths problem"
2. Use the calculator tool
3. Get the answer
4. Return it to you

If you ask "plan a wedding", it will search the web, gather ideas, and write you a plan.

---

## The 3 tools it can use

| Tool | What it does |
|---|---|
| Web Search | Looks things up on DuckDuckGo — no account needed |
| Run Code | Writes and runs Python code to solve problems |
| Calculator | Does maths safely — handles sqrt, sin, log, and more |

---

## Safety limits

The agent has two guardrails built in:

**Call limit — max 10 AI calls per task**
Each time the agent thinks, that's one call. At 10 it stops and tells you what it managed to finish.

**Loop detection**
If the agent tries the exact same thing twice in a row, it automatically switches approach instead of wasting calls going in circles.

---

## How to run it

Make sure Ollama is installed (https://ollama.com/download) and you've pulled a model:
```
ollama pull llama3.2
```

Then open two terminal windows:

**Window 1:**
```
ollama serve
```

**Window 2:**
```
cd ai-agent
pip install -r requirements.txt
python web_ui.py
```

Open your browser and go to **http://localhost:5000**

Full step-by-step instructions are in `HOWTO.md`.

---

## The 5 built-in tests

You can run these automatically to check everything is working:
```
python tests/run_tests.py
```

| Test | What it does | Type |
|---|---|---|
| 1 | Solves a multi-step maths problem | Normal |
| 2 | Writes and runs the Sieve of Eratosthenes | Normal |
| 3 | Answers "how long does light take to reach Earth?" | Normal |
| 4 | Tries to find a document that doesn't exist — forever | Trap test |
| 5 | Asked to research every programming language ever made | Trap test |

The two trap tests are intentionally impossible or absurd. The agent should recognise this and stop gracefully instead of looping forever or pretending to complete the task.

**Trap test 4 result:** The agent searches once, finds nothing, gets told to keep searching — then the loop detector kicks in and it gives up cleanly with an explanation.

**Trap test 5 result:** The agent does as much as it can in 10 calls, then stops and honestly says what it finished and what it couldn't get to.

---

## Known limitations

**Web search is basic.** DuckDuckGo works great for facts and general knowledge but struggles with recent news or very specific queries. The agent handles this by switching to its calculator or code tools when search fails.

**Local models make mistakes.** Llama3.2 running on your computer is not as accurate as paid models like GPT-4 or Claude. It sometimes ignores formatting instructions. The agent has a fallback that handles this gracefully.

**10 calls goes fast on big tasks.** If you ask something very broad ("research the entire history of AI"), the agent will do its best and then stop, explaining what it didn't get to. This is by design — not a bug.

---

## What could be added in the future

- Let the agent read and write files on your computer
- Give it a memory so it remembers things between sessions
- Break big tasks into smaller chunks automatically
- Show the agent's thinking in real time as it types
- Add more models (Mistral, Qwen, Phi) as easy options in the UI

---

## Files in this project

```
ai-agent/
├── .env              ← your settings (Ollama model, port)
├── web_ui.py         ← the website at localhost:5000
├── main.py           ← run tasks from the terminal instead
├── src/
│   ├── agent.py      ← the brain (planning, thinking, loop detection)
│   └── tools.py      ← the hands (search, code runner, calculator)
└── tests/
    └── run_tests.py  ← the 5 automated tests
```
