"""Orchestration code to instantiate and launch the FastAPI app"""

from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.routers import search, feedback, health
from app.database import init_db
from app.limiter import limiter
from dotenv import load_dotenv
from frame_finder.engine import RacquetSearchEngine
from frame_finder.config import EMBEDDING_MODEL_NAME
from frame_finder.adapters import AnthropicAdapter


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv()
    ROOT = Path(__file__).resolve().parents[1]
    ARTIFACTS_PATH = ROOT / "data" / "processed"

    init_db()

    anthropic_adapter = AnthropicAdapter()
    engine = RacquetSearchEngine(
        path_to_artifacts=ARTIFACTS_PATH,
        embedder_name=EMBEDDING_MODEL_NAME,
        llm_adapter=anthropic_adapter,
    )

    engine.setup()
    app.state.engine = engine
    yield


app = FastAPI(lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded, _rate_limit_exceeded_handler # type:ignore
)  

app.include_router(search.router)
app.include_router(health.router)
app.include_router(feedback.router)

app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
