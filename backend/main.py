from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.models import ErrorResponse
from backend.routes import api_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="DocForge ID Forgery Detection API",
        version="1.0.0",
        description=(
            "Production-style prototype for an explainable ID document forgery "
            "detection service. Combines ELA, noise, edge, blur, and metadata "
            "signals into a structured fraud report."
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health", response_model=dict)
    async def health_check() -> dict:
        return {"status": "ok", "version": "1.0.0"}

    return app


app = create_app()
