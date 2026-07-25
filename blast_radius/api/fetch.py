"""
blast_radius/api/fetch.py -- Fetches Documenso API specifications via HTTP/OpenAPI or Docs parsing.
"""

from __future__ import annotations

import logging
from typing import Any
import httpx

logger = logging.getLogger(__name__)

API_SPEC_URLS: list[str] = [
    "https://documenso.com/openapi.json",
    "https://documenso.com/api/v1",
    "https://raw.githubusercontent.com/documenso/documenso/main/packages/api/v1/openapi.json",
    "https://docs.documenso.com/developers/api-reference",
]


def fetch_documenso_api_spec() -> list[dict[str, Any]]:
    """
    Try API spec URLs in order until one works, returning a list of endpoint dicts:
    {
        "id": "POST /api/v1/documents",
        "method": "POST",
        "path": "/api/v1/documents",
        "description": "Create a new document",
        "handler_file": "",
        "handler_function": "",
        "request_body_schema": {},
        "response_schema": {},
        "tags": ["documents"],
        "feature_area": "sending"
    }
    """
    endpoints: list[dict[str, Any]] = []

    for url in API_SPEC_URLS:
        try:
            logger.info("Attempting to fetch API spec from %s", url)
            response = httpx.get(url, timeout=10.0, follow_redirects=True)
            if response.status_code != 200:
                continue

            content_type = response.headers.get("content-type", "")
            if "json" in content_type or url.endswith(".json"):
                data = response.json()
                if isinstance(data, dict) and "paths" in data:
                    parsed = _parse_openapi_spec(data)
                    if parsed:
                        logger.info("Successfully parsed %d endpoints from OpenAPI at %s", len(parsed), url)
                        return parsed
            elif "html" in content_type:
                parsed = _parse_html_api_docs(response.text)
                if parsed:
                    logger.info("Parsed %d endpoints from HTML at %s", len(parsed), url)
                    return parsed
        except Exception as exc:
            logger.debug("Failed fetching spec from %s: %s", url, exc)

    logger.warning("All remote spec URLs failed. Returning baseline API spec list.")
    return _get_fallback_api_spec()


