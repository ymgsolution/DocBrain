from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.error_handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import CorrelationIdMiddleware
from app.modules.auth.public_router import router as public_auth_router
from app.modules.auth.router import router as auth_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.documents.router import router as documents_router
from app.modules.invitations.public_router import router as public_invitations_router
from app.modules.invitations.router import router as invitations_router
from app.modules.reviews.router import router as reviews_router
from app.modules.shares.public_router import router as public_shares_router
from app.modules.shares.router import router as shares_router
from app.modules.taxonomy.router import router as taxonomy_router
from app.modules.versions.router import router as versions_router

configure_logging()
settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(auth_router)
app.include_router(public_auth_router)
app.include_router(documents_router)
app.include_router(versions_router)
app.include_router(taxonomy_router)
app.include_router(invitations_router)
app.include_router(public_invitations_router)
app.include_router(shares_router)
# The only unauthenticated router — see its module docstring.
app.include_router(public_shares_router)
app.include_router(reviews_router)
app.include_router(dashboard_router)


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
