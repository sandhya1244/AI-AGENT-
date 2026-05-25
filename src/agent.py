"""
ReAct Agent - uses Ollama (100% free, runs locally)
No API key needed. Just install Ollama and pull a model.
"""
import os
import sys
import json
import urllib.request

_src_dir = os.path.dirname(os.path.abspath(__file__))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

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

from tools import WebSearchTool, CodeExecutionTool, CalculatorTool

# ── Config ─────────────────────────────────────────────────────────────────────
OLLAMA_URL   = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")  # change if you pulled a different model

MAX_LLM_CALLS         = 10
MAX_BUDGET_USD        = 0.20  # kept for structure; Ollama is always free
COST_PER_INPUT_TOKEN  = 0.0
COST_PER_OUTPUT_TOKEN = 0.0

SYSTEM_PROMPT = """You are a ReAct-style AI agent. Solve tasks step by step.

Each turn you must output ONLY a single valid JSON object — no prose, no markdown fences, nothing else.

Format:
{
  "thought": "what I am thinking",
  "reflection": "did the last step help? should I change approach?",
  "action": "web_search" or "execute_code" or "calculator" or "final_answer",
  "action_input": {},
  "answer": "only fill this when action is final_answer"
}

Available tools:
- web_search      : {"query": "search terms"}
- execute_code    : {"code": "python code here", "language": "python"}
- calculator      : {"expression": "2**10 + sqrt(144)"}
- final_answer    : {"answer": "your complete answer"}  -- use this when done

Rules:
- Output ONLY the JSON. No text before or after it.
- Never repeat the exact same action+input twice in a row.
- If a tool returns an error, try a different approach.
- When you have enough information, use final_answer immediately.
"""


def _call_ollama(messages: list) -> str:
    """Call local Ollama API."""
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 1024,
        }
    }).encode()

    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode())
        return data["message"]["content"]
    except urllib.error.URLError:
        raise ConnectionError(
            f"Cannot connect to Ollama at {OLLAMA_URL}. "
            "Make sure Ollama is running (open a terminal and run: ollama serve)"
        )


def _extract_json(raw: str) -> dict:
    """Try hard to extract a JSON object from the model's response."""
    raw = raw.strip()

    # Remove markdown fences
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:]).rstrip("`").strip()

    # Direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Find first { ... } block
    start = raw.find("{")
    end   = raw.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(raw[start:end+1])
        except json.JSONDecodeError:
            pass

    # Fallback — treat entire response as final answer
    return {
        "thought": "Could not parse JSON from model response",
        "reflection": "Returning raw text as final answer",
        "action": "final_answer",
        "action_input": {},
        "answer": raw,
    }


class Agent:
    def __init__(self):
        self.tools = {
            "web_search":   WebSearchTool(),
            "execute_code": CodeExecutionTool(),
            "calculator":   CalculatorTool(),
        }
        self.reset()

    def reset(self):
        self.llm_calls            = 0
        self.total_cost           = 0.0
        self.history              = []
        self.action_log           = []
        self.last_action          = None
        self.last_action_input    = None
        self.consecutive_failures = 0

    def _check_budget(self):
        if self.llm_calls >= MAX_LLM_CALLS:
            return False, f"LLM call limit reached ({MAX_LLM_CALLS})"
        return True, "ok"

    def _call_llm(self, user_message: str) -> dict:
        ok, reason = self._check_budget()
        if not ok:
            raise RuntimeError(f"BUDGET_EXCEEDED: {reason}")
        self.history.append({"role": "user", "content": user_message})
        self.llm_calls += 1
        raw = _call_ollama(self.history)
        self.history.append({"role": "assistant", "content": raw})
        return _extract_json(raw)

    def _detect_loop(self, action, action_input):
        return (action == self.last_action and
                json.dumps(action_input, sort_keys=True) ==
                json.dumps(self.last_action_input or {}, sort_keys=True))

    def run(self, task: str) -> dict:
        self.reset()
        print(f"\n{'='*60}")
        print(f"TASK: {task}")
        print(f"MODEL: {OLLAMA_MODEL} (local Ollama)")
        print(f"{'='*60}")

        step_input = f"Task: {task}\n\nPlan your approach and begin."
        step = 0

        while True:
            step += 1
            ok, reason = self._check_budget()
            if not ok:
                print(f"\n⛔ {reason}")
                return self._budget_summary(reason)

            try:
                decision = self._call_llm(step_input)
            except RuntimeError as exc:
                return self._budget_summary(str(exc))
            except ConnectionError as exc:
                print(f"\n❌ {exc}")
                return self._budget_summary(str(exc))
            except Exception as exc:
                return self._budget_summary(f"Unexpected error: {exc}")

            action       = decision.get("action", "final_answer")
            action_input = decision.get("action_input", {})
            thought      = decision.get("thought", "")
            reflection   = decision.get("reflection", "")

            print(f"\n[Step {step}] Calls: {self.llm_calls}/{MAX_LLM_CALLS}")
            print(f"  THINK  : {thought}")
            print(f"  REFLECT: {reflection}")
            print(f"  ACTION : {action} <- {json.dumps(action_input)}")

            # Loop detection
            if self._detect_loop(action, action_input):
                self.consecutive_failures += 1
                print(f"  ⚠ Repetition detected! (x{self.consecutive_failures})")
                if self.consecutive_failures >= 2:
                    step_input = (
                        "You are repeating the same action with the same input. "
                        "This is not making progress. You MUST either switch to a "
                        "completely different tool, or output final_answer with what "
                        "you already know."
                    )
                    self.last_action = None
                    continue
            else:
                self.consecutive_failures = 0

            self.last_action       = action
            self.last_action_input = action_input

            # Final answer
            if action == "final_answer":
                answer = decision.get("answer", "") or decision.get("action_input", {}).get("answer", "No answer.")
                print(f"\n✅ FINAL ANSWER:\n{answer}")
                self.action_log.append({"step": step, "action": "final_answer", "result": answer})
                return {
                    "task": task, "answer": answer,
                    "llm_calls": self.llm_calls,
                    "total_cost": 0.0,
                    "steps": self.action_log,
                    "status": "completed",
                }

            # Run tool
            tool = self.tools.get(action)
            if tool is None:
                observation = f"ERROR: Unknown tool '{action}'. Use web_search, execute_code, or calculator."
            else:
                try:
                    observation = tool.run(**action_input)
                except TypeError as exc:
                    observation = f"TOOL_ERROR (wrong arguments): {exc}"
                except Exception as exc:
                    observation = f"TOOL_ERROR: {exc}"

            print(f"  OBSERVE: {str(observation)[:300]}")
            self.action_log.append({
                "step": step,
                "action": action,
                "action_input": action_input,
                "observation": str(observation)[:500],
            })
            step_input = (
                f"Observation from {action}:\n{observation}\n\n"
                f"Continue. Remember to output ONLY valid JSON."
            )

    def _budget_summary(self, reason: str) -> dict:
        return {
            "status": "budget_exceeded", "reason": reason,
            "llm_calls": self.llm_calls, "total_cost": 0.0,
            "steps": self.action_log,
            "answer": f"Stopped: {reason}. Completed {len(self.action_log)} steps.",
            "incomplete": "Task not fully completed.",
        }