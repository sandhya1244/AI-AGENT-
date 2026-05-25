"""
ReAct-style AI Agent with budget enforcement, reflection, and 3 tools.
"""
import os
import sys
import json
import time
from typing import Any

# ── Ensure src/ is on sys.path so 'from tools import' always works ────────────
_src_dir = os.path.dirname(os.path.abspath(__file__))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

# ── Load .env from project root ───────────────────────────────────────────────
def _load_dotenv():
    env_path = os.path.abspath(os.path.join(_src_dir, "..", ".env"))
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    os.environ.setdefault(key.strip(), val.strip())

_load_dotenv()

from anthropic import Anthropic
from tools import WebSearchTool, CodeExecutionTool, CalculatorTool

# ── Budget constants ───────────────────────────────────────────────────────────
MAX_LLM_CALLS   = 10
MAX_BUDGET_USD  = 0.20

# claude-sonnet-4-20250514 pricing (per-token)
COST_PER_INPUT_TOKEN  = 3.00 / 1_000_000   # $3 / M input tokens
COST_PER_OUTPUT_TOKEN = 15.00 / 1_000_000  # $15 / M output tokens

SYSTEM_PROMPT = """You are a ReAct-style AI agent. You solve tasks by cycling through:

THINK  → reason about what to do next
ACT    → call ONE tool
OBSERVE→ read the result
REFLECT→ ask "Am I making progress? Should I change strategy?"

After each observation, EXPLICITLY reflect:
- Did the last action help?
- If the same approach failed twice, switch strategies immediately.
- If the task is solved, output FINAL_ANSWER.

Available tools:
1. web_search(query: str)         — search the web
2. execute_code(code: str, language: str)  — run Python or JS code
3. calculator(expression: str)    — evaluate math expressions safely

Respond ONLY in this JSON format:
{
  "thought": "...",
  "reflection": "...",
  "action": "web_search" | "execute_code" | "calculator" | "final_answer",
  "action_input": { ... },
  "answer": "..."   // only when action == "final_answer"
}

CRITICAL RULES:
- NEVER repeat a failed action with identical input.
- If a tool fails twice in a row, switch to a different tool or approach.
- If you cannot answer with remaining budget, say so in final_answer.
"""


