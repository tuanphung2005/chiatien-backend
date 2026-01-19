from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query

from database import db
from models.schemas import ExpenseCreate, ExpenseSettle, ExpenseUpdate
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
            "paidBy": True,
            "participants": {
                "include": {"user": True}
            },
            "group": True,
            "receipt": True,
        },
        order={"date": "desc"},
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
            "paidBy": True,
            "participants": {
                "include": {"user": True}
            },
            "group": {
                "include": {
                    "members": {
                        "include": {"user": True}
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


@router.put("/{expense_id}")
async def update_expense(
    expense_id: str,
    request: ExpenseUpdate,
    current_user: JwtPayload = Depends(get_current_user)
):
    expense = await db.expense.find_unique(
        where={"id": expense_id},
        include={"participants": True}
    )

    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chi tiêu không tồn tại",
        )

    if expense.paidById != current_user.userId:
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ người trả tiền mới có thể sửa",
        )

    # If updating amount, must update participants
    if request.amount is not None and request.participants is None:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Khi cập nhật số tiền, vui lòng gửi kèm danh sách người chia tiền",
        )

    update_data = {}
    if request.amount is not None:
        update_data["amount"] = request.amount
    if request.description is not None:
        update_data["description"] = request.description
    if request.date is not None:
        update_data["date"] = request.date
    if request.paidById is not None:
        update_data["paidById"] = request.paidById
    if request.receiptId is not None:
        update_data["receiptId"] = request.receiptId
    
    # Handle participants update
    if request.participants:
        # Delete old participants
        await db.expenseparticipant.delete_many(where={"expenseId": expense_id})
        
        # Determine payer ID (new or old)
        payer_id = request.paidById or expense.paidById

        # Create new participants
        # Note: avoiding create_many if not supported, but typical prisma client supports it
        # If create_many is an issue, loop and create. But let's try create_many or loop.
        # Python prisma client usually supports create_many.
        
        for p in request.participants:
            await db.expenseparticipant.create(
                data={
                    "expenseId": expense_id,
                    "userId": p.userId,
                    "amount": p.amount,
                    "settled": p.userId == payer_id
                }
            )
            
    elif request.paidById and request.paidById != expense.paidById:
        # Payer changed, re-evaluate settled status
        await db.expenseparticipant.update_many(
            where={"expenseId": expense_id},
            data={"settled": False}
        )
        await db.expenseparticipant.update_many(
            where={"expenseId": expense_id, "userId": request.paidById},
            data={"settled": True}
        )

    
    if update_data:
        expense = await db.expense.update(
            where={"id": expense_id},
            data=update_data,
            include={
                "paidBy": True,
                "participants": {
                    "include": {"user": True}
                },
                "group": True,
                "receipt": True,
            }
        )
    else:
        # Refetch if we only updated participants but not expense fields
        expense = await db.expense.find_unique(
            where={"id": expense_id},
             include={
                "paidBy": True,
                "participants": {
                    "include": {"user": True}
                },
                "group": True,
                "receipt": True,
            }
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