def _parse_openapi_spec(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse standard OpenAPI v3 JSON spec into endpoint dicts."""
    endpoints: list[dict[str, Any]] = []
    paths = data.get("paths", {})

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method_name, op in path_item.items():
            if method_name.upper() not in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                continue
            if not isinstance(op, dict):
                continue

            method = method_name.upper()
            summary = op.get("summary", "")
            desc = op.get("description", summary)
            tags = op.get("tags", [])
            area = tags[0] if tags else _guess_feature_area(path)

            ep_id = f"{method} {path}"
            endpoints.append({
                "id": ep_id,
                "method": method,
                "path": path,
                "description": desc or summary,
                "handler_file": "",
                "handler_function": "",
                "request_body_schema": op.get("requestBody", {}),
                "response_schema": op.get("responses", {}),
                "tags": tags or [area],
                "feature_area": area,
            })
    return endpoints


def _parse_html_api_docs(html_text: str) -> list[dict[str, Any]]:
    """Extract API endpoints from HTML docs using regex / parsing."""
    import re
    endpoints: list[dict[str, Any]] = []
    # Match patterns like GET /api/v1/documents or POST /api/v1/documents/{id}/send
    pattern = r'(GET|POST|PUT|DELETE|PATCH)\s+(/api/v1/[a-zA-Z0-9/_\-\{\}:]+)'
    matches = set(re.findall(pattern, html_text))

    for method, path in matches:
        normalized_path = path.replace(":", "{").replace("}", "}")
        area = _guess_feature_area(normalized_path)
        endpoints.append({
            "id": f"{method} {normalized_path}",
            "method": method,
            "path": normalized_path,
            "description": f"{method} endpoint for {normalized_path}",
            "handler_file": "",
            "handler_function": "",
            "request_body_schema": {},
            "response_schema": {},
            "tags": [area],
            "feature_area": area,
        })
    return endpoints


def _guess_feature_area(path: str) -> str:
    p = path.lower()
    if "template" in p:
        return "template"
    elif "recipient" in p:
        return "recipient"
    elif "field" in p:
        return "field"
    elif "document" in p or "sign" in p:
        return "sending"
    elif "team" in p or "member" in p:
        return "team"
    elif "webhook" in p:
        return "webhook"
    elif "token" in p or "api" in p:
        return "api"
    elif "profile" in p or "user" in p:
        return "admin"
    return "api"


def _get_fallback_api_spec() -> list[dict[str, Any]]:
    """Return canonical baseline endpoints for Documenso REST API."""
    return [
        {"id": "POST /api/v1/documents", "method": "POST", "path": "/api/v1/documents", "description": "Create a new document", "feature_area": "sending", "tags": ["documents"], "handler_function": "createDocument"},
        {"id": "GET /api/v1/documents", "method": "GET", "path": "/api/v1/documents", "description": "List all documents", "feature_area": "sending", "tags": ["documents"], "handler_function": "getDocuments"},
        {"id": "GET /api/v1/documents/{id}", "method": "GET", "path": "/api/v1/documents/{id}", "description": "Get single document", "feature_area": "sending", "tags": ["documents"], "handler_function": "getDocument"},
        {"id": "DELETE /api/v1/documents/{id}", "method": "DELETE", "path": "/api/v1/documents/{id}", "description": "Delete document", "feature_area": "sending", "tags": ["documents"], "handler_function": "deleteDocument"},
        {"id": "POST /api/v1/documents/{id}/send", "method": "POST", "path": "/api/v1/documents/{id}/send", "description": "Send document for signing", "feature_area": "sending", "tags": ["documents"], "handler_function": "sendDocument"},
        {"id": "POST /api/v1/documents/{id}/resend", "method": "POST", "path": "/api/v1/documents/{id}/resend", "description": "Resend document notification", "feature_area": "sending", "tags": ["documents"], "handler_function": "resendDocument"},
        {"id": "GET /api/v1/documents/{id}/recipients", "method": "GET", "path": "/api/v1/documents/{id}/recipients", "description": "Get document recipients", "feature_area": "recipient", "tags": ["recipients"], "handler_function": "getRecipients"},
        {"id": "POST /api/v1/documents/{id}/recipients", "method": "POST", "path": "/api/v1/documents/{id}/recipients", "description": "Create document recipient", "feature_area": "recipient", "tags": ["recipients"], "handler_function": "createRecipient"},
        {"id": "PUT /api/v1/documents/{id}/recipients/{recipientId}", "method": "PUT", "path": "/api/v1/documents/{id}/recipients/{recipientId}", "description": "Update recipient", "feature_area": "recipient", "tags": ["recipients"], "handler_function": "updateRecipient"},
        {"id": "DELETE /api/v1/documents/{id}/recipients/{recipientId}", "method": "DELETE", "path": "/api/v1/documents/{id}/recipients/{recipientId}", "description": "Delete recipient", "feature_area": "recipient", "tags": ["recipients"], "handler_function": "deleteRecipient"},
        {"id": "POST /api/v1/documents/{id}/fields", "method": "POST", "path": "/api/v1/documents/{id}/fields", "description": "Create document field", "feature_area": "field", "tags": ["fields"], "handler_function": "createField"},
        {"id": "GET /api/v1/templates", "method": "GET", "path": "/api/v1/templates", "description": "List templates", "feature_area": "template", "tags": ["templates"], "handler_function": "getTemplates"},
        {"id": "POST /api/v1/templates", "method": "POST", "path": "/api/v1/templates", "description": "Create template", "feature_area": "template", "tags": ["templates"], "handler_function": "createTemplate"},
        {"id": "GET /api/v1/templates/{id}", "method": "GET", "path": "/api/v1/templates/{id}", "description": "Get single template", "feature_area": "template", "tags": ["templates"], "handler_function": "getTemplate"},
        {"id": "DELETE /api/v1/templates/{id}", "method": "DELETE", "path": "/api/v1/templates/{id}", "description": "Delete template", "feature_area": "template", "tags": ["templates"], "handler_function": "deleteTemplate"},
        {"id": "POST /api/v1/templates/{id}/use", "method": "POST", "path": "/api/v1/templates/{id}/use", "description": "Generate document from template", "feature_area": "template", "tags": ["templates"], "handler_function": "generateDocumentFromTemplate"},
        {"id": "GET /api/v1/profile", "method": "GET", "path": "/api/v1/profile", "description": "Get user profile", "feature_area": "admin", "tags": ["profile"], "handler_function": "getProfile"},
    ]
