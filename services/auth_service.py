from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel

from config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


class JwtPayload(BaseModel):
    userId: str
    username: str


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def sign_token(payload: JwtPayload) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode = {
        "userId": payload.userId,
        "username": payload.username,
        "exp": expire,
    }
    return jwt.encode(to_encode, settings.jwt_secret, algorithm="HS256")


def verify_token(token: str) -> Optional[JwtPayload]:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return JwtPayload(userId=payload["userId"], username=payload["username"])
    except JWTError:
        return None


def get_token_from_request(request: Request) -> Optional[str]:
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]
    return None


def get_user_from_request(request: Request) -> Optional[JwtPayload]:
    token = get_token_from_request(request)
    if not token:
        return None
    return verify_token(token)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> JwtPayload:
    token = credentials.credentials
    user = verify_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return user
