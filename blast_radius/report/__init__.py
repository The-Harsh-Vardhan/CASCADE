"""
blast_radius/report/__init__.py -- Phase 6: Human-Readable Report orchestrator.
"""
from pathlib import Path

from blast_radius.config import settings
from blast_radius.models import BlastRadiusReport
from blast_radius.report.render import render


def render_report() -> tuple[Path, Path]:
    """Load Phase 5 JSON report and render HTML + Markdown outputs."""
    report_path = Path(settings.data_dir) / "reports" / "blast_radius_report.json"
    if not report_path.exists():
        raise FileNotFoundError(
            f"Report JSON not found at {report_path}. Run Phase 5 first:\n"
            "  python -m blast_radius.reason"
        )
    report = BlastRadiusReport.model_validate_json(report_path.read_text(encoding="utf-8"))
    return render(report)
