"""
blast_radius/code/index.py — AST-grep static analysis to build a call graph.

Phase 3 DEEP implementation:
- Two-pass scan: ts-functions.yml + trpc-procedures.yml
- Path normalization: always forward-slash, relative to repo root
- BUG-04 fix: verify_path_alignment() raises hard if 0 matches

Scan paths (Documenso-specific, as of v2025):
  packages/lib/          — server-only business logic
  packages/trpc/server/  — tRPC procedure definitions
  apps/remix/app/        — Remix UI actions/loaders (optional, falls back gracefully)
"""

import json
import re
import subprocess
import sys
from pathlib import Path

from blast_radius.models import CodeFunction, PRDelta

# On Windows, npm-installed ast-grep is exposed as sg.cmd (a .cmd shim).
# The bare 'sg' command is a .ps1 script that Python subprocess cannot invoke
# without shell=True. Use sg.cmd unconditionally on Windows.
_SG_CMD = "sg.cmd" if sys.platform == "win32" else "sg"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_path(abs_path: str, repo_dir: Path) -> str:
    """
    Return path relative to repo_dir with forward slashes.
    Handles both Windows backslash and POSIX paths.
    """
    try:
        rel = Path(abs_path).resolve().relative_to(repo_dir.resolve())
        return rel.as_posix()
    except ValueError:
        # abs_path already relative, or outside repo root
        return Path(abs_path).as_posix()


def _make_function_id(repo_dir: Path, abs_file: str, start_line: int, name: str) -> str:
    """
    Stable function ID: relative/path/file.ts:start_line:name
    Must match the format used in Phase 5 seed computation.
    """
    rel = _normalize_path(abs_file, repo_dir)
    return f"{rel}:{start_line}:{name}"


def _extract_name_from_text(text: str, rule_id: str) -> str:
    """Extract function/procedure name from matched AST text snippet."""
    text = text.strip()

    # tRPC Route: matched text looks like 'createDocumentRoute = authenticatedProcedure...'
    if rule_id == "trpc-procedure":
        m = re.match(r"(\w+Route)\s*=", text)
        if m:
            return m.group(1)

    # Standard function declaration: function foo(...) { ... }
    m = re.match(r"(?:export\s+)?(?:async\s+)?function\s+(\w+)", text)
    if m:
        return m.group(1)

    # Const arrow function: const foo = async (...) => ...
    m = re.match(r"(?:export\s+)?const\s+(\w+)\s*=", text)
    if m:
        return m.group(1)

    # Variable declarator (from trpc rule): xRoute = ...
    m = re.match(r"(\w+)\s*=", text)
    if m and m.group(1) not in ("async", "function", "const", "let", "var"):
        return m.group(1)

    # Method definition: async methodName(...)
    m = re.match(r"(?:async\s+)?(\w+)\s*\(", text)
    if m and m.group(1) not in ("async", "function", "const", "let", "var", "if", "for"):
        return m.group(1)

    return "anonymous"


def _parse_ast_grep_output(stdout: str) -> list[dict]:
    """
    Parse ast-grep JSON output. Handles both array and NDJSON formats.
    ast-grep exits 1 with no matches (POSIX grep convention) — caller must
    allow returncode=1.
    """
    stdout = stdout.strip()
    if not stdout or stdout == "[]":
        return []
    try:
        data = json.loads(stdout)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass
    # Try NDJSON fallback
    rows = []
    for line in stdout.splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return rows


