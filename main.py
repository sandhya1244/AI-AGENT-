#!/usr/bin/env python3
"""
CLI entry-point: run the agent on a single task.
Usage:
    python main.py "What is the square root of 144?"
    python main.py  (interactive mode)
"""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from agent import Agent


def main():
    agent = Agent()

    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
        result = agent.run(task)
        print("\n" + "=" * 60)
        print("RESULT JSON:")
        print(json.dumps(result, indent=2))
    else:
        print("AI Agent — Interactive Mode")
        print("Type 'quit' to exit.\n")
        while True:
            try:
                task = input("Task > ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if task.lower() in ("quit", "exit", "q"):
                break
            if not task:
                continue
            result = agent.run(task)
            print("\nRESULT:")
            print(json.dumps(result, indent=2))
            print()


if __name__ == "__main__":
    main()