class Agent:
    def __init__(self):
        self.client = Anthropic()
        self.tools  = {
            "web_search"   : WebSearchTool(),
            "execute_code" : CodeExecutionTool(),
            "calculator"   : CalculatorTool(),
        }
        self.reset()

    # ── State management ───────────────────────────────────────────────────────
    def reset(self):
        self.llm_calls             = 0
        self.total_cost            = 0.0
        self.history               = []
        self.action_log            = []
        self.last_action           = None
        self.last_action_input     = None
        self.consecutive_failures  = 0

    # ── Budget helpers ─────────────────────────────────────────────────────────
    def _check_budget(self) -> tuple:
        if self.llm_calls >= MAX_LLM_CALLS:
            return False, f"LLM call limit reached ({MAX_LLM_CALLS})"
        if self.total_cost >= MAX_BUDGET_USD:
            return False, f"Budget limit reached (${self.total_cost:.4f} >= ${MAX_BUDGET_USD})"
        return True, "ok"

    def _record_cost(self, usage):
        cost = (usage.input_tokens  * COST_PER_INPUT_TOKEN +
                usage.output_tokens * COST_PER_OUTPUT_TOKEN)
        self.total_cost += cost
        return cost

    # ── LLM call wrapper ───────────────────────────────────────────────────────
    def _call_llm(self, user_message: str) -> dict:
        ok, reason = self._check_budget()
        if not ok:
            raise RuntimeError(f"BUDGET_EXCEEDED: {reason}")

        self.history.append({"role": "user", "content": user_message})
        self.llm_calls += 1

        response = self.client.messages.create(
            model      = "claude-sonnet-4-20250514",
            max_tokens = 1024,
            system     = SYSTEM_PROMPT,
            messages   = self.history,
        )
        self._record_cost(response.usage)

        raw = response.content[0].text
        self.history.append({"role": "assistant", "content": raw})

        try:
            clean = raw.strip()
            if clean.startswith("```"):
                clean = "\n".join(clean.split("\n")[1:])
                clean = clean.rstrip("`").strip()
            parsed = json.loads(clean)
        except json.JSONDecodeError:
            parsed = {
                "thought"    : "Could not parse response",
                "reflection" : "parse error",
                "action"     : "final_answer",
                "action_input": {},
                "answer"     : raw,
            }
        return parsed

    # ── Loop / repetition detection ────────────────────────────────────────────
    def _detect_loop(self, action: str, action_input: dict) -> bool:
        return (action == self.last_action and
                json.dumps(action_input, sort_keys=True) ==
                json.dumps(self.last_action_input or {}, sort_keys=True))

    # ── Main run loop ──────────────────────────────────────────────────────────
    def run(self, task: str) -> dict:
        self.reset()
        print(f"\n{'='*60}")
        print(f"TASK: {task}")
        print(f"{'='*60}")

        step_input = f"Task: {task}\n\nBegin by planning your approach."
        step = 0

        while True:
            step += 1
            ok, reason = self._check_budget()
            if not ok:
                summary = self._budget_summary(reason)
                print(f"\n⛔ {reason}")
                return summary

            try:
                decision = self._call_llm(step_input)
            except RuntimeError as exc:
                return self._budget_summary(str(exc))

            action       = decision.get("action", "final_answer")
            action_input = decision.get("action_input", {})
            thought      = decision.get("thought", "")
            reflection   = decision.get("reflection", "")

            print(f"\n[Step {step}] Calls: {self.llm_calls}/{MAX_LLM_CALLS}  "
                  f"Cost: ${self.total_cost:.4f}/${MAX_BUDGET_USD}")
            print(f"  THINK  : {thought}")
            print(f"  REFLECT: {reflection}")
            print(f"  ACTION : {action} ← {json.dumps(action_input)}")

            # ── Loop detection ─────────────────────────────────────────────────
            if self._detect_loop(action, action_input):
                self.consecutive_failures += 1
                print(f"  ⚠  Repetition detected! (×{self.consecutive_failures})")
                if self.consecutive_failures >= 2:
                    step_input = (
                        "You are repeating the same action with the same input. "
                        "This is NOT making progress. You MUST switch to a completely "
                        "different tool or approach, or provide a final_answer with "
                        "what you know so far."
                    )
                    self.last_action = None
                    continue
            else:
                self.consecutive_failures = 0

            self.last_action       = action
            self.last_action_input = action_input

            # ── Final answer ───────────────────────────────────────────────────
            if action == "final_answer":
                answer = decision.get("answer", "No answer provided.")
                print(f"\n✅ FINAL ANSWER:\n{answer}")
                self.action_log.append({"step": step, "action": "final_answer",
                                        "result": answer})
                return {
                    "task"      : task,
                    "answer"    : answer,
                    "llm_calls" : self.llm_calls,
                    "total_cost": round(self.total_cost, 6),
                    "steps"     : self.action_log,
                    "status"    : "completed",
                }

            # ── Tool execution ─────────────────────────────────────────────────
            tool = self.tools.get(action)
            if tool is None:
                observation = f"ERROR: Unknown tool '{action}'. Available: web_search, execute_code, calculator."
            else:
                try:
                    observation = tool.run(**action_input)
                except Exception as exc:
                    observation = f"TOOL_ERROR: {exc}"

            print(f"  OBSERVE: {str(observation)[:300]}")
            self.action_log.append({
                "step"        : step,
                "action"      : action,
                "action_input": action_input,
                "observation" : str(observation)[:500],
            })

            step_input = f"Observation from {action}:\n{observation}\n\nContinue."

    # ── Budget summary ─────────────────────────────────────────────────────────
    def _budget_summary(self, reason: str) -> dict:
        return {
            "status"         : "budget_exceeded",
            "reason"         : reason,
            "llm_calls"      : self.llm_calls,
            "total_cost"     : round(self.total_cost, 6),
            "steps"          : self.action_log,
            "incomplete"     : "Task was not fully completed due to budget limits.",
            "answer"         : f"Stopped: {reason}. Completed {len(self.action_log)} steps.",
        }
