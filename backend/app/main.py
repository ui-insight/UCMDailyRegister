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

# authlib keeps the OIDC `state` between the login redirect and the callback
# in Starlette's signed session cookie, so SSO cannot work without this.
# Added only when SSO is the configured login, so the trusted-header
# deployment carries no session cookie at all.
if settings.auth_provider == "oidc":
    from starlette.middleware.sessions import SessionMiddleware

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_cookie_secret_key,
        https_only=settings.is_production,
        same_site="lax",
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router)
