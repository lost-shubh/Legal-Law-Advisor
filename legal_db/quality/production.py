from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from legal_db.config import settings
from legal_db.quality.checks import QUALITY_CHECKS, QualityCheck


@dataclass(frozen=True)
class QualityCheckResult:
    name: str
    severity: str
    count: int | None
    passed: bool
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "severity": self.severity,
            "count": self.count,
            "passed": self.passed,
            "error": self.error,
        }


def sql_text(statement: str) -> Any:
    from sqlalchemy import text

    return text(statement)


def make_pg_engine(database_url: str | None = None) -> Any:
    from legal_db.db import make_engine

    return make_engine(database_url or settings.database_url)


def run_quality_check(conn: Any, check: QualityCheck) -> QualityCheckResult:
    try:
        count = int(conn.execute(sql_text(check.sql)).scalar() or 0)
    except Exception as exc:
        return QualityCheckResult(
            name=check.name,
            severity=check.severity,
            count=None,
            passed=False,
            error=str(exc),
        )
    return QualityCheckResult(
        name=check.name,
        severity=check.severity,
        count=count,
        passed=count == 0,
    )


def run_production_quality_checks(database_url: str | None = None) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).isoformat()
    try:
        engine = make_pg_engine(database_url)
        with engine.connect() as conn:
            conn.execute(sql_text("SELECT 1"))
            results = [run_quality_check(conn, check) for check in QUALITY_CHECKS]
    except Exception as exc:
        return {
            "database_available": False,
            "generated_at": generated_at,
            "checks": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "errors": 1,
                "error_failures": 0,
                "warn_failures": 0,
            },
            "error": str(exc),
        }

    failed = [item for item in results if not item.passed]
    error_failures = [item for item in failed if item.severity == "ERROR"]
    warn_failures = [item for item in failed if item.severity != "ERROR"]
    check_errors = [item for item in results if item.error]
    return {
        "database_available": True,
        "generated_at": generated_at,
        "checks": [item.to_dict() for item in results],
        "summary": {
            "total": len(results),
            "passed": len(results) - len(failed),
            "failed": len(failed),
            "errors": len(check_errors),
            "error_failures": len(error_failures),
            "warn_failures": len(warn_failures),
        },
    }


def quality_gate_passed(report: dict[str, Any]) -> bool:
    if not report.get("database_available"):
        return False
    summary = report.get("summary", {})
    return int(summary.get("errors") or 0) == 0 and int(summary.get("error_failures") or 0) == 0
