from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from jose import JWTError

from app.core.security import decode_access_token
from app.database.session import SessionDep
from app.modules.auth.service import get_user_by_id
from uuid import UUID

security = HTTPBearer()


async def get_current_user(credentials=Depends(security), session: SessionDep = None):
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")

    user = await get_user_by_id(user_id, session)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user
