from datetime import datetime, timezone

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.db.session import get_db
from backend.dependencies import create_access_token
from backend.models.admin_user import AdminUser

router = APIRouter(prefix="/admin/auth", tags=["oauth"])
settings = get_settings()

oauth = OAuth()

oauth.register(
    name="microsoft",
    client_id=settings.microsoft_client_id,
    client_secret=settings.microsoft_client_secret,
    server_metadata_url="https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile",
        "token_endpoint_auth_method": "client_secret_post",
    },
)

oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

# The sub column for each provider
SUB_FIELD = {"microsoft": "microsoft_sub", "google": "google_sub"}


async def _find_or_onboard(
    provider: str, sub: str, email: str, name: str, db: AsyncSession
) -> AdminUser | None:
    """
    Shared identity resolution, per-provider onboarding policy.

    1. Match by provider sub (returning user) — authoritative
    2. Match by email (first SSO login for a known user) — bind the sub
    3. Unknown user — policy decides:
         microsoft: reject (whitelist; org-managed staff are pre-registered)
         google:    reject FOR NOW (flip to auto-create when multi-tenancy lands)
    """
    sub_field = SUB_FIELD[provider]

    # 1. Returning SSO user
    result = await db.execute(
        select(AdminUser).where(
            getattr(AdminUser, sub_field) == sub,
            AdminUser.is_active.is_(True),
        )
    )
    user = result.scalar_one_or_none()
    if user:
        return user

    # 2. Known email, first SSO login — bind the immutable sub
    result = await db.execute(
        select(AdminUser).where(
            AdminUser.email == email,
            AdminUser.is_active.is_(True),
        )
    )
    user = result.scalar_one_or_none()
    if user:
        setattr(user, sub_field, sub)
        await db.flush()
        return user

    # 3. Unknown user — the ONLY place the providers differ
    if provider == "google" and settings.google_self_serve_enabled:
        # Future: create Organization, then AdminUser inside it.
        # Deliberately not implemented until multi-tenancy exists —
        # auto-creating users today would expose all existing data to strangers.
        pass

    return None


async def _handle_callback(provider: str, request: Request, db: AsyncSession):
    client = oauth.create_client(provider)
    token = await client.authorize_access_token(
        request,
        claims_options={"iss": {"essential": False}},
    )
    info = token.get("userinfo")

    if not info or not info.get("email") or not info.get("sub"):
        return RedirectResponse(f"{settings.frontend_url}/login?error=provider")

    user = await _find_or_onboard(
        provider=provider,
        sub=info["sub"],
        email=info["email"].lower(),
        name=info.get("name", info["email"]),
        db=db,
    )

    if not user:
        return RedirectResponse(f"{settings.frontend_url}/login?error=unauthorized")

    user.last_login_at = datetime.now(timezone.utc)
    await db.flush()

    jwt_token = create_access_token({"sub": user.email})
    return RedirectResponse(f"{settings.frontend_url}/auth/callback?token={jwt_token}")


@router.get("/microsoft")
async def microsoft_login(request: Request):
    redirect_uri = str(request.url_for("microsoft_callback"))
    return await oauth.microsoft.authorize_redirect(request, redirect_uri)


@router.get("/microsoft/callback", name="microsoft_callback")
async def microsoft_callback(request: Request, db: AsyncSession = Depends(get_db)):
    return await _handle_callback("microsoft", request, db)


@router.get("/google")
async def google_login(request: Request):
    redirect_uri = str(request.url_for("google_callback"))
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback", name="google_callback")
async def google_callback(request: Request, db: AsyncSession = Depends(get_db)):
    return await _handle_callback("google", request, db)
