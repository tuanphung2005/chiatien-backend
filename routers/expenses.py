from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query

from database import db
from models.schemas import ExpenseCreate, ExpenseSettle
from services.auth_service import get_current_user, JwtPayload
from services.notification_service import notify_group_members

router = APIRouter()


@router.get("")
async def get_expenses(
    groupId: Optional[str] = Query(None),
    current_user: JwtPayload = Depends(get_current_user),
):
    if groupId:
        where_clause = {"groupId": groupId}
    else:
        where_clause = {"group": {"members": {"some": {"userId": current_user.userId}}}}

    expenses = await db.expense.find_many(
        where=where_clause,
        include={
            "paidBy": {"select": {"id": True, "displayName": True, "avatar": True}},
            "participants": {
                "include": {"user": {"select": {"id": True, "displayName": True}}}
            },
            "group": {"select": {"id": True, "name": True, "emoji": True}},
            "receipt": True,
        },
        order_by={"date": "desc"},
    )

    return expenses


@router.post("")
async def create_expense(
    request: ExpenseCreate, current_user: JwtPayload = Depends(get_current_user)
):
    if not request.groupId or not request.amount or not request.description:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vui lòng điền đầy đủ thông tin",
        )

    actual_payer_id = request.paidById or current_user.userId

    participant_data = request.participants
    if not participant_data or len(participant_data) == 0:
        group = await db.group.find_unique(
            where={"id": request.groupId}, include={"members": True}
        )

        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nhóm không tồn tại",
            )

        split_amount = request.amount / len(group.members)
        participant_data = [
            {"userId": m.userId, "amount": split_amount} for m in group.members
        ]

    expense = await db.expense.create(
        data={
            "groupId": request.groupId,
            "amount": request.amount,
            "description": request.description,
            "date": request.date if request.date else None,
            "paidById": actual_payer_id,
            "receiptId": request.receiptId,
            "participants": {
                "create": [
                    {
                        "userId": p["userId"] if isinstance(p, dict) else p.userId,
                        "amount": p["amount"] if isinstance(p, dict) else p.amount,
                        "settled": (p["userId"] if isinstance(p, dict) else p.userId)
                        == actual_payer_id,
                    }
                    for p in participant_data
                ]
            },
        },
        include={
            "paidBy": {"select": {"id": True, "displayName": True}},
            "participants": {
                "include": {"user": {"select": {"id": True, "displayName": True}}}
            },
            "group": {
                "include": {
                    "members": {
                        "include": {"user": {"select": {"id": True, "pushToken": True}}}
                    }
                }
            },
        },
    )

    other_member_tokens = [
        m.user.pushToken
        for m in expense.group.members
        if m.user.id != current_user.userId and m.user.pushToken
    ]

    if other_member_tokens:
        await notify_group_members(
            other_member_tokens,
            expense.description,
            expense.amount,
            expense.paidBy.displayName,
        )

    return expense


@router.delete("/{expense_id}")
async def delete_expense(
    expense_id: str, current_user: JwtPayload = Depends(get_current_user)
):
    expense = await db.expense.find_unique(
        where={"id": expense_id}, select={"paidById": True}
    )

    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chi tiêu không tồn tại",
        )

    if expense.paidById != current_user.userId:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ người trả tiền mới có thể xóa",
        )

    await db.expense.delete(where={"id": expense_id})

    return {"message": "Đã xóa chi tiêu"}


@router.patch("/{expense_id}")
async def settle_expense(
    expense_id: str,
    request: ExpenseSettle,
    current_user: JwtPayload = Depends(get_current_user),
):
    participant_user_id = request.participantUserId or current_user.userId

    await db.expenseparticipant.update_many(
        where={"expenseId": expense_id, "userId": participant_user_id},
        data={"settled": True},
    )

    return {"message": "Đã thanh toán"}
