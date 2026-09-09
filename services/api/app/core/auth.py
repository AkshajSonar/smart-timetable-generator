import jwt
from fastapi import Request, HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.models.identity import Identity
from app.core.config import settings

security = HTTPBearer()

# We cache the JWKS client so we don't fetch certs on every request
# JWT_ISSUER_URL might be like http://localhost:8080/realms/timetable
JWKS_URL = f"{settings.JWT_ISSUER_URL}/protocol/openid-connect/certs" if settings.JWT_ISSUER_URL else "http://localhost:8080/realms/timetable/protocol/openid-connect/certs"
jwks_client = jwt.PyJWKClient(JWKS_URL)

async def verify_jwt(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: AsyncSession = Depends(get_db)
) -> str:
    """
    Validates the incoming JWT against Keycloak and extracts the identity_id (sub).
    Auto-provisions the identity if it doesn't exist.
    """
    token = credentials.credentials
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        # Verify token (we don't strictly enforce audience here unless specified)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_aud": False}
        )
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "FORBIDDEN", "message": f"Invalid token: {str(e)}"}}
        )

    from uuid import UUID
    try:
        identity_id = UUID(payload.get("sub"))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "FORBIDDEN", "message": "Token 'sub' claim is not a valid UUID"}}
        )

    email = payload.get("email")
    
    # Auto-provisioning check
    # Note: An auto-provisioned identity always gets platform_role = null.
    # Auto-provisioning creates a login record only - it grants no access by itself.
    # A freshly auto-provisioned identity with no staff_profile anywhere will be
    # correctly rejected by every RBAC check because it has nothing to authorize against.
    result = await db.execute(select(Identity).where(Identity.id == identity_id))
    identity = result.scalars().first()

    if not identity:
        identity = Identity(
            id=identity_id,
            email=email or f"{identity_id}@unknown",
            auth_provider_ref="keycloak",
            platform_role=None  # Explicitly None
        )
        db.add(identity)
        await db.commit()

    return identity_id
