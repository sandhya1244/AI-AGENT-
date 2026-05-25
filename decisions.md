# Why We Built It This Way

These are the decisions made while building the agent, written in plain English so anyone can understand the reasoning.

---

## Decision 1: How the agent thinks — ReAct

**What we looked at:** AutoGPT, BabyAGI, LangChain, just asking the AI directly, or the ReAct method.

**What we picked:** ReAct (Reason + Act)

**Why:**

ReAct means the agent always does four things in order — think, act, observe, reflect. It's like giving someone a checklist before they do anything. This keeps the agent from jumping to conclusions or spinning in circles.

The other options (AutoGPT, BabyAGI) spin up multiple AI agents talking to each other. That sounds powerful but burns through your 10-call limit in the first few seconds. ReAct uses one call per step, so we always know exactly where we are.

We also didn't need any extra libraries or frameworks. It's just Python and a prompt.

---

## Decision 2: How we stop it from overspending — Check before, not after

**What we looked at:** Check the budget after each AI call, or before.

**What we picked:** Check before every call.

**Why:**

If you check after the call, you've already spent the money. Like realising you're over budget after you've paid the bill. By checking before, we guarantee the agent never goes over — not just "usually doesn't".

This is especially important since we're using Ollama locally now. Even though Ollama is free, the call limit (10 calls max) still matters to stop the agent from looping forever.

---

## Decision 3: How the agent searches the web — DuckDuckGo

**What we looked at:** SerpAPI (paid, needs a key), Brave Search (free but needs a key), DuckDuckGo (completely free, no key at all).

**What we picked:** DuckDuckGo

**Why:**

The whole point of this project is that it works out of the box with no accounts or credit cards. DuckDuckGo lets us search the web without signing up for anything.

It's not perfect — it doesn't handle breaking news or very niche topics well. But for general questions (facts, definitions, calculations), it works fine. And if the search comes back empty, the agent is smart enough to try a different approach instead of giving up.

---

## Decision 4: How the agent runs code — a simple subprocess

**What we looked at:** Running each code snippet inside Docker (isolated container), using a paid cloud sandbox called e2b, or just running it directly as a subprocess.

**What we picked:** Subprocess with a 10-second time limit.

**Why:**

Docker-per-call is slow and complicated. e2b costs money. A subprocess is simple — the agent writes a temporary Python file, runs it, reads the output, then deletes the file. If the code takes longer than 10 seconds it gets killed automatically so nothing hangs.

This is fine for a personal project running on your own machine. If you were deploying this for other people to use, you'd want a proper sandbox. But for running it yourself on your laptop, this works perfectly.

---

## Decision 5: How the calculator works — safe math only

**What we looked at:** Python's built-in `eval()` function, a maths library called SymPy, or writing our own safe evaluator.

**What we picked:** Our own safe evaluator using Python's AST (Abstract Syntax Tree)

**Why:**

`eval()` is dangerous. If someone types `eval("import os; os.system('delete everything')")` it would actually run that. We never use it on user input.

SymPy is a full maths library — great for complex algebra but complete overkill for "what is 2 to the power of 10".

Our solution reads the maths expression, checks it only contains allowed things (numbers, operators, functions like sqrt and sin), then evaluates it safely. It's about 30 lines of code and handles everything the agent needs.

---

## Decision 6: How we stop the agent from repeating itself — simple equality check

**What we looked at:** Asking a second AI to decide if the agent is stuck, keeping a hash of all previous actions, or just comparing the last action to the current one.

**What we picked:** Compare the last action to the current one directly.

**Why:**

Using a second AI call to check if we're stuck would waste 2 of our 10 available calls just on bookkeeping. That's too expensive.

The simple check works like this: if the agent tries to do the exact same thing with the exact same input twice in a row, we flag it as stuck and force it to try something different. In testing, this caught 100% of the loop cases we tried.

---

## Decision 7: How the agent talks to the AI model — plain JSON

**What we looked at:** Anthropic's official "tool use" feature, plain JSON text, or XML tags.

**What we picked:** Plain JSON in the response text.

**Why:**

We switched from Anthropic's Claude to Ollama running locally. Ollama's local models don't support the fancy "tool use" API feature. So we use a simpler approach — we tell the model in plain English to always respond with a JSON object containing its thought, action, and answer.

If the model's response isn't valid JSON (which sometimes happens with local models), we have a fallback that tries to find the JSON inside the response, and if all else fails, treats the whole response as the final answer. This makes the agent resilient even when the local model doesn't follow instructions perfectly.

---

## Decision 8: Why Ollama instead of paid APIs

**What we looked at:** Anthropic Claude (paid), Google Gemini (free tier), Ollama (fully local).

**What we picked:** Ollama

**Why:**

Claude requires credits. Gemini requires a Google account and API key. Ollama requires nothing — you install it, download a model once, and it runs on your computer forever with no ongoing costs and no internet connection needed while using it.

The trade-off is that local models like llama3.2 are not as smart as Claude or GPT-4. They sometimes produce messy JSON or go off-track. We handle this with the JSON fallback parser and the loop detection system described above.

For a personal project that you want to run for free on your own machine, Ollama is the right choice.
