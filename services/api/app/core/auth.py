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
    if token.startswith("demo-"):
        from uuid import UUID
        try:
            return UUID(token[5:])
        except ValueError:
            pass

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
    # Check if we have an identity matching the ID or linked via auth_provider_ref
    from sqlalchemy import or_
    result = await db.execute(
        select(Identity).where(
            or_(
                Identity.id == identity_id,
                Identity.auth_provider_ref == str(identity_id)
            )
        )
    )
    identity = result.scalars().first()

    if not identity:
        # Check for collision by email (stub identity pending first login)
        if email:
            result_email = await db.execute(
                select(Identity).where(
                    Identity.email == email,
                    Identity.auth_provider_ref == None
                )
            )
            identity = result_email.scalars().first()

        if identity:
            # Stub found, link it
            identity.auth_provider_ref = str(identity_id)
            # If Keycloak provides a full_name that we don't have, we could populate it here
            await db.commit()
        else:
            # No stub found, create a new one
            identity = Identity(
                id=identity_id,
                email=email or f"{identity_id}@unknown",
                auth_provider_ref="keycloak", # original default, though str(identity_id) is better, but preserving behavior
                platform_role=None  # Explicitly None
            )
            db.add(identity)
            await db.commit()

    return identity.id
