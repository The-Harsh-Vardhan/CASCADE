"""
api/extract.py alias wrapper.
"""
from blast_radius.api.extract import extract_api_endpoints_from_repo
from blast_radius.api.fetch import fetch_documenso_api_spec

__all__ = ["extract_api_endpoints_from_repo", "fetch_documenso_api_spec"]
