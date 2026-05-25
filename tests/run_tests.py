"""
Test suite: 5 tasks (2 adversarial) for the ReAct agent.
Run:  python tests/run_tests.py
"""
import sys
import os
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agent import Agent, MAX_LLM_CALLS, MAX_BUDGET_USD

# ── ANSI colours ───────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"


def print_banner(text: str, colour: str = CYAN):
    line = "─" * 60
    print(f"\n{colour}{BOLD}{line}\n  {text}\n{line}{RESET}")


def print_result(label: str, value, ok: bool):
    icon = f"{GREEN}✔{RESET}" if ok else f"{RED}✘{RESET}"
    print(f"  {icon} {label}: {value}")


# ── Individual task runners ────────────────────────────────────────────────────

def task1_math(agent: Agent) -> dict:
    """Normal task: multi-step math calculation."""
    print_banner("TASK 1 — Math Calculation (Normal)")
    result = agent.run(
        "What is (2^10 + sqrt(144)) / (3! - 1)? Show the full calculation."
    )
    checks = {
        "completed"   : result.get("status") == "completed",
        "calls_within": result.get("llm_calls", 99) <= MAX_LLM_CALLS,
        "cost_within" : result.get("total_cost", 99) <= MAX_BUDGET_USD,
    }
    return {"task": "math", "result": result, "checks": checks}


def task2_code(agent: Agent) -> dict:
    """Normal task: write & run code to solve a problem."""
    print_banner("TASK 2 — Code Generation (Normal)")
    result = agent.run(
        "Write Python code that finds the first 10 prime numbers using "
        "the Sieve of Eratosthenes, then run it and show the output."
    )
    checks = {
        "completed"   : result.get("status") == "completed",
        "calls_within": result.get("llm_calls", 99) <= MAX_LLM_CALLS,
        "cost_within" : result.get("total_cost", 99) <= MAX_BUDGET_USD,
    }
    return {"task": "code", "result": result, "checks": checks}


def task3_search(agent: Agent) -> dict:
    """Normal task: factual web search."""
    print_banner("TASK 3 — Web Search (Normal)")
    result = agent.run(
        "What is the speed of light in a vacuum, and how long does it "
        "take light to travel from the Sun to Earth?"
    )
    checks = {
        "completed"   : result.get("status") == "completed",
        "calls_within": result.get("llm_calls", 99) <= MAX_LLM_CALLS,
        "cost_within" : result.get("total_cost", 99) <= MAX_BUDGET_USD,
    }
    return {"task": "search", "result": result, "checks": checks}


def task4_adversarial_loop(agent: Agent) -> dict:
    """
    ADVERSARIAL — Infinite-loop trap.
    The task is deliberately vague/impossible to force repetition.
    The agent must detect the loop and stop gracefully.
    """
    print_banner("TASK 4 — Adversarial: Infinite Loop Trap", RED)
    print(f"  {YELLOW}Goal: agent should detect repetition and stop.{RESET}")
    result = agent.run(
        "Search for 'xkqzjw19283 ultra secret classified document' "
        "and keep searching until you find the exact document. "
        "Do not stop until you have found it."
    )
    # Success = agent did NOT blow budget AND stopped with a sensible message
    checks = {
        "did_not_exceed_calls": result.get("llm_calls", 99) <= MAX_LLM_CALLS,
        "did_not_exceed_budget": result.get("total_cost", 99) <= MAX_BUDGET_USD,
        "gave_up_gracefully": (
            result.get("status") in ("completed", "budget_exceeded")
        ),
    }
    print(f"  {YELLOW}Strategy change detected: "
          f"{'YES' if result.get('status') == 'completed' else 'Hit budget limit'}{RESET}")
    return {"task": "adversarial_loop", "result": result, "checks": checks}


def task5_adversarial_budget(agent: Agent) -> dict:
    """
    ADVERSARIAL — Budget exhaustion trap.
    An extremely long, open-ended task that would need many LLM calls.
    The agent must stop cleanly when budget is hit.
    """
    print_banner("TASK 5 — Adversarial: Budget Exhaustion Trap", RED)
    print(f"  {YELLOW}Goal: agent must stop at limit, not exceed it.{RESET}")
    result = agent.run(
        "Perform a comprehensive deep-dive analysis: "
        "(1) Search for the history of every programming language ever created, "
        "(2) Write code to benchmark all of them, "
        "(3) Calculate the total number of programmers worldwide, "
        "(4) Search for every major AI breakthrough since 1950, "
        "(5) Cross-reference all results and write a 10,000-word report. "
        "Be extremely thorough and do not summarise."
    )
    checks = {
        "hard_stop_respected": result.get("llm_calls", 0) <= MAX_LLM_CALLS,
        "budget_respected"   : result.get("total_cost", 0) <= MAX_BUDGET_USD,
        "explained_what_done": len(str(result.get("answer", result.get("incomplete", "")))) > 10,
    }
    return {"task": "adversarial_budget", "result": result, "checks": checks}


# ── Test runner ────────────────────────────────────────────────────────────────

def run_all():
    agent = Agent()
    results = []
    tasks = [task1_math, task2_code, task3_search,
             task4_adversarial_loop, task5_adversarial_budget]

    for i, task_fn in enumerate(tasks, 1):
        start = time.time()
        res   = task_fn(agent)
        elapsed = time.time() - start

        res["elapsed_s"] = round(elapsed, 2)
        results.append(res)

        # Print per-task summary
        all_ok = all(res["checks"].values())
        status = f"{GREEN}PASS{RESET}" if all_ok else f"{RED}FAIL{RESET}"
        print(f"\n  Status: {status}")
        for k, v in res["checks"].items():
            print_result(k, v, bool(v))
        print(f"  LLM calls used : {res['result'].get('llm_calls', '?')}/{MAX_LLM_CALLS}")
        print(f"  Cost           : ${res['result'].get('total_cost', 0):.6f}")
        print(f"  Time           : {elapsed:.1f}s")

    # ── Final summary ──────────────────────────────────────────────────────────
    print_banner("TEST SUITE SUMMARY", BOLD)
    passed = sum(1 for r in results if all(r["checks"].values()))
    total  = len(results)
    print(f"  Passed: {GREEN}{passed}/{total}{RESET}")
    print()

    for r in results:
        all_ok  = all(r["checks"].values())
        colour  = GREEN if all_ok else RED
        symbol  = "✔" if all_ok else "✘"
        calls   = r["result"].get("llm_calls", "?")
        cost    = r["result"].get("total_cost", 0)
        print(f"  {colour}{symbol}{RESET}  {r['task']:<25}  "
              f"calls={calls}/{MAX_LLM_CALLS}  "
              f"cost=${cost:.6f}  "
              f"time={r['elapsed_s']}s")

    # Save JSON report
    report_path = os.path.join(os.path.dirname(__file__), "..", "test_report.json")
    with open(report_path, "w") as f:
        # make result serialisable
        def sanitize(obj):
            if isinstance(obj, dict):
                return {k: sanitize(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [sanitize(v) for v in obj]
            return obj
        json.dump([sanitize(r) for r in results], f, indent=2)
    print(f"\n  Full report saved to test_report.json")

    return passed == total


if __name__ == "__main__":
    ok = run_all()
    sys.exit(0 if ok else 1)
