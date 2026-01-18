from fastapi import APIRouter, HTTPException, status

from database import db
from models.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from services.auth_service import (
    hash_password,
    verify_password,
    sign_token,
    JwtPayload,
)

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    if not request.username or not request.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vui lòng nhập tên đăng nhập và mật khẩu",
        )

    user = await db.user.find_unique(where={"username": request.username})

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu không đúng",
        )

    if not verify_password(request.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu không đúng",
        )

    token = sign_token(JwtPayload(userId=user.id, username=user.username))

    return TokenResponse(
        token=token,
        user=UserResponse(
            id=user.id,
            username=user.username,
            displayName=user.displayName,
            avatar=user.avatar,
        ),
    )


@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest):
    if not request.username or not request.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vui lòng nhập tên đăng nhập và mật khẩu",
        )

    existing_user = await db.user.find_unique(where={"username": request.username})

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tên đăng nhập đã tồn tại",
        )

    hashed_password = hash_password(request.password)

    user = await db.user.create(
        data={
            "username": request.username,
            "password": hashed_password,
            "displayName": request.displayName or request.username,
        }
    )

    token = sign_token(JwtPayload(userId=user.id, username=user.username))

    return TokenResponse(
        token=token,
        user=UserResponse(
            id=user.id,
            username=user.username,
            displayName=user.displayName,
            avatar=user.avatar,
        ),
    )
