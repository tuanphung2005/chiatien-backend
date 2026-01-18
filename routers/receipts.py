from fastapi import APIRouter, HTTPException, status, Depends

from database import db
from models.schemas import ReceiptParseRequest, ReceiptParseResponse, ReceiptItem
from services.auth_service import get_current_user, JwtPayload
from services.cloudinary_service import upload_image
from services.ocr_service import parse_receipt_image

router = APIRouter()


@router.post("/parse", response_model=ReceiptParseResponse)
async def parse_receipt(
    request: ReceiptParseRequest,
    current_user: JwtPayload = Depends(get_current_user),
):
    if not request.imageBase64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vui lòng chọn ảnh hóa đơn",
        )

    try:
        upload_result = await upload_image(request.imageBase64)

        parsed_data = await parse_receipt_image(request.imageBase64)

        receipt = await db.receipt.create(
            data={
                "imageUrl": upload_result.url,
                "publicId": upload_result.public_id,
                "parsedData": {
                    "items": [item.model_dump() for item in parsed_data.items],
                    "total": parsed_data.total,
                },
                "uploadedById": current_user.userId,
            }
        )

        return ReceiptParseResponse(
            receiptId=receipt.id,
            imageUrl=receipt.imageUrl,
            items=[
                ReceiptItem(name=item.name, price=item.price, quantity=item.quantity)
                for item in parsed_data.items
            ],
            total=parsed_data.total,
            message="Đã phân tích hóa đơn thành công!",
        )

    except Exception as e:
        print(f"Parse receipt error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Đã xảy ra lỗi khi phân tích hóa đơn",
        )
