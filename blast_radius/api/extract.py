"""
blast_radius/api/extract.py -- Extracts APIEndpoints from local Documenso repo analysis.
"""

from __future__ import annotations

import re
import logging
from pathlib import Path
from typing import Any

from blast_radius.api.fetch import fetch_documenso_api_spec, _guess_feature_area

logger = logging.getLogger(__name__)


def extract_api_endpoints_from_repo(repo_dir: str | Path) -> list[dict[str, Any]]:
    """
    Search repository files for API route definitions and handlers:
    - packages/api/**/*.ts
    - apps/web/src/app/api/**/*.ts
    - packages/trpc/**/*.ts

    Returns list of endpoint dicts with extracted fields:
    {
        "id": "POST /api/v1/documents",
        "method": "POST",
        "path": "/api/v1/documents",
        "description": "Create a new document",
        "handler_file": "packages/api/v1/implementation.ts",
        "handler_function": "createDocument",
        "tags": ["documents"],
        "feature_area": "sending"
    }
    """
    repo_path = Path(repo_dir)
    endpoints_map: dict[str, dict[str, Any]] = {}

    # 1. Fetch remote / baseline spec first
    baseline_specs = fetch_documenso_api_spec()
    for ep in baseline_specs:
        endpoints_map[ep["id"]] = ep

    if not repo_path.exists():
        logger.warning("Repo directory %s does not exist -- returning fetched spec list.", repo_dir)
        return list(endpoints_map.values())

    # 2. Parse ts-rest contract file (packages/api/v1/contract.ts)
    contract_file = repo_path / "packages" / "api" / "v1" / "contract.ts"
    if contract_file.exists():
        try:
            content = contract_file.read_text(encoding="utf-8")
            parsed_contract = _parse_ts_rest_contract(content, "packages/api/v1/contract.ts")
            for ep in parsed_contract:
                endpoints_map[ep["id"]] = ep
            logger.info("Parsed %d endpoints from contract.ts", len(parsed_contract))
        except Exception as exc:
            logger.warning("Failed parsing contract.ts: %s", exc)

    # 3. Parse Next.js route handler files (apps/web/src/app/api/**/*.ts)
    for ts_file in repo_path.glob("**/api/**/*.ts"):
        rel_path = str(ts_file.relative_to(repo_path)).replace("\\", "/")
        try:
            text = ts_file.read_text(encoding="utf-8")
            # Look for export async function GET / POST / PUT / DELETE
            methods = re.findall(r'export\s+async\s+function\s+(GET|POST|PUT|DELETE|PATCH)', text)
            if methods:
                # Derive path from file path: e.g. apps/web/src/app/api/v1/documents/[id]/route.ts
                route_path = _file_path_to_api_route(rel_path)
                if route_path:
                    for method in methods:
                        ep_id = f"{method} {route_path}"
                        area = _guess_feature_area(route_path)
                        if ep_id not in endpoints_map:
                            endpoints_map[ep_id] = {
                                "id": ep_id,
                                "method": method,
                                "path": route_path,
                                "description": f"{method} endpoint for {route_path}",
                                "handler_file": rel_path,
                                "handler_function": method.lower(),
                                "tags": [area],
                                "feature_area": area,
                            }
                        else:
                            endpoints_map[ep_id]["handler_file"] = rel_path
        except Exception:
            pass

    return list(endpoints_map.values())


def _parse_ts_rest_contract(content: str, rel_file_path: str) -> list[dict[str, Any]]:
    """Parse ts-rest contract definitions from contract.ts content."""
    endpoints: list[dict[str, Any]] = []

    # Regex block matcher for contract entries like:
    # getDocuments: { method: 'GET', path: '/api/v1/documents', ... summary: '...' }
    block_pattern = r'([a-zA-Z0-9_]+):\s*\{\s*method:\s*[\'"](GET|POST|PUT|DELETE|PATCH)[\'"],\s*path:\s*[\'"]([^\'"]+)[\'"](?:,\s*summary:\s*[\'"]([^\'"]+)[\'"])?'

    for match in re.finditer(block_pattern, content, re.DOTALL):
        fn_name, method, raw_path, summary = match.groups()
        normalized_path = raw_path.replace(":", "{").replace("Id", "Id}").replace("id", "id}")
        if not normalized_path.endswith("}") and "{" in normalized_path and not normalized_path.count("{") == normalized_path.count("}"):
            normalized_path += "}"

        # Clean path e.g. /api/v1/documents/:id -> /api/v1/documents/{id}
        normalized_path = re.sub(r':([a-zA-Z0-9_]+)', r'{\1}', raw_path)
        area = _guess_feature_area(normalized_path)
        ep_id = f"{method} {normalized_path}"

        endpoints.append({
            "id": ep_id,
            "method": method,
            "path": normalized_path,
            "description": summary or f"{fn_name} procedure for {normalized_path}",
            "handler_file": rel_file_path,
            "handler_function": fn_name,
            "tags": [area],
            "feature_area": area,
        })

    return endpoints


def _file_path_to_api_route(rel_file_path: str) -> str | None:
    """Convert Next.js route file path to API path: apps/web/src/app/api/v1/documents/[id]/route.ts -> /api/v1/documents/{id}"""
    if "route.ts" not in rel_file_path and "route.js" not in rel_file_path:
        return None
    p = rel_file_path.split("app")[-1] if "app" in rel_file_path else rel_file_path
    p = p.replace("/route.ts", "").replace("/route.js", "")
    p = p.replace("[", "{").replace("]", "}")
    if not p.startswith("/"):
        p = "/" + p
    return p
