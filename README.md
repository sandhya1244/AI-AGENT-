# ReAct AI Agent — Budget-Aware Task Solver

A self-reflecting AI agent that solves tasks efficiently with hard limits on LLM calls and cost.

---

## How It Works

The agent follows the **ReAct** pattern (Reason + Act):

```
THINK → ACT → OBSERVE → REFLECT → repeat
```

Each iteration the model outputs structured JSON:

```json
{
  "thought":    "What I want to do and why",
  "reflection": "Did the last step work? Do I need to change strategy?",
  "action":     "web_search | execute_code | calculator | final_answer",
  "action_input": { ... },
  "answer":     "Only when action = final_answer"
}
```

### Budget Enforcement

| Limit        | Value    | Enforced by          |
|--------------|----------|----------------------|
| LLM calls    | 10       | Checked before every API call |
| Budget       | $0.20    | Tracked per token (input + output) |

When either limit is hit the agent **stops immediately** and returns a structured summary of what was completed and what was not.

### Reflection & Loop Detection

After every tool call the agent explicitly answers:
> *"Am I making progress? Should I change strategy?"*

The `Agent._detect_loop()` method catches **exact repetition** (same action + same input twice in a row). On detection:
1. A warning is printed.
2. The agent is forced to either switch tools or provide a `final_answer`.

---

## Tools

| Tool | Description |
|------|-------------|
| `web_search(query)` | DuckDuckGo Instant Answers — no API key required |
| `execute_code(code, language)` | Runs Python or Node.js in a subprocess with a 10-second timeout |
| `calculator(expression)` | Safe AST-based math evaluator (sqrt, sin, cos, log, …) |

---

## Running

### With Docker (recommended — one command)

```bash
# 1. Set your API key
cp .env.example .env
# Edit .env and add your key

# 2. Build & run tests
docker build -t ai-agent .
docker run --env-file .env ai-agent
```

### Locally

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...

# Run all 5 tests
python tests/run_tests.py

# Run a single task
python main.py "What is sqrt(2) + 3^4?"

# Interactive mode
python main.py
```

---

## Test Suite

5 tasks are run automatically:

| # | Task | Type |
|---|------|------|
| 1 | Multi-step math | Normal |
| 2 | Sieve of Eratosthenes code | Normal |
| 3 | Speed of light fact | Normal |
| 4 | Search for a non-existent document forever | **Adversarial — loop trap** |
| 5 | Impossibly broad research task | **Adversarial — budget trap** |

### Adversarial Task Outcomes

**Task 4 (loop trap):** The agent searches for a nonsense document (`xkqzjw19283 ultra secret classified document`). After finding no results and being instructed to "keep searching", the loop detector fires within 2 identical calls and forces a strategy change. The agent explains it cannot find the document and terminates.

**Task 5 (budget trap):** An absurdly broad task is given that would normally require 30+ calls. The agent completes what it can within the 10-call budget, then stops and explains what it finished vs. what remained.

---

## Why ReAct?

See `decisions.md` for the full rationale. Short version: ReAct gives us the explicit reasoning trace we need to implement reflection without a complex multi-agent scaffold.

---

## What Failed / Limitations

- **DuckDuckGo Instant Answers** is limited to encyclopaedia-style facts. For current news or niche queries it often returns empty results, which the agent handles by switching to `execute_code` or `calculator`.
- The **10-call limit** means multi-step research tasks will always be incomplete. The agent documents this honestly.
- The **cost model** is an estimate based on published token prices; actual invoiced amounts may differ slightly.

---

## Future Improvements

1. **Tool registry expansion** — add file I/O, email, or database tools.
2. **Memory / scratchpad** — persist intermediate findings across steps without burning tokens re-explaining context.
3. **Hierarchical planning** — have the agent break big tasks into sub-tasks with sub-budgets.
4. **Streaming UI** — real-time display of thoughts and observations.
5. **Smarter cost estimation** — query the API for real-time pricing via billing endpoint.
