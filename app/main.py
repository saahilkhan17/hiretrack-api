"""HireTrack API — FastAPI app factory and router wiring."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import settings
from .database import Base, engine
from .routers import applications, auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(auth.router)
    app.include_router(applications.router)

    @app.get("/health", tags=["meta"])
    def health():
        return {"status": "ok", "app": settings.app_name}

    return app


app = create_app()
