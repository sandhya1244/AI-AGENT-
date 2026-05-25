# Engineering Decisions

## ADR-001: Planning Method — ReAct vs. Others

**Considered:** AutoGPT, BabyAGI, LangChain Agents, plain chain-of-thought, ReAct.

**Chosen:** ReAct (Reason + Act, Yao et al. 2022)

**Why:**
- Produces an explicit *reasoning trace* (`thought` + `reflection` fields) without additional infrastructure.
- Each step is a single LLM call, making call-counting trivial.
- No framework dependency — pure Python, minimal surface area.
- The `reflection` field is native to the prompt, not bolted on, which makes loop detection straightforward.

AutoGPT and BabyAGI both spawn multiple agents and do recursive planning, which would burn through a 10-call budget in seconds.

---

## ADR-002: Budget Enforcement — Pre-call vs. Post-call Check

**Considered:**
- Check budget *after* the call and abort the response.
- Check budget *before* the call and refuse to proceed.

**Chosen:** Pre-call check.

**Why:** Checking after the call still costs money and burns a call slot. By checking beforehand we guarantee we never exceed the stated limits, not just rarely exceed them.

---

## ADR-003: Web Search — SerpAPI vs. DuckDuckGo vs. Brave

**Considered:** SerpAPI (paid), Brave Search API (free tier), DuckDuckGo Instant Answer API (free, no key).

**Chosen:** DuckDuckGo Instant Answer API.

**Why:**
- Zero API key requirement removes onboarding friction for anyone running the project.
- Sufficient for encyclopaedic and factual questions that are the agent's primary workload.
- The agent's reflection mechanism compensates for weak results by switching to `execute_code` or `calculator`.

Trade-off: DuckDuckGo IA is limited for current events / news. Documented in README.

---

## ADR-004: Code Execution — Docker Sandbox vs. Subprocess vs. e2b

**Considered:** Running code inside a Docker container per call, using the `e2b` hosted sandbox API, plain `subprocess` with a timeout.

**Chosen:** `subprocess` with a 10-second timeout.

**Why:**
- Docker-per-call adds latency and complexity incompatible with a 10-call budget.
- `e2b` is a paid service, contradicting the zero-key philosophy for local dev.
- Subprocess with a timeout is simple, auditable, and sufficient for the test tasks.

Security note: Production deployments should use a proper sandbox. The subprocess approach is acceptable for a controlled demo environment.

---

## ADR-005: Calculator — `eval()` vs. AST-based evaluator vs. SymPy

**Considered:** Direct `eval()`, `sympy.sympify`, custom AST walker.

**Chosen:** Custom AST walker (`_safe_eval` in `tools.py`).

**Why:**
- `eval()` is a security hole; never use on untrusted input.
- `sympy` is a large dependency for what is essentially arithmetic.
- A whitelist-based AST walker is ~30 lines, zero dependencies, and provably safe within the whitelist.

---

## ADR-006: Loop Detection — External Classifier vs. Input-hashing vs. Simple Equality

**Considered:**
- Sending tool history to a second LLM to classify "stuck" state.
- Hashing tool inputs and tracking frequencies.
- Simple equality check on (action, action_input) pairs.

**Chosen:** Simple equality check.

**Why:**
- A second LLM classifier burns 2 call slots out of 10 just for meta-reasoning.
- For the target failure mode (agent searches for the same thing repeatedly), exact equality is 100% accurate.
- The adversarial test confirms this is sufficient.

---

## ADR-007: Response Format — Function Calling vs. JSON in Text vs. XML Tags

**Considered:** Anthropic tool-use / function-calling API, raw JSON in text, XML tags.

**Chosen:** JSON in text with a strict system prompt schema.

**Why:**
- Function-calling adds an extra round-trip (tool result injection) which complicates call counting.
- JSON in text is parsed once per step; a simple `json.loads` with a fallback handles edge cases.
- The agent needs to output both a *decision* (which tool) and a *reasoning trace* (thought + reflection) in the same response; JSON in text handles this cleanly in one object.
