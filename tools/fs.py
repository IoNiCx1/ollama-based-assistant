from pathlib import Path
# from config import ALLOWED_FOLDERS, BLOCKED_PATHS
from config import ALLOWED_FOLDERS, BLOCKED_PATHS, TIER3_FOLDERS, TIER2_FOLDERS
MAX_BYTES = 200_000
TEXT_EXTS = {".txt", ".md", ".csv", ".json", ".py", ".log", ".ini",
             ".yaml", ".yml", ".html", ".xml"}
SHEET_EXTS = {".xlsx", ".xlsm", ".csv"}

def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False

def _safe(path_str: str) -> Path:
    p = Path(path_str).resolve()
    if any(_inside(p, Path(b).resolve()) for b in BLOCKED_PATHS):
        raise PermissionError("this location is blocked")
    if not any(_inside(p, Path(a).resolve()) for a in ALLOWED_FOLDERS):
        raise PermissionError("path is outside the allowed folders")
    return p

def list_files(folder: str, depth: int = 1, limit: int = 200) -> str:
    p = _safe(folder)
    if not p.is_dir():
        return f"Not a folder: {p}"
    base = len(p.parts)
    lines, count = [], 0
    for item in sorted(p.rglob("*")):
        if len(item.parts) - base > depth:
            continue
        count += 1
        if len(lines) < limit:
            rel = item.relative_to(p)
            lines.append(("[DIR] " if item.is_dir() else "") + str(rel))
    result = "\n".join(lines) or "(empty folder)"
    if count > limit:
        result += f"\n... showing {limit} of {count} items. Ask for a subfolder to see more."
    return result

def read_file(path: str) -> str:
    p = _safe(path)
    if not p.is_file():
        return f"Not a file: {p}"
    if p.suffix.lower() not in TEXT_EXTS:
        return (f"Cannot read {p.suffix or 'this'} files as text. "
                f"Use preview_excel for spreadsheets.")
    if p.stat().st_size > MAX_BYTES:
        return "File is too large for this tool (limit 200 KB)."
    return p.read_text(encoding="utf-8", errors="replace")

# def preview_excel(path: str, rows: int = 20) -> str:
#     import pandas as pd
#     p = _safe(path)
#     if not p.is_file():
#         return f"Not a file: {p}"
#     if p.suffix.lower() not in SHEET_EXTS:
#         return "Not a supported spreadsheet (use .xlsx, .xlsm, or .csv)."
#     if p.stat().st_size > 50_000_000:
#         return "File too large for preview (limit 50 MB)."
#     if p.suffix.lower() == ".csv":
#         sheets = {"csv": pd.read_csv(p)}
#     else:
#         sheets = pd.read_excel(p, sheet_name=None)
#     out = []
#     for name, df in sheets.items():
#         out.append(f"Sheet: {name} ({len(df)} rows, {len(df.columns)} columns)")
#         out.append("Columns: " + ", ".join(map(str, df.columns)))
#         out.append(df.head(rows).to_string(max_cols=20))
#         out.append("")
#     return "\n".join(out)
def _find_header(df) -> int:
    # First row with at least 3 text cells is treated as the header
    for i in range(min(10, len(df))):
        row = df.iloc[i].dropna()
        if len(row) >= 3 and all(isinstance(v, str) for v in row):
            return i
    return 0

def preview_excel(path: str, rows: int = 30) -> str:
    import pandas as pd
    p = _safe(path)
    if not p.is_file():
        return f"Not a file: {p}"
    if p.suffix.lower() not in SHEET_EXTS:
        return "Not a supported spreadsheet (use .xlsx, .xlsm, or .csv)."
    if p.stat().st_size > 50_000_000:
        return "File too large for preview (limit 50 MB)."
    if p.suffix.lower() == ".csv":
        sheets = {"csv": pd.read_csv(p, header=None)}
    else:
        sheets = pd.read_excel(p, sheet_name=None, header=None)
    out = []
    for name, raw in sheets.items():
        raw = raw.dropna(how="all").dropna(axis=1, how="all").reset_index(drop=True)
        h = _find_header(raw)
        df = raw.iloc[h + 1:].copy()
        df.columns = [str(c) for c in raw.iloc[h]]
        df = df.dropna(how="all")
        out.append(f"Sheet: {name}")
        out.append(f"Total data rows: {len(df)}. Columns: {', '.join(df.columns)}")
        out.append(f"Sample of first {min(rows, len(df))} rows:")
        out.append(df.head(rows).to_string(index=False, max_cols=20))
        out.append("")
    return "\n".join(out)
def tier_of(path_str: str) -> int:
    p = Path(path_str).resolve()
    if any(_inside(p, Path(b).resolve()) for b in BLOCKED_PATHS):
        raise PermissionError("this location is blocked")
    if any(_inside(p, Path(f).resolve()) for f in TIER3_FOLDERS):
        return 3
    if any(_inside(p, Path(f).resolve()) for f in TIER2_FOLDERS):
        return 2
    raise PermissionError("path is outside the allowed folders")

def write_file(path: str, content: str) -> str:
    tier_of(path)  # raises if not allowed
    p = Path(path).resolve()
    if p.suffix.lower() not in TEXT_EXTS:
        raise PermissionError("only text files can be created (.txt, .md, .csv, .json, ...)")
    if len(content.encode("utf-8")) > MAX_BYTES:
        raise ValueError("content too large (limit 200 KB)")
    if not p.parent.is_dir():
        raise FileNotFoundError(f"folder does not exist: {p.parent}")
    target, n = p, 1
    while target.exists():  # never overwrite; add _1, _2, ...
        target = p.with_name(f"{p.stem}_{n}{p.suffix}")
        n += 1
    target.write_text(content, encoding="utf-8")
    if not target.is_file():
        raise OSError("file was not written")
    return str(target)