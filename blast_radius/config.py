"""
blast_radius/config.py — Centralized configuration settings via Pydantic BaseSettings.
"""
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # LLM — Google Gemini (supports up to 5 keys in rotation via GEMINI_API_KEY_1..5)
    # Falls back to GEMINI_API_KEY for single-key backward compatibility.
    gemini_api_key:   str = Field("", description="Fallback single Gemini API key")
    gemini_api_key_1: str = Field("", alias="GEMINI_API_KEY_1")
    gemini_api_key_2: str = Field("", alias="GEMINI_API_KEY_2")
    gemini_api_key_3: str = Field("", alias="GEMINI_API_KEY_3")
    gemini_api_key_4: str = Field("", alias="GEMINI_API_KEY_4")
    gemini_api_key_5: str = Field("", alias="GEMINI_API_KEY_5")
    gemini_model: str = Field("gemini-flash-latest", description="Gemini model name")

    @property
    def gemini_api_keys(self) -> list[str]:
        """Return all configured Gemini API keys in order (non-empty only)."""
        numbered = [
            self.gemini_api_key_1, self.gemini_api_key_2, self.gemini_api_key_3,
            self.gemini_api_key_4, self.gemini_api_key_5,
        ]
        keys = [k for k in numbered if k]
        if not keys and self.gemini_api_key:
            keys = [self.gemini_api_key]  # backward compat
        if not keys:
            raise EnvironmentError(
                "No Gemini API key configured. Set GEMINI_API_KEY_1 (through _5) or GEMINI_API_KEY in .env"
            )
        return keys

    # Neo4j
    neo4j_uri: str = Field("bolt://localhost:7687")
    neo4j_user: str = Field("neo4j")
    neo4j_password: str = Field("password", description="Neo4j password — required")

    # GitHub
    github_token: Optional[str] = Field(None, description="GitHub token for PR API calls")
    github_repo: str = Field("documenso/documenso", description="Target GitHub repo")

    # Target application
    target_url: str = Field("https://app.documenso.com")
    target_repo_url: str = Field("https://github.com/documenso/documenso.git")
    target_repo_name: str = Field("documenso/documenso")

    # Crawl Auth
    documenso_email: Optional[str] = Field(None, description="Documenso account email")
    documenso_password: Optional[str] = Field(None, description="Documenso account password")
    documenso_base_url: str = Field("https://app.documenso.com")

    # PR Analysis — BUG-10 Fix: default pr_number to 0 so module import succeeds before Phase 3
    pr_number: int = Field(0, description="Target PR number — set before Phase 3")
    merge_sha: str = Field("", description="Pinned merge SHA — set before Phase 3")

    # Pipeline Settings
    data_dir: Path = Field(Path("data"))
    repo_clone_dir: Path = Field(Path("data/repos/documenso"))
    crawl_max_pages: int = Field(20)
    log_level: str = Field("INFO")

    def validate_and_print(self) -> None:
        from rich.console import Console
        from rich.table import Table
        console = Console()
        table = Table(title="Blast Radius Analyzer — Configuration")
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="green")
        table.add_column("Status", style="yellow")

        display = [
            ("gemini_api_keys", f"{len(self.gemini_api_keys)} key(s) configured", "✓"),
            ("gemini_model", self.gemini_model, "✓"),
            ("neo4j_uri", self.neo4j_uri, "✓"),
            ("neo4j_user", self.neo4j_user, "✓"),
            ("neo4j_password", "***" if self.neo4j_password else "NOT SET", "✓" if self.neo4j_password else "✗"),
            ("github_token", ("set (" + self.github_token[:8] + "...)") if self.github_token else "NOT SET", "⚠ API rate limits may apply" if not self.github_token else "✓"),
            ("documenso_email", self.documenso_email or "NOT SET", "⚠ Auth crawl disabled" if not self.documenso_email else "✓"),
            ("documenso_password", "***" if self.documenso_password else "NOT SET", "⚠ Auth crawl disabled" if not self.documenso_password else "✓"),
            ("pr_number", str(self.pr_number), "✓"),
            ("merge_sha", self.merge_sha if self.merge_sha else "NOT SET", "⚠ Set before Phase 3" if not self.merge_sha else "✓"),
            ("data_dir", str(self.data_dir), "✓"),
        ]
        for key, value, status in display:
            table.add_row(key, value, status)
        console.print(table)


settings = Settings()
