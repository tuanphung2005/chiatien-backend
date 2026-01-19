from fastapi import APIRouter, Depends

from database import db
from services.auth_service import get_current_user, JwtPayload

router = APIRouter()


@router.get("")
async def get_notifications(current_user: JwtPayload = Depends(get_current_user)):
    notifications = await db.notification.find_many(
        where={"userId": current_user.userId},
        order={"createdAt": "desc"},
        take=50,
    )
    return notifications


@router.get("/unread-count")
async def get_unread_count(current_user: JwtPayload = Depends(get_current_user)):
    count = await db.notification.count(
        where={"userId": current_user.userId, "read": False}
    )
    return {"count": count}


@router.patch("/{notification_id}/read")
async def mark_as_read(
    notification_id: str, current_user: JwtPayload = Depends(get_current_user)
):
    await db.notification.update_many(
        where={"id": notification_id, "userId": current_user.userId},
        data={"read": True},
    )
    return {"message": "Đã đánh dấu đã đọc"}


@router.patch("/read-all")
async def mark_all_as_read(current_user: JwtPayload = Depends(get_current_user)):
    await db.notification.update_many(
        where={"userId": current_user.userId, "read": False},
        data={"read": True},
    )
    return {"message": "Đã đánh dấu tất cả đã đọc"}
