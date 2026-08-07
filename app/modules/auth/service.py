from datetime import datetime, timezone, timedelta
from uuid import UUID
from hashlib import sha256

from sqlmodel import select
from app.database.session import SessionDep

from app.modules.auth.model import User, RefreshToken


# ── User ──────────────────────────────────────────────────────────────────────

async def get_user_by_email(email: str, session: SessionDep) -> User | None:
    result = await session.exec(select(User).where(User.email == email))
    return result.first()


async def get_user_by_id(user_id: UUID, session: SessionDep) -> User | None:
    result = await session.exec(select(User).where(User.id == user_id))
    return result.first()


async def create_user(name: str, email: str, password_hash: str, session: SessionDep) -> User:
    user = User(name=name, email=email, password_hash=password_hash)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


# ── Refresh Token ─────────────────────────────────────────────────────────────

def _hash_token(token: str) -> str:
    return sha256(token.encode()).hexdigest()


async def save_refresh_token(
    user_id: UUID,
    token: str,
    session: SessionDep,
    expires_days: int = 30,
    device_name: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> RefreshToken:
    rt = RefreshToken(
        user_id=user_id,
        token_hash=_hash_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=expires_days),
        device_name=device_name,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    session.add(rt)
    await session.commit()
    return rt


async def verify_refresh_token(user_id: UUID, token: str, session: SessionDep) -> bool:
    token_hash = _hash_token(token)
    result = await session.exec(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at == None,
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
    )
    return result.first() is not None


async def revoke_refresh_token(user_id: UUID, token: str, session: SessionDep) -> None:
    token_hash = _hash_token(token)
    result = await session.exec(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.token_hash == token_hash,
        )
    )
    rt = result.first()
    if rt:
        rt.revoked_at = datetime.now(timezone.utc)
        session.add(rt)
        await session.commit()


async def revoke_all_user_tokens(user_id: UUID, session: SessionDep) -> None:
    result = await session.exec(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at == None,
        )
    )
    now = datetime.now(timezone.utc)
    for rt in result.all():
        rt.revoked_at = now
        session.add(rt)
    await session.commit()
