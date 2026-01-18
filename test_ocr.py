from services.ocr_service import extract_text_from_image, parse_receipt_text, get_ocr
import sys

print("Testing OCR Service...")

try:
    ocr = get_ocr()
    if ocr:
        print("✅ PaddleOCR initialized successfully")
    else:
        print("⚠️ PaddleOCR not available (using fallback/mock mode)")

    # Test regex parsing logic with dummy data
    print("\nTesting Parsing Logic...")
    dummy_lines = [
        "Phở bò tái x2 90,000đ",
        "Trà đá 5.000",
        "Tổng cộng: 95,000"
    ]
    result = parse_receipt_text(dummy_lines)
    
    parsed_items = len(result.items)
    print(f"Parsed {parsed_items} items")
    for item in result.items:
        print(f" - {item.name}: {item.quantity} x {item.price}")
    
    print(f"Total: {result.total}")

    if parsed_items == 2 and result.total == 95000:
        print("✅ Parsing logic verified")
    else:
        print("❌ Parsing logic failed")

except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
