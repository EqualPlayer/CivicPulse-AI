
import os
import logging
from functools import lru_cache

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


def get_supabase_url():
    return os.getenv("SUPABASE_URL", "").strip()


@lru_cache(maxsize=1)
def get_auth_client():
    url = get_supabase_url()
    key = os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()

    if not url or not key:
        raise RuntimeError("Supabase public authentication configuration missing.")

    return create_client(url, key)


@lru_cache(maxsize=1)
def get_admin_client():
    url = get_supabase_url()

    # Support both names used in earlier CivicPulse configuration.
    key = (
        os.getenv("SUPABASE_SECRET_KEY", "").strip()
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    )

    if not url or not key:
        raise RuntimeError("Supabase server-side secret configuration missing.")

    return create_client(url, key)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Please sign in to continue."
        )

    token = credentials.credentials

    # Verify the access token against Supabase Auth.
    try:
        response = get_auth_client().auth.get_user(token)
        auth_user = response.user

        if not auth_user:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired session."
            )

    except HTTPException:
        raise
    except Exception:
        logger.warning("Supabase access-token verification failed.")
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session."
        )

    # Retrieve the role from the protected database table.
    try:
        result = (
            get_admin_client()
            .table("user_roles")
            .select("role, is_active")
            .eq("user_id", str(auth_user.id))
            .limit(1)
            .execute()
        )

        roles = result.data or []

        if not roles:
            raise HTTPException(
                status_code=403,
                detail="No application role is assigned to this account."
            )

        role_record = roles[0]

        if role_record["is_active"] is not True:
            raise HTTPException(
                status_code=403,
                detail="This account has been deactivated."
            )

        role = role_record["role"]

        if role not in ("citizen", "worker", "admin"):
            raise HTTPException(
                status_code=403,
                detail="Invalid account permissions."
            )

    except HTTPException:
        raise
    except Exception:
        logger.exception("Could not retrieve account permissions.")
        raise HTTPException(
            status_code=503,
            detail="Unable to verify account permissions."
        )

    return {
        "id": str(auth_user.id),
        "email": getattr(auth_user, "email", None),
        "role": role,
    }


def require_roles(*allowed_roles):
    def role_dependency(
        current_user: dict = Depends(get_current_user)
    ):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to access this resource."
            )

        return current_user

    return role_dependency
