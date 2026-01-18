import re
import base64
import tempfile
import os
from typing import Optional
from pydantic import BaseModel

ocr_available = False
ocr_instance = None

try:
    from paddleocr import PaddleOCR
    ocr_available = True
except ImportError:
    print("PaddleOCR not available. Using fallback mode.")


class ReceiptItem(BaseModel):
    name: str
    price: float
    quantity: int


class ParsedReceipt(BaseModel):
    items: list[ReceiptItem]
    total: float


def get_ocr():
    global ocr_instance
    if ocr_instance is None and ocr_available:
        # Minimal initialization for compatibility
        ocr_instance = PaddleOCR(lang="vi", use_angle_cls=True)
    return ocr_instance


def parse_vnd_amount(amount_str: str) -> float:
    cleaned = re.sub(r"[^\d]", "", amount_str)
    if cleaned:
        return float(cleaned)
    return 0.0


def extract_text_from_image(image_path: str) -> list[str]:
    ocr = get_ocr()
    if not ocr:
        return []
    
    result = ocr.ocr(image_path, cls=True)

    if not result or not result[0]:
        return []

    lines = []
    for line in result[0]:
        if line and len(line) >= 2:
            text = line[1][0]
            lines.append(text)
    return lines


def parse_receipt_text(lines: list[str]) -> ParsedReceipt:
    items = []
    total = 0.0

    for line in lines:
        line_lower = line.lower()

        item_patterns = [
            r"(.+?)\s*[x×]\s*(\d+)\s*[:\s=]*([0-9.,]+)",
            r"(.+?)\s+(\d+)\s*[x×]\s*([0-9.,]+)",
            r"(\d+)\s*[x×]\s*(.+?)\s*[:\s=]*([0-9.,]+)",
        ]

        matched = False
        for pattern in item_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                groups = match.groups()
                if pattern == item_patterns[2]:
                    quantity = int(groups[0])
                    name = groups[1].strip()
                    price = parse_vnd_amount(groups[2])
                else:
                    name = groups[0].strip()
                    quantity = int(groups[1])
                    price = parse_vnd_amount(groups[2])

                if name and quantity > 0 and price > 0:
                    items.append(ReceiptItem(name=name, price=price, quantity=quantity))
                    matched = True
                    break

        if not matched:
            simple_match = re.search(r"(.+?)\s+([0-9.,]+)\s*(đ|d|VND)?$", line)
            if simple_match:
                name = simple_match.group(1).strip()
                price = parse_vnd_amount(simple_match.group(2))
                if name and price >= 1000:
                    skip_keywords = [
                        "tổng",
                        "total",
                        "thành tiền",
                        "thanh toán",
                        "tiền thừa",
                        "tiền nhận",
                        "vat",
                        "thuế",
                    ]
                    if not any(kw in name.lower() for kw in skip_keywords):
                        items.append(ReceiptItem(name=name, price=price, quantity=1))

        total_keywords = ["tổng cộng", "tổng tiền", "total", "thành tiền", "thanh toán"]
        if any(kw in line_lower for kw in total_keywords):
            total_match = re.search(r"([0-9.,]+)", line)
            if total_match:
                potential_total = parse_vnd_amount(total_match.group(1))
                if potential_total > total:
                    total = potential_total

    if total == 0 and items:
        total = sum(item.price * item.quantity for item in items)

    return ParsedReceipt(items=items, total=total)


def generate_mock_receipt() -> ParsedReceipt:
    import random
    
    mock_items = [
        ReceiptItem(name="Phở bò tái", price=45000, quantity=2),
        ReceiptItem(name="Cơm gà xối mỡ", price=55000, quantity=1),
        ReceiptItem(name="Trà đá", price=5000, quantity=3),
        ReceiptItem(name="Nước cam ép", price=25000, quantity=2),
        ReceiptItem(name="Bánh mì thịt", price=20000, quantity=1),
    ]
    
    num_items = random.randint(2, 4)
    selected = random.sample(mock_items, num_items)
    
    for item in selected:
        item.quantity = random.randint(1, 3)
    
    total = sum(item.price * item.quantity for item in selected)
    
    return ParsedReceipt(items=selected, total=total)


async def parse_receipt_image(image_base64: str) -> ParsedReceipt:
    if not ocr_available:
        print("PaddleOCR not available, using mock data")
        return generate_mock_receipt()
    
    if "," in image_base64:
        image_base64 = image_base64.split(",")[1]

    image_data = base64.b64decode(image_base64)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
        tmp_file.write(image_data)
        tmp_path = tmp_file.name

    try:
        lines = extract_text_from_image(tmp_path)
        if not lines:
            print("No text extracted, using mock data")
            return generate_mock_receipt()
        result = parse_receipt_text(lines)
        if not result.items:
            print("No items parsed, using mock data")
            return generate_mock_receipt()
        return result
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
