"""
================================================================================
FILE: app/db/connection.py
DESKRIPSI: Prisma Client Singleton Connection
ASSIGNEE: @Backend
PRIORITY: HIGH
SPRINT: 1
================================================================================

TODO [DB-001]: Create Prisma Client Instance
- Import Prisma dari prisma (generated client)
- Buat singleton instance: prisma = Prisma()
- Export untuk digunakan di seluruh aplikasi

TODO [DB-002]: Connection Helper Functions
- async def connect_db(): await prisma.connect()
- async def disconnect_db(): await prisma.disconnect()
- def is_connected() -> bool: return prisma.is_connected()

CATATAN:
- Prisma client harus di-generate dulu: prisma generate
- DATABASE_URL harus ada di .env
- Format PostgreSQL: postgresql://user:password@host:port/database

SETUP PRISMA:
1. pip install prisma
2. prisma generate (generate client dari schema.prisma)
3. prisma db push (sync schema ke database)

ATAU dengan migrations:
1. prisma migrate dev --name init (create migration)
2. prisma migrate deploy (apply migration)
================================================================================
"""
