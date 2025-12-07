"""
Worker Testing Entry Point
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Temporary entry point untuk testing worker tanpa bot
"""
import asyncio
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

TEST_USER_ID = 123456789

async def ensure_test_user_exists():
    """Create test user jika belum ada"""
    from app.db.connection import prisma
    
    try:
        # Check if user exists
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
        else:
            logger.info(f"✅ Test user already exists: {user.displayName}")
            
    except Exception as e:
        logger.error(f"Failed to create test user: {e}")
        raise


async def test_worker():
    """Test worker functionality"""
    from app.db.connection import connect_db, prisma
    from worker import process_text_message
    
    logger.info("=" * 70)
    logger.info("WORKER TEST MODE")
    logger.info("=" * 70)
    
    # Connect to database
    logger.info("Connecting to database...")
    await connect_db()
    logger.info("✅ Database connected!")
    
    # Run migrations
    logger.info("Running database migrations...")
    os.system("python -m prisma migrate deploy")
    
    # Ensure test user exists
    await ensure_test_user_exists()
    
    # Test worker dengan sample data
    test_cases = [
        "Makan siang warteg 25rb",
        "Gaji bulan ini masuk 5jt",
        "Transfer ke teman 100rb"
    ]
    
    logger.info("\n" + "=" * 70)
    logger.info("Testing Worker with Sample Data")
    logger.info("=" * 70)
    
    for i, text in enumerate(test_cases, 1):
        logger.info(f"\n📝 Test {i}/{len(test_cases)}: {text}")
        
        result = await process_text_message(
            user_id=TEST_USER_ID,
            text=text,
            source="docker_test"
        )
        
        if result:
            logger.info(f"   ✅ SUCCESS - Transaction ID: {result['id']}")
            logger.info(f"   Amount: Rp {result.get('amount'):,.0f}")
            logger.info(f"   Category: {result.get('category')}")
        else:
            logger.info(f"   ❌ FAILED")
    
    logger.info("\n" + "=" * 70)
    logger.info("Worker test complete!")
    logger.info("=" * 70)
    
    # Keep container running
    logger.info("\n⏸️  Keeping container alive... (Press Ctrl+C to stop)")
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await prisma.disconnect()


async def interactive_mode():
    """Interactive testing mode"""
    from app.db.connection import connect_db, prisma
    from worker import process_text_message
    
    logger.info("=" * 70)
    logger.info("WORKER INTERACTIVE MODE")
    logger.info("=" * 70)
    
    await connect_db()
    logger.info("✅ Database connected!")
    
    # Ensure test user exists
    await ensure_test_user_exists()
    
    logger.info("\n📝 Enter transaction text (or 'quit' to exit):")
    
    # Simulate interactive input (dalam Docker akan auto-test)
    # Untuk testing real interactive, jalankan di luar Docker
    await test_worker()


if __name__ == "__main__":
    mode = os.getenv("WORKER_MODE", "test")  # test atau interactive
    
    try:
        if mode == "interactive":
            asyncio.run(interactive_mode())
        else:
            asyncio.run(test_worker())
    except KeyboardInterrupt:
        logger.info("\n👋 Worker stopped by user")
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)