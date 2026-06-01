from __future__ import annotations


def health() -> dict[str, str]:
    return {"status": "ok", "service": "legal-api"}


try:
    from fastapi import FastAPI

    app = FastAPI(title="Legal Law Advisor API", version="0.1.0")

    @app.get("/health")
    def health_route() -> dict[str, str]:
        return health()

except ImportError:
    # FastAPI is an app runtime dependency. The pure function above keeps the
    # skeleton importable in the current data-pipeline environment.
    app = None

