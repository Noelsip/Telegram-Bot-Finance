from typing import AsyncGenerator

from prisma import Prisma

# Singleton Prisma client (1 instance untuk seluruh app)
prisma = Prisma()


async def connect_db() -> None:
    """
    konek ke database
    """
    await prisma.connect()


async def get_db() -> AsyncGenerator[Prisma, None]:
    """
    Dependency async untuk FastAPI (kalau nanti kamu pakai).
    Contoh:
        async def handler(db: Prisma = Depends(get_db)):
            ...
    """
    yield prisma