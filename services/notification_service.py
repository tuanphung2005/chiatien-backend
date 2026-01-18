from typing import Optional
from pydantic import BaseModel
from exponent_server_sdk import (
    DeviceNotRegisteredError,
    PushClient,
    PushMessage,
    PushServerError,
)

from config import get_settings

settings = get_settings()


class NotificationPayload(BaseModel):
    title: str
    body: str
    data: Optional[dict] = None


def is_valid_expo_token(token: str) -> bool:
    return token.startswith("ExponentPushToken[") or token.startswith("ExpoPushToken[")


async def send_push_notifications(
    push_tokens: list[str], payload: NotificationPayload
) -> list:
    messages = []
    for token in push_tokens:
        if not is_valid_expo_token(token):
            print(f"Push token {token} is not a valid Expo push token")
            continue

        messages.append(
            PushMessage(
                to=token,
                title=payload.title,
                body=payload.body,
                data=payload.data,
            )
        )

    if not messages:
        return []

    try:
        push_client = PushClient()
        responses = push_client.publish_multiple(messages)
        return responses
    except PushServerError as e:
        print(f"Error sending push notifications: {e}")
        return []
    except DeviceNotRegisteredError:
        return []


async def notify_group_members(
    member_push_tokens: list[str],
    expense_title: str,
    amount: float,
    paid_by_name: str,
) -> None:
    formatted_amount = f"{amount:,.0f}".replace(",", ".")
    await send_push_notifications(
        member_push_tokens,
        NotificationPayload(
            title="Chi tiêu mới 💸",
            body=f'{paid_by_name} đã thêm "{expense_title}" - {formatted_amount}₫',
            data={"type": "new_expense"},
        ),
    )
