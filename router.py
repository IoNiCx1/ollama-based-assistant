import json, requests
from datetime import datetime
from pathlib import Path
from config import MODEL, OLLAMA_URL, NUM_CTX
from tools import fs

SYSTEM = """You are a local assistant with these tools:
- list_files(folder, depth): list files in a folder; depth 1 is the top level
- read_file(path): read a plain text file (.txt, .md, .csv, .json, .py, etc.)
- preview_excel(path, rows): show the first rows of each sheet in an Excel or CSV file
- create_file(path, content): create a NEW text file with the given content

You cannot edit, move, rename, or delete files, and you cannot run programs.
Never say in "reply" that you created or changed a file; the system reports file actions itself.
If the user asks you to read a file and also create or save something from it, choose the read tool.
The system will handle the file creation step.

Reply with ONLY a JSON object, no other text:
{"tool": "list_files" | "read_file" | "preview_excel" | "create_file" | "none", "args": {...}, "reply": "text for the user"}

Use "none" for normal conversation and put your answer in "reply".
Use a tool only when the user asks about files. Never invent file contents.
For .xlsx files always use preview_excel, never read_file.
If you don't know something, say so in "reply"."""

ANSWER_SYSTEM = """Answer the user's question using ONLY the data provided.
- Summaries, descriptions, and counts that can be read directly from the data are allowed.
- Name the sheets, columns, or values you used.
- The data may be a sample of the rows. Say so if it affects the answer.
- If the answer needs information that is not in the data, reply exactly: The data does not say this.
- Do not add outside knowledge."""

SUMMARY_SYSTEM = """Write a short plain-text summary of the data provided.
- Describe what the file contains: sheets or sections, main columns or topics, and rough size.
- If the data is a sample, say so.
- Use only the data provided. Do not add outside knowledge.
- Plain text only. No markdown tables or headers."""

TOOLS = {
    "list_files": lambda a: fs.list_files(a["folder"], int(a.get("depth", 1))),
    "read_file": lambda a: fs.read_file(a["path"]),
    "preview_excel": lambda a: fs.preview_excel(a["path"], int(a.get("rows", 30))),
}

ANSWER_FROM_DATA = {"read_file", "preview_excel"}
WRITE_WORDS = ("create", "save", "write")

PENDING = None  # a Tier 3 write waiting for your yes/no

def _log(line: str):
    with open("data/actions.log", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {line}\n")

def _ask_json(messages):
    r = requests.post(OLLAMA_URL, json={
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "format": "json",
        "options": {"num_ctx": NUM_CTX, "temperature": 0.2},
    }, timeout=300)
    r.raise_for_status()
    return r.json()["message"]["content"]

def _ask_text(messages):
    r = requests.post(OLLAMA_URL, json={
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "options": {"num_ctx": NUM_CTX, "temperature": 0.1},
    }, timeout=300)
    r.raise_for_status()
    return r.json()["message"]["content"]

def _answer_from_data(question: str, tool: str, data: str) -> str:
    messages = [
        {"role": "system", "content": ANSWER_SYSTEM},
        {"role": "user", "content": f"Data from {tool}:\n{data}\n\nQuestion: {question}"},
    ]
    return _ask_text(messages)

def _do_write(path: str, content: str) -> str:
    try:
        final = fs.write_file(path, content)
    except PermissionError as e:
        _log(f"DENIED create_file {path} ({e})")
        return f"Blocked: {e}"
    except Exception as e:
        return f"Could not create file: {e}"
    _log(f"CREATED {final}")
    return f"Created: {final}"

def _request_write(args: dict) -> str:
    global PENDING
    path, content = args["path"], args["content"]
    tier = fs.tier_of(path)  # raises PermissionError if not allowed
    if Path(path).suffix.lower() not in fs.TEXT_EXTS:
        return "Only text files can be created (.txt, .md, .csv, .json, ...)."
    if tier == 2:
        return _do_write(path, content)
    PENDING = {"path": path, "content": content}
    return (f"Create this file?\n{path}\n\nFirst lines:\n{content[:300]}\n\n"
            "Reply yes to create it, or anything else to cancel.")

def _wants_file(text: str) -> bool:
    t = text.lower()
    return any(w in t for w in WRITE_WORDS)

def _summarize_to_file(tool: str, args: dict, data: str) -> str:
    src = Path(args["path"])
    summary = _ask_text([
        {"role": "system", "content": SUMMARY_SYSTEM},
        {"role": "user", "content": f"File: {src.name}\n\nData from {tool}:\n{data}"},
    ])
    dest = src.with_name(f"{src.stem}_summary.txt")
    return _request_write({"path": str(dest), "content": summary})

def handle(user_text, history):
    global PENDING
    if PENDING is not None:
        action, PENDING = PENDING, None
        if user_text.strip().lower() in ("yes", "y"):
            return _do_write(action["path"], action["content"])
        return "Cancelled. Nothing was written."

    messages = [{"role": "system", "content": SYSTEM}] + history
    messages.append({"role": "user", "content": user_text})
    raw = _ask_json(messages)

    try:
        plan = json.loads(raw)
    except json.JSONDecodeError:
        return raw

    tool = plan.get("tool", "none")
    if tool == "none" or (tool not in TOOLS and tool != "create_file"):
        return plan.get("reply", raw)

    args = plan.get("args", {})

    if tool == "create_file":
        try:
            return _request_write(args)
        except KeyError as e:
            return f"Missing argument: {e}"
        except PermissionError as e:
            _log(f"DENIED create_file {args} ({e})")
            return f"Blocked: {e}"

    try:
        result = TOOLS[tool](args)
    except KeyError as e:
        return f"Missing argument: {e}"
    except PermissionError as e:
        _log(f"DENIED {tool} {args} ({e})")
        return f"Blocked: {e}"
    except OSError as e:
        return f"File error: {e}"
    except Exception as e:
        return f"Could not read the file: {e}"

    _log(f"OK {tool} {args}")

    if tool in ANSWER_FROM_DATA:
        if _wants_file(user_text):
            return _summarize_to_file(tool, args, result)
        return _answer_from_data(user_text, tool, result)
    return f"[{tool}]\n{result}"