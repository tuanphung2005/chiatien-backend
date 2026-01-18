from fastapi import APIRouter, HTTPException, status, Depends

from database import db
from models.schemas import GroupCreate, GroupUpdate
from services.auth_service import get_current_user, JwtPayload

router = APIRouter()


@router.get("")
async def get_groups(current_user: JwtPayload = Depends(get_current_user)):
    groups = await db.group.find_many(
        where={"members": {"some": {"userId": current_user.userId}}},
        include={
            "members": {
                "include": {
                    "user": True
                }
            },
            "expenses": {
                "include": {
                    "paidBy": True,
                    "participants": True,
                },
            },
        },
        order={"updatedAt": "desc"},
    )

    groups_with_balance = []
    for group in groups:
        balance = 0.0

        for expense in group.expenses:
            if expense.paidById == current_user.userId:
                others_share = sum(
                    p.amount
                    for p in expense.participants
                    if p.userId != current_user.userId
                )
                balance += others_share
            else:
                user_share = next(
                    (p for p in expense.participants if p.userId == current_user.userId),
                    None,
                )
                if user_share and not user_share.settled:
                    balance -= user_share.amount

        groups_with_balance.append(
            {
                "id": group.id,
                "name": group.name,
                "emoji": group.emoji,
                "description": group.description,
                "memberCount": len(group.members),
                "expenseCount": len(group.expenses),
                "balance": balance,
                "members": [m.user for m in group.members],
                "recentExpenses": group.expenses[:3],
            }
        )

    return groups_with_balance


@router.post("")
async def create_group(
    request: GroupCreate, current_user: JwtPayload = Depends(get_current_user)
):
    if not request.name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vui lòng nhập tên nhóm",
        )

    member_creates = [{"userId": current_user.userId}]
    if request.memberIds:
        member_creates.extend([{"userId": uid} for uid in request.memberIds])

    group = await db.group.create(
        data={
            "name": request.name,
            "emoji": request.emoji or "💰",
            "description": request.description,
            "createdById": current_user.userId,
            "members": {"create": member_creates},
        },
        include={
            "members": {
                "include": {
                    "user": True
                }
            }
        },
    )

    return group


@router.get("/{group_id}")
async def get_group(
    group_id: str, current_user: JwtPayload = Depends(get_current_user)
):
    group = await db.group.find_unique(
        where={"id": group_id},
        include={
            "members": {
                "include": {
                    "user": True
                }
            },
            "expenses": {
                "include": {
                    "paidBy": True,
                    "participants": {
                        "include": {
                            "user": True
                        }
                    },
                    "receipt": True,
                },
            },
            "createdBy": True,
        },
    )

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nhóm không tồn tại",
        )

    is_member = any(m.user.id == current_user.userId for m in group.members)
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không phải thành viên của nhóm này",
        )

    balances = {m.user.id: 0.0 for m in group.members}

    for expense in group.expenses:
        balances[expense.paidById] = balances.get(expense.paidById, 0) + expense.amount

        for p in expense.participants:
            if not p.settled:
                balances[p.userId] = balances.get(p.userId, 0) - p.amount

    members_with_balance = [
        {
            "id": m.user.id,
            "username": m.user.username,
            "displayName": m.user.displayName,
            "avatar": m.user.avatar,
            "balance": balances.get(m.user.id, 0),
        }
        for m in group.members
    ]

    total_expenses = sum(e.amount for e in group.expenses)

    return {
        "id": group.id,
        "name": group.name,
        "emoji": group.emoji,
        "description": group.description,
        "createdBy": group.createdBy,
        "members": members_with_balance,
        "expenses": group.expenses,
        "totalExpenses": total_expenses,
    }


@router.put("/{group_id}")
async def update_group(
    group_id: str,
    request: GroupUpdate,
    current_user: JwtPayload = Depends(get_current_user),
):
    update_data = {}
    if request.name is not None:
        update_data["name"] = request.name
    if request.emoji is not None:
        update_data["emoji"] = request.emoji
    if request.description is not None:
        update_data["description"] = request.description

    group = await db.group.update(where={"id": group_id}, data=update_data)

    return group


@router.delete("/{group_id}")
async def delete_group(
    group_id: str, current_user: JwtPayload = Depends(get_current_user)
):
    group = await db.group.find_unique(
        where={"id": group_id}, select={"createdById": True}
    )

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nhóm không tồn tại",
        )

    if group.createdById != current_user.userId:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ người tạo nhóm mới có thể xóa",
        )

    await db.group.delete(where={"id": group_id})

    return {"message": "Đã xóa nhóm"}
