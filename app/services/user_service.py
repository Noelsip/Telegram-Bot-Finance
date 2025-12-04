"""
================================================================================
FILE: app/services/user_service.py
DESKRIPSI: Service untuk operasi User
ASSIGNEE: @Backend
PRIORITY: HIGH
SPRINT: 1
================================================================================

TODO [USER-001]: get_or_create_user(user_id, username, display_name, source)
Fungsi untuk mendapatkan atau membuat user baru.

Parameter:
- user_id: BigInt (Telegram ID atau nomor WA)
- username: String optional
- display_name: String optional  
- source: String ("telegram" atau "whatsapp")

Langkah:
1. Query prisma.user.find_unique(where={"id": user_id})
2. Jika ada, return user
3. Jika tidak ada, prisma.user.create dengan data yang diberikan
4. Return user baru

TODO [USER-002]: update_user(user_id, data)
Update informasi user.

Parameter:
- user_id: BigInt
- data: dict dengan field yang mau diupdate

Langkah:
1. prisma.user.update(where={"id": user_id}, data=data)
2. Return updated user

TODO [USER-003]: get_user_by_id(user_id)
Simple fetch user by ID.

CATATAN:
- Semua operasi async (gunakan await)
- Import prisma client dari app.db.connection
================================================================================
"""
