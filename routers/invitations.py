from fastapi import APIRouter, HTTPException, status, Depends
import secrets

from database import db
from models.schemas import InvitationCreate, InvitationResponse
from services.auth_service import get_current_user, JwtPayload

router = APIRouter()


@router.get("")
async def get_invitations(current_user: JwtPayload = Depends(get_current_user)):
    invitations = await db.groupinvitation.find_many(
        where={"inviteeId": current_user.userId, "status": "pending"},
        include={
            "group": True,
            "inviter": True,
        },
        order={"createdAt": "desc"},
    )
    return invitations


@router.post("")
async def create_invitation(
    request: InvitationCreate, current_user: JwtPayload = Depends(get_current_user)
):
    group = await db.group.find_unique(
        where={"id": request.groupId},
        include={"members": True},
    )

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nhóm không tồn tại",
        )

    is_member = any(m.userId == current_user.userId for m in group.members)
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không phải thành viên của nhóm này",
        )

    if not request.inviteeUsername:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vui lòng nhập tên người dùng",
        )

    invitee = await db.user.find_unique(where={"username": request.inviteeUsername})
    if not invitee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy người dùng",
        )

    already_member = any(m.userId == invitee.id for m in group.members)
    if already_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Người dùng đã là thành viên của nhóm",
        )

    existing = await db.groupinvitation.find_first(
        where={"groupId": request.groupId, "inviteeId": invitee.id, "status": "pending"}
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Đã gửi lời mời cho người dùng này",
        )

    invitation = await db.groupinvitation.create(
        data={
            "groupId": request.groupId,
            "inviterId": current_user.userId,
            "inviteeId": invitee.id,
        },
        include={"group": True, "inviter": True, "invitee": True},
    )

    await db.notification.create(
        data={
            "userId": invitee.id,
            "type": "invitation_received",
            "title": "Lời mời tham gia nhóm",
            "body": f"{invitation.inviter.displayName} mời bạn tham gia nhóm {group.name}",
            "data": {"invitationId": invitation.id, "groupId": group.id},
        }
    )

    return invitation


@router.post("/join")
async def join_by_code(
    code: str, current_user: JwtPayload = Depends(get_current_user)
):
    group = await db.group.find_unique(
        where={"inviteCode": code},
        include={"members": True},
    )

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mã mời không hợp lệ",
        )

    already_member = any(m.userId == current_user.userId for m in group.members)
    if already_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bạn đã là thành viên của nhóm này",
        )

    await db.groupmember.create(
        data={"userId": current_user.userId, "groupId": group.id}
    )

    updated_group = await db.group.find_unique(
        where={"id": group.id},
        include={"members": {"include": {"user": True}}},
    )

    return updated_group


@router.patch("/{invitation_id}")
async def respond_invitation(
    invitation_id: str,
    accept: bool,
    current_user: JwtPayload = Depends(get_current_user),
):
    invitation = await db.groupinvitation.find_unique(
        where={"id": invitation_id},
        include={"group": True, "inviter": True},
    )

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lời mời không tồn tại",
        )

    if invitation.inviteeId != current_user.userId:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền thực hiện hành động này",
        )

    new_status = "accepted" if accept else "rejected"

    await db.groupinvitation.update(
        where={"id": invitation_id},
        data={"status": new_status},
    )

    if accept:
        await db.groupmember.create(
            data={"userId": current_user.userId, "groupId": invitation.groupId}
        )

        user = await db.user.find_unique(where={"id": current_user.userId})

        await db.notification.create(
            data={
                "userId": invitation.inviterId,
                "type": "invitation_accepted",
                "title": "Lời mời được chấp nhận",
                "body": f"{user.displayName} đã tham gia nhóm {invitation.group.name}",
                "data": {"groupId": invitation.groupId},
            }
        )

    return {"message": "Đã chấp nhận lời mời" if accept else "Đã từ chối lời mời"}