def ast_matches(repo: Path, rule_file: str) -> list[dict]:
    """
    Run ast-grep with the given rule against Documenso's TypeScript source.

    Scan paths (Documenso-specific):
      - packages/lib/          (server-only business logic)
      - packages/trpc/server/  (tRPC procedures)
      - apps/remix/app/        (Remix UI actions/loaders — optional)

    Excludes migrations, node_modules, dist, build.
    """
    rule = Path(rule_file)
    if not rule.exists():
        raise FileNotFoundError(
            f"Rule file not found: {rule}. Run from the project root."
        )

    candidate_paths = [
        repo / "packages" / "lib",
        repo / "packages" / "trpc" / "server",
        repo / "apps" / "remix" / "app",
        # Fallback for older clones that still have apps/web
        repo / "apps" / "web" / "src",
    ]
    scan_paths = [str(p) for p in candidate_paths if p.exists()]
    if not scan_paths:
        raise RuntimeError(
            f"No valid scan paths under {repo}. "
            "Expected packages/lib/, packages/trpc/server/, apps/remix/app/."
        )

    result = subprocess.run(
        [_SG_CMD, "scan", "--rule", str(rule)] + scan_paths + ["--json"],
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    # ast-grep exits 1 when no matches (normal, like POSIX grep)
    if result.returncode not in (0, 1):
        raise RuntimeError(
            f"ast-grep failed (exit {result.returncode}) for rule {rule_file}:\n"
            f"stderr: {result.stderr[:500]}"
        )

    return _parse_ast_grep_output(result.stdout)


# ---------------------------------------------------------------------------
# BUG-04 fix: path alignment guard
# ---------------------------------------------------------------------------

def verify_path_alignment(functions: list[CodeFunction], delta: PRDelta) -> None:
    """
    BUG-04 fix: ensure CodeFunction.file paths can be matched against
    PRDelta changed_files paths. Raises hard if 0 matches — means 100%
    dark changes and the report would be meaningless.
    """
    if not functions or not delta.changed_files:
        return

    sample_fn = functions[0].file if functions else "N/A"
    sample_delta = delta.changed_files[0].path if delta.changed_files else "N/A"

    matches = sum(
        1 for cf in functions
        for f in delta.changed_files
        if cf.file.endswith(f.path) or f.path.endswith(cf.file)
    )

    print(f"[verify] fn.file sample:   {sample_fn}")
    print(f"[verify] delta.path sample: {sample_delta}")
    print(f"[verify] Matches: {matches}/{len(delta.changed_files)} changed files align")

    if matches == 0:
        raise ValueError(
            "ZERO path matches between CodeFunctions and PRDelta. "
            "Path normalization failed — all functions will be dark changes.\n"
            f"  fn.file sample:    {sample_fn}\n"
            f"  delta.path sample: {sample_delta}"
        )


# ---------------------------------------------------------------------------
# Main entry: build call graph
# ---------------------------------------------------------------------------

def build_call_graph(repo: Path) -> list[CodeFunction]:
    """
    Two-pass AST scan:
      Pass 1 — ts-functions.yml: function_declaration, method_definition, arrow_function
      Pass 2 — trpc-procedures.yml: variable_declarator with name matching *Route

    BUG-04 fix applied: fn.file stored as forward-slash repo-relative path.
    """
    fn_lookup: dict[str, CodeFunction] = {}
    file_fns: dict[str, list[tuple[str, int]]] = {}  # abs_file -> [(name, start_line)]
    trpc_count = 0

    for rule_file in ["rules/ts-functions.yml", "rules/trpc-procedures.yml"]:
        rule_id = Path(rule_file).stem   # "ts-functions" or "trpc-procedures"
        is_trpc = "trpc" in rule_id

        try:
            matches = ast_matches(repo, rule_file)
        except Exception as e:
            print(f"[code] WARNING: {rule_file} scan failed: {e}")
            continue

        for match in matches:
            abs_file = match.get("file", "")
            # ast-grep uses 0-indexed lines; store as-is and document it
            start_line = match.get("range", {}).get("start", {}).get("line", 0)
            end_line = match.get("range", {}).get("end", {}).get("line", 0)
            # "text" is the matched AST node body (arrow functions start with 'async (').
            # "lines" is the full source line including 'export const cancelDocument = ...'.
            # Strategy: try text first; if anonymous, retry with lines (catches arrow functions).
            text = match.get("text", "")
            lines_field = match.get("lines", "")

            name = _extract_name_from_text(text, rule_id)
            if name in ("anonymous", "") and lines_field:
                name = _extract_name_from_text(lines_field, rule_id)
            if name in ("anonymous", ""):
                continue

            if is_trpc:
                trpc_count += 1

            try:
                fn_id = _make_function_id(repo, abs_file, start_line, name)
                rel_file = _normalize_path(abs_file, repo)
            except Exception:
                continue

            file_fns.setdefault(abs_file, []).append((name, start_line))

            if fn_id not in fn_lookup:
                fn_lookup[fn_id] = CodeFunction(
                    function_id=fn_id,
                    name=name,
                    file=rel_file,           # BUG-04: forward-slash relative path
                    start_line=start_line,
                    end_line=end_line,
                    ast_node_type="trpc-procedure" if is_trpc else "ts-function",
                    is_trpc_procedure=is_trpc,
                )

    if len(fn_lookup) < 50:
        sample = [(f.name, f.file) for f in list(fn_lookup.values())[:5]]
        raise RuntimeError(
            f"Only {len(fn_lookup)} functions found (need ≥50).\n"
            f"Sample found: {sample}\n"
            "Debug:\n"
            "  1. sg --version\n"
            "  2. ls data/repos/documenso/packages/lib/server-only/document/\n"
            "  3. sg scan --rule rules/ts-functions.yml data/repos/documenso/packages/lib --json | python -c 'import json,sys; d=json.load(sys.stdin); print(len(d))'"
        )

    if trpc_count == 0:
        print(
            "[code] WARNING: 0 tRPC procedures found. "
            "Check rules/trpc-procedures.yml against the actual router file structure."
        )

    # ── Same-file call resolution (conservative: name appears in same file) ──
    name_to_ids: dict[str, list[str]] = {}
    for fn in fn_lookup.values():
        name_to_ids.setdefault(fn.name, []).append(fn.function_id)

    for abs_file, fn_list in file_fns.items():
        same_file_names = {name for name, _ in fn_list}
        try:
            file_content = Path(abs_file).read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for fn_name, fn_line in fn_list:
            try:
                caller_id = _make_function_id(repo, abs_file, fn_line, fn_name)
            except Exception:
                continue
            if caller_id not in fn_lookup:
                continue

            for callee_name in same_file_names:
                if callee_name == fn_name:
                    continue
                # Check for call or property-access reference
                if re.search(r"\b" + re.escape(callee_name) + r"\s*[\(.]", file_content):
                    for callee_id in name_to_ids.get(callee_name, []):
                        callee_fn = fn_lookup.get(callee_id)
                        if not callee_fn or callee_fn.file != fn_lookup[caller_id].file:
                            continue
                        if callee_id not in fn_lookup[caller_id].calls:
                            fn_lookup[caller_id].calls.append(callee_id)
                        if caller_id not in callee_fn.called_by:
                            callee_fn.called_by.append(caller_id)

    return list(fn_lookup.values())
