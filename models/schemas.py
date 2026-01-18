from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    displayName: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    username: str
    displayName: str
    avatar: Optional[str] = None


class TokenResponse(BaseModel):
    token: str
    user: UserResponse


class GroupCreate(BaseModel):
    name: str
    emoji: Optional[str] = "💰"
    description: Optional[str] = None
    memberIds: Optional[list[str]] = None


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    emoji: Optional[str] = None
    description: Optional[str] = None


class MemberBalance(BaseModel):
    id: str
    username: Optional[str] = None
    displayName: str
    avatar: Optional[str] = None
    balance: float = 0


class GroupListItem(BaseModel):
    id: str
    name: str
    emoji: str
    description: Optional[str] = None
    memberCount: int
    expenseCount: int
    balance: float
    members: list[UserResponse]


class ParticipantCreate(BaseModel):
    userId: str
    amount: float


class ExpenseCreate(BaseModel):
    groupId: str
    amount: float
    description: str
    date: Optional[str] = None
    paidById: Optional[str] = None
    participants: Optional[list[ParticipantCreate]] = None
    receiptId: Optional[str] = None


class ExpenseSettle(BaseModel):
    participantUserId: Optional[str] = None


class ReceiptParseRequest(BaseModel):
    imageBase64: str


class ReceiptItem(BaseModel):
    name: str
    price: float
    quantity: int


class ReceiptParseResponse(BaseModel):
    receiptId: str
    imageUrl: str
    items: list[ReceiptItem]
    total: float
    message: str
