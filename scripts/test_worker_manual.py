"""
Manual Worker Testing - Input Sendiri
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Test worker dengan input manual dari user
"""
import sys
import os
import asyncio
import logging
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.connection import connect_db, prisma
from worker import process_text_message, process_image_message

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

TEST_USER_ID = 123456789

def print_header(title: str):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_result(result: dict):
    """Print transaction result"""
    if result:
        print(f"\n✅ SUCCESS - Transaction Created")
        print(f"   ID          : {result.get('id')}")
        print(f"   Amount      : Rp {result.get('amount'):,.0f}")
        print(f"   Category    : {result.get('category')}")
        print(f"   Intent      : {result.get('intent')}")
        print(f"   Note        : {result.get('note', '-')}")
        print(f"   Created At  : {result.get('createdAt')}")
    else:
        print(f"\n❌ FAILED - Check logs for details")


async def ensure_test_user():
    """Ensure test user exists"""
    user = await prisma.user.find_unique(where={"id": TEST_USER_ID})
    
    if not user:
        logger.info(f"Creating test user {TEST_USER_ID}...")
        user = await prisma.user.create(
            data={
                "id": TEST_USER_ID,
                "username": "test_user",
                "displayName": "Test User"
            }
        )
        logger.info(f"✅ Test user created: {user.displayName}")
    
    return user


async def test_text_input():
    """Test dengan text input manual"""
    print_header("TEST: Text Message Processing")
    
    print("\n📝 Contoh input:")
    print("   - Makan siang warteg 25rb")
    print("   - Gaji bulan ini masuk 5jt")
    print("   - Transfer ke teman 100ribu")
    print("   - Bayar listrik 350rb")
    
    while True:
        text = input("\n💬 Masukkan text transaksi (atau 'q' untuk quit): ").strip()
        
        if text.lower() in ['q', 'quit', 'exit']:
            break
        
        if not text:
            print("⚠️  Text kosong, coba lagi")
            continue
        
        # Process
        print(f"\n🔄 Processing: {text}")
        result = await process_text_message(
            user_id=TEST_USER_ID,
            text=text,
            source="manual_test"
        )
        
        print_result(result)


async def test_image_input():
    """Test dengan image file path"""
    print_header("TEST: Image/OCR Processing")
    
    print("\n📷 Masukkan path ke file gambar struk")
    print("   Contoh: upload/receipts/struk.jpg")
    
    while True:
        file_path = input("\n🖼️  Path gambar (atau 'q' untuk quit): ").strip()
        
        if file_path.lower() in ['q', 'quit', 'exit']:
            break
        
        if not file_path:
            print("⚠️  Path kosong, coba lagi")
            continue
        
        if not os.path.exists(file_path):
            print(f"❌ File tidak ditemukan: {file_path}")
            continue
        
        # Create receipt record first
        print(f"\n📝 Creating receipt record...")
        
        # ✅ FIX: Hapus createdAt, user relation otomatis via userId
        receipt = await prisma.receipt.create(
            data={
                "userId": TEST_USER_ID,  # ✅ userId (camelCase)
                "filePath": file_path,
                "fileName": os.path.basename(file_path),
                "mimeType": "image/jpeg",
                "fileSize": os.path.getsize(file_path),
                # ❌ HAPUS: "createdAt": datetime.now()  # Auto-generated via uploadedAt
            }
        )
        print(f"   Receipt ID: {receipt.id}")
        
        # Process image
        print(f"\n🔄 Processing image...")
        result = await process_image_message(
            user_id=TEST_USER_ID,
            receipt_id=receipt.id,
            file_path=file_path,
            source="manual_test"
        )
        
        print_result(result)


async def main_menu():
    """Main interactive menu"""
    print_header("🧪 Worker Manual Testing Tool")
    
    # Connect to database
    print("\n🔌 Connecting to database...")
    await connect_db()
    print("✅ Connected")
    
    # Ensure test user exists
    await ensure_test_user()
    
    while True:
        print("\n" + "-" * 70)
        print("Pilih mode test:")
        print("  1. Test Text Processing")
        print("  2. Test Image/OCR Processing")
        print("  3. View Last 5 Transactions")
        print("  q. Quit")
        print("-" * 70)
        
        choice = input("\nPilihan: ").strip()
        
        if choice == '1':
            await test_text_input()
        elif choice == '2':
            await test_image_input()
        elif choice == '3':
            await view_transactions()
        elif choice.lower() in ['q', 'quit', 'exit']:
            break
        else:
            print("⚠️  Pilihan tidak valid")
    
    # Disconnect
    print("\n🔌 Disconnecting from database...")
    await prisma.disconnect()
    print("✅ Disconnected")
    
    print_header("Testing Complete - Goodbye! 👋")


async def view_transactions():
    """View last transactions"""
    print_header("Last 5 Transactions")
    
    transactions = await prisma.transaction.find_many(
        take=5,
        order_by={"createdAt": "desc"},
        include={
            "llmResponse": True
        }
    )
    
    if not transactions:
        print("\n📭 No transactions found")
        return
    
    for i, tx in enumerate(transactions, 1):
        print(f"\n{i}. Transaction #{tx.id}")
        print(f"   Amount      : Rp {tx.amount:,.0f}")
        print(f"   Category    : {tx.category}")
        print(f"   Intent      : {tx.intent}")
        print(f"   Note        : {tx.note or '-'}")
        print(f"   Source      : {tx.extra}")
        print(f"   Created     : {tx.createdAt}")
        if tx.llmResponse:
            print(f"   Input Text  : {tx.llmResponse.inputText[:50]}...")


if __name__ == "__main__":
    try:
        asyncio.run(main_menu())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()