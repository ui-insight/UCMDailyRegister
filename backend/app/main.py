import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create upload directory
    os.makedirs(settings.upload_dir, exist_ok=True)
    yield


app = FastAPI(
    title="UCM Newsletter Builder",
    description="AI-assisted newsletter production for University of Idaho",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router)
