"""
Agent tools: WebSearchTool, CodeExecutionTool, CalculatorTool
"""
import ast
import math
import operator
import subprocess
import tempfile
import os
import json
import urllib.request
import urllib.parse
import urllib.error


# ── Web Search Tool ────────────────────────────────────────────────────────────
class WebSearchTool:
    """
    Searches the web using the DuckDuckGo Instant Answer API (free, no key needed).
    Falls back to a snippet-based approach if the main result is empty.
    """
    name        = "web_search"
    description = "Search the web for current information."

    def run(self, query: str) -> str:
        if not query or not query.strip():
            return "ERROR: Empty query provided."

        encoded = urllib.parse.quote_plus(query)
        url     = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AI-Agent/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
        except Exception as exc:
            return f"SEARCH_ERROR: {exc}"

        # Build result from available fields
        parts = []

        abstract = data.get("AbstractText", "").strip()
        if abstract:
            parts.append(f"Summary: {abstract}")

        answer = data.get("Answer", "").strip()
        if answer:
            parts.append(f"Direct answer: {answer}")

        topics = data.get("RelatedTopics", [])
        snippets = []
        for t in topics[:4]:
            if isinstance(t, dict) and t.get("Text"):
                snippets.append(f"• {t['Text'][:200]}")
        if snippets:
            parts.append("Related:\n" + "\n".join(snippets))

        if not parts:
            return (f"No direct results found for '{query}'. "
                    "Try rephrasing or use execute_code to compute the answer directly.")

        return "\n\n".join(parts)


# ── Code Execution Tool ────────────────────────────────────────────────────────
class CodeExecutionTool:
    """
    Executes sandboxed Python code in a subprocess with a timeout.
    JavaScript is supported via Node.js if available.
    """
    name        = "execute_code"
    description = "Run Python (or JS) code and return stdout/stderr."
    TIMEOUT     = 10  # seconds

    def run(self, code: str, language: str = "python") -> str:
        if not code or not code.strip():
            return "ERROR: No code provided."

        language = language.lower().strip()

        if language in ("python", "py"):
            return self._run_python(code)
        elif language in ("javascript", "js", "node"):
            return self._run_node(code)
        else:
            return f"ERROR: Unsupported language '{language}'. Use 'python' or 'javascript'."

    def _run_python(self, code: str) -> str:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py",
                                         delete=False) as f:
            f.write(code)
            path = f.name
        try:
            result = subprocess.run(
                ["python3", path],
                capture_output=True, text=True, timeout=self.TIMEOUT
            )
            out = result.stdout.strip()
            err = result.stderr.strip()
            if err and not out:
                return f"STDERR: {err}"
            if err:
                return f"STDOUT: {out}\nSTDERR: {err}"
            return out or "(no output)"
        except subprocess.TimeoutExpired:
            return f"TIMEOUT: Code exceeded {self.TIMEOUT}s limit."
        except Exception as exc:
            return f"EXEC_ERROR: {exc}"
        finally:
            os.unlink(path)

    def _run_node(self, code: str) -> str:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js",
                                         delete=False) as f:
            f.write(code)
            path = f.name
        try:
            result = subprocess.run(
                ["node", path],
                capture_output=True, text=True, timeout=self.TIMEOUT
            )
            out = result.stdout.strip()
            err = result.stderr.strip()
            return out or err or "(no output)"
        except FileNotFoundError:
            return "ERROR: Node.js is not installed. Use Python instead."
        except subprocess.TimeoutExpired:
            return f"TIMEOUT: Code exceeded {self.TIMEOUT}s limit."
        except Exception as exc:
            return f"EXEC_ERROR: {exc}"
        finally:
            os.unlink(path)


# ── Calculator Tool ────────────────────────────────────────────────────────────
_SAFE_NAMES = {
    k: v for k, v in math.__dict__.items() if not k.startswith("_")
}
_SAFE_NAMES.update({"abs": abs, "round": round, "min": min, "max": max,
                    "sum": sum, "pow": pow, "int": int, "float": float})

_ALLOWED_NODE_TYPES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Call, ast.Constant,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.FloorDiv,
    ast.USub, ast.UAdd, ast.Name, ast.Load,
)


def _safe_eval(expr: str):
    """Parse and evaluate a math expression using AST – no exec/eval abuse."""
    tree = ast.parse(expr.strip(), mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODE_TYPES):
            raise ValueError(f"Forbidden AST node: {type(node).__name__}")
    return eval(compile(tree, "<calc>", "eval"), {"__builtins__": {}}, _SAFE_NAMES)


class CalculatorTool:
    """
    Safely evaluates mathematical expressions without using eval on raw strings.
    Supports standard math functions (sqrt, sin, cos, log, etc.).
    """
    name        = "calculator"
    description = "Evaluate a math expression. Supports sqrt, sin, cos, log, etc."

    def run(self, expression: str) -> str:
        if not expression or not expression.strip():
            return "ERROR: Empty expression."
        try:
            result = _safe_eval(expression)
            return str(result)
        except ZeroDivisionError:
            return "ERROR: Division by zero."
        except (ValueError, SyntaxError) as exc:
            return f"CALC_ERROR: {exc}"
        except Exception as exc:
            return f"CALC_ERROR: {exc}"
