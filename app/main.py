import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import close_pool, get_pool
from app.publisher import close_publisher
from app.routers import events

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()
    yield
    await close_pool()
    await close_publisher()


app = FastAPI(
    title="EventRelay",
    description="Async event processing pipeline with RabbitMQ, FastAPI and PostgreSQL.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.include_router(events.router)


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}
