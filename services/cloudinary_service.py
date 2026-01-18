import cloudinary
import cloudinary.uploader
from pydantic import BaseModel

from config import get_settings

settings = get_settings()

cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name,
    api_key=settings.cloudinary_api_key,
    api_secret=settings.cloudinary_api_secret,
)


class UploadResult(BaseModel):
    url: str
    public_id: str


async def upload_image(base64_data: str) -> UploadResult:
    result = cloudinary.uploader.upload(
        base64_data,
        folder="chiatien/receipts",
        resource_type="image",
    )
    return UploadResult(url=result["secure_url"], public_id=result["public_id"])


async def delete_image(public_id: str) -> None:
    cloudinary.uploader.destroy(public_id)
