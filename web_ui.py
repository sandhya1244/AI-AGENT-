"""
Web UI for the ReAct Agent.
Run:  python web_ui.py
Then open: http://localhost:5000
"""
import os
import sys
import json
import threading

_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if _src not in sys.path:
    sys.path.insert(0, _src)
_root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)

# Load .env
def _load_dotenv():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    os.environ.setdefault(key.strip(), val.strip())
_load_dotenv()

from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import html

# ── Simple streaming agent wrapper ──────────────────────────────────────────
from agent import Agent, MAX_LLM_CALLS, MAX_BUDGET_USD

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ReAct AI Agent</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #0f1117; --bg2: #1a1d27; --bg3: #252836;
    --border: rgba(255,255,255,0.08);
    --text: #e8e9f0; --muted: #8b8fa8; --accent: #6366f1;
    --green: #22c55e; --amber: #f59e0b; --red: #ef4444;
    --blue: #3b82f6; --purple: #a855f7;
    --radius: 10px;
  }
  body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', system-ui, sans-serif; min-height: 100vh; display: flex; flex-direction: column; }
  header { padding: 1.25rem 2rem; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 12px; }
  header .logo { width: 32px; height: 32px; border-radius: 8px; background: var(--accent); display: flex; align-items: center; justify-content: center; font-size: 16px; }
  header h1 { font-size: 17px; font-weight: 600; }
  header span { font-size: 12px; color: var(--muted); }
  .limits { margin-left: auto; display: flex; gap: 16px; font-size: 12px; color: var(--muted); }
  .limits b { color: var(--text); }
  .main { display: flex; flex: 1; overflow: hidden; max-height: calc(100vh - 61px); }
  .sidebar { width: 260px; border-right: 1px solid var(--border); padding: 1.25rem; display: flex; flex-direction: column; gap: 1rem; overflow-y: auto; flex-shrink: 0; }
  .sidebar h3 { font-size: 11px; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); margin-bottom: 8px; }
  .budget-block { background: var(--bg2); border-radius: var(--radius); padding: 12px; }
  .b-row { margin-bottom: 10px; }
  .b-row:last-child { margin-bottom: 0; }
  .b-label { display: flex; justify-content: space-between; font-size: 12px; color: var(--muted); margin-bottom: 5px; }
  .b-label span:last-child { color: var(--text); font-weight: 500; }
  .b-track { height: 6px; background: var(--bg3); border-radius: 3px; overflow: hidden; }
  .b-fill { height: 100%; border-radius: 3px; transition: width .3s ease; }
  .b-fill.calls { background: var(--blue); }
  .b-fill.cost  { background: var(--green); }
  .b-fill.warn  { background: var(--amber); }
  .b-fill.danger{ background: var(--red); }
  .tool-pill { display: flex; align-items: center; gap: 8px; padding: 7px 10px; border-radius: 7px; background: var(--bg2); font-size: 12px; cursor: default; }
  .tool-dot { width: 7px; height: 7px; border-radius: 50%; }
  .tool-dot.search { background: var(--blue); }
  .tool-dot.code   { background: var(--green); }
  .tool-dot.calc   { background: var(--amber); }
  .tool-name { font-weight: 500; }
  .tool-desc { color: var(--muted); margin-left: auto; font-size: 11px; }
  .sample-list { display: flex; flex-direction: column; gap: 5px; }
  .sample-btn { text-align: left; background: var(--bg2); border: 1px solid var(--border); border-radius: 7px; padding: 7px 10px; font-size: 12px; color: var(--muted); cursor: pointer; transition: all .15s; }
  .sample-btn:hover { border-color: var(--accent); color: var(--text); }
  .chat-area { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
  .messages { flex: 1; overflow-y: auto; padding: 1.5rem 2rem; display: flex; flex-direction: column; gap: 1rem; }
  .msg { display: flex; flex-direction: column; gap: 4px; max-width: 820px; }
  .msg.user { align-items: flex-end; align-self: flex-end; }
  .msg.agent { align-self: flex-start; }
  .msg-label { font-size: 11px; color: var(--muted); }
  .msg-bubble { padding: 10px 14px; border-radius: 10px; font-size: 14px; line-height: 1.6; }
  .msg.user .msg-bubble { background: var(--accent); color: #fff; border-bottom-right-radius: 3px; }
  .msg.agent .msg-bubble { background: var(--bg2); border: 1px solid var(--border); border-bottom-left-radius: 3px; white-space: pre-wrap; }
  .step-block { background: var(--bg3); border: 1px solid var(--border); border-radius: 8px; padding: 10px 12px; font-size: 12px; font-family: 'Cascadia Code', 'Fira Code', monospace; }
  .step-block .s-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
  .step-tag { padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; letter-spacing: .04em; }
  .tag-think   { background: rgba(99,102,241,.2); color: #a5b4fc; }
  .tag-act     { background: rgba(59,130,246,.2); color: #93c5fd; }
  .tag-observe { background: rgba(34,197,94,.2);  color: #86efac; }
  .tag-reflect { background: rgba(168,85,247,.2); color: #d8b4fe; }
  .tag-answer  { background: rgba(34,197,94,.2);  color: #86efac; }
  .tag-stop    { background: rgba(239,68,68,.2);  color: #fca5a5; }
  .s-text { color: var(--muted); line-height: 1.5; }
  .s-text b { color: var(--text); font-weight: 500; }
  .input-row { padding: 1rem 2rem; border-top: 1px solid var(--border); display: flex; gap: 10px; }
  .input-row textarea { flex: 1; background: var(--bg2); border: 1px solid var(--border); border-radius: var(--radius); padding: 10px 14px; color: var(--text); font-size: 14px; resize: none; height: 48px; font-family: inherit; outline: none; transition: border-color .15s; }
  .input-row textarea:focus { border-color: var(--accent); }
  .input-row textarea::placeholder { color: var(--muted); }
  .send-btn { width: 48px; height: 48px; border-radius: var(--radius); background: var(--accent); border: none; color: #fff; font-size: 18px; cursor: pointer; transition: opacity .15s; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
  .send-btn:hover { opacity: .85; }
  .send-btn:disabled { opacity: .4; cursor: default; }
  .empty-state { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; color: var(--muted); }
  .empty-state .icon { font-size: 40px; opacity: .3; }
  .empty-state p { font-size: 14px; }
  .thinking { display: flex; gap: 4px; align-items: center; padding: 10px 14px; background: var(--bg2); border: 1px solid var(--border); border-radius: 10px; border-bottom-left-radius: 3px; }
  .thinking span { width: 6px; height: 6px; border-radius: 50%; background: var(--muted); animation: bounce .9s infinite; }
  .thinking span:nth-child(2) { animation-delay: .15s; }
  .thinking span:nth-child(3) { animation-delay: .3s; }
  @keyframes bounce { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-5px)} }
  ::-webkit-scrollbar { width: 5px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
</style>
</head>
<body>
<header>
  <div class="logo">🤖</div>
  <h1>ReAct AI Agent</h1>
  <span>Budget-aware · Self-reflecting</span>
  <div class="limits">
    <div>Max calls <b>10</b></div>
    <div>Budget <b>$0.20</b></div>
  </div>
</header>

<div class="main">
  <div class="sidebar">
    <div>
      <h3>Budget tracker</h3>
      <div class="budget-block">
        <div class="b-row">
          <div class="b-label"><span>LLM calls</span><span id="calls-label">0 / 10</span></div>
          <div class="b-track"><div class="b-fill calls" id="bar-calls" style="width:0%"></div></div>
        </div>
        <div class="b-row">
          <div class="b-label"><span>Cost</span><span id="cost-label">$0.0000</span></div>
          <div class="b-track"><div class="b-fill cost" id="bar-cost" style="width:0%"></div></div>
        </div>
      </div>
    </div>

    <div>
      <h3>Tools available</h3>
      <div style="display:flex;flex-direction:column;gap:5px">
        <div class="tool-pill"><div class="tool-dot search"></div><span class="tool-name">web_search</span><span class="tool-desc">DuckDuckGo</span></div>
        <div class="tool-pill"><div class="tool-dot code"></div><span class="tool-name">execute_code</span><span class="tool-desc">Python/JS</span></div>
        <div class="tool-pill"><div class="tool-dot calc"></div><span class="tool-name">calculator</span><span class="tool-desc">Math AST</span></div>
      </div>
    </div>

    <div>
      <h3>Sample tasks</h3>
      <div class="sample-list">
        <button class="sample-btn" onclick="setTask('What is (2^10 + sqrt(144)) / (3! - 1)?')">Math: (2¹⁰+√144)/(3!-1)</button>
        <button class="sample-btn" onclick="setTask('Write Python code to find the first 10 prime numbers using Sieve of Eratosthenes and run it.')">Sieve of Eratosthenes</button>
        <button class="sample-btn" onclick="setTask('How long does light take to travel from Sun to Earth?')">Speed of light</button>
        <button class="sample-btn" onclick="setTask('Calculate compound interest: $1000 at 7% annually for 20 years.')">Compound interest</button>
        <button class="sample-btn" onclick="setTask('What is the Fibonacci sequence? Write code to print first 15 terms.')">Fibonacci code</button>
      </div>
    </div>
  </div>

  <div class="chat-area">
    <div class="messages" id="messages">
      <div class="empty-state" id="empty-state">
        <div class="icon">🧠</div>
        <p>Ask the agent anything. It will plan, act, and reflect.</p>
      </div>
    </div>
    <div class="input-row">
      <textarea id="task-input" placeholder="Enter a task… (Shift+Enter for new line, Enter to send)" rows="1"></textarea>
      <button class="send-btn" id="send-btn" onclick="sendTask()" title="Send">➤</button>
    </div>
  </div>
</div>

<script>
let running = false;

function setTask(t) {
  document.getElementById('task-input').value = t;
  document.getElementById('task-input').focus();
}

document.getElementById('task-input').addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendTask(); }
});

function updateBudget(calls, cost) {
  const pct = v => Math.min(v * 100, 100).toFixed(1);
  document.getElementById('calls-label').textContent = calls + ' / 10';
  document.getElementById('cost-label').textContent  = '$' + cost.toFixed(4);
  const bc = document.getElementById('bar-calls');
  const bx = document.getElementById('bar-cost');
  bc.style.width = pct(calls / 10) + '%';
  bx.style.width = pct(cost / 0.20) + '%';
  bc.className = 'b-fill calls' + (calls >= 8 ? ' danger' : calls >= 6 ? ' warn' : '');
  bx.className = 'b-fill cost'  + (cost >= 0.16 ? ' danger' : cost >= 0.12 ? ' warn' : '');
}

function appendMsg(role, content) {
  const empty = document.getElementById('empty-state');
  if (empty) empty.remove();
  const msgs = document.getElementById('messages');
  const div = document.createElement('div');
  div.className = 'msg ' + role;
  div.innerHTML = `<div class="msg-label">${role === 'user' ? 'You' : 'Agent'}</div>
    <div class="msg-bubble">${content}</div>`;
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
  return div;
}

function appendStep(tag, title, body) {
  const msgs = document.getElementById('messages');
  const div = document.createElement('div');
  div.className = 'msg agent';
  div.innerHTML = `<div class="step-block">
    <div class="s-header"><span class="step-tag tag-${tag}">${tag.toUpperCase()}</span><span style="font-size:12px;color:var(--muted)">${escHtml(title)}</span></div>
    <div class="s-text">${escHtml(body)}</div>
  </div>`;
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
}

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function showThinking() {
  const msgs = document.getElementById('messages');
  const div = document.createElement('div');
  div.className = 'msg agent';
  div.id = 'thinking-indicator';
  div.innerHTML = `<div class="thinking"><span></span><span></span><span></span></div>`;
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
}

function removeThinking() {
  const t = document.getElementById('thinking-indicator');
  if (t) t.remove();
}

async function sendTask() {
  if (running) return;
  const inp = document.getElementById('task-input');
  const task = inp.value.trim();
  if (!task) return;

  inp.value = '';
  running = true;
  document.getElementById('send-btn').disabled = true;

  appendMsg('user', escHtml(task));
  showThinking();

  try {
    const resp = await fetch('/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task })
    });
    const data = await resp.json();
    removeThinking();

    // Show each step
    if (data.steps) {
      for (const s of data.steps) {
        const action = s.action || '';
        const tag = action === 'final_answer' ? 'answer' : 'act';
        appendStep(tag, action, JSON.stringify(s.action_input || {}).slice(0,120) + (s.observation ? '\n→ ' + String(s.observation).slice(0,200) : ''));
      }
    }

    // Final answer / budget exceeded
    if (data.status === 'budget_exceeded') {
      appendMsg('agent', `⛔ <b>Budget limit reached</b>: ${escHtml(data.reason)}\n\nCompleted: ${escHtml(data.incomplete || 'partial work done.')}`);
      appendStep('stop', 'stopped', data.reason);
    } else {
      appendMsg('agent', escHtml(data.answer || 'No answer returned.'));
    }

    updateBudget(data.llm_calls || 0, data.total_cost || 0);
  } catch(err) {
    removeThinking();
    appendMsg('agent', '⚠ Error contacting agent: ' + err.message);
  }

  running = false;
  document.getElementById('send-btn').disabled = false;
  inp.focus();
}
</script>
</body>
</html>
"""

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # suppress default logging

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML_PAGE.encode())

    def do_POST(self):
        if self.path != "/run":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length)
        data   = json.loads(body)
        task   = data.get("task", "").strip()

        if not task:
            self._json({"error": "empty task"}, 400)
            return

        agent  = Agent()
        result = agent.run(task)

        self._json(result)

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    port = int(os.environ.get("PORT", 5000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"\n{'='*50}")
    print(f"  ReAct AI Agent — Web UI")
    print(f"{'='*50}")
    print(f"  Open in browser: http://localhost:{port}")
    print(f"  Press Ctrl+C to stop")
    print(f"{'='*50}\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    main()
