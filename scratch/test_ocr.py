import asyncio
from dotenv import load_dotenv
load_dotenv("backend/.env")
from app.services.expense_ocr import scan_receipt_text

async def main():
    text = """
    Walmart Supercenter
    Date: 2026-06-14
    1x Office Paper $5.99
    1x Printer Ink $29.99
    Tax: $2.50
    Total: $38.48
    Payment: VISA **** 1234
    """
    print("Testing OCR...")
    result = await scan_receipt_text(text)
    print("Result:", result)

if __name__ == "__main__":
    asyncio.run(main())
