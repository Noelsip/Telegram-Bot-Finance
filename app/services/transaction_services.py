import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple, Optional

import pandas as pd
from prisma import Prisma
from prisma.models import Transaction

_logger = logging.getLogger(__name__)

EXPORTS_DIR = Path("exports")


def _get_period_range(period: str) -> Tuple[datetime, datetime, str]:
    """Hitung rentang waktu utk periode tertentu."""
    now = datetime.utcnow()
    if period == "today":
        start = datetime(now.year, now.month, now.day)
        label = "harian (hari ini)"
    elif period == "week":
        start = now - timedelta(days=7)
        label = "mingguan (7 hari terakhir)"
    elif period == "month":
        start = now - timedelta(days=30)
        label = "bulanan (30 hari terakhir)"
    elif period == "year":
        start = now - timedelta(days=365)
        label = "tahunan (365 hari terakhir)"
    else:
        raise ValueError(f"Unknown period: {period}")
    return start, now, label


async def get_transactions_for_period(
    prisma: Prisma,
    user_id: int,
    period: str,
) -> Tuple[List[Transaction], str]:
    """Ambil transaksi user utk periode yg diminta."""
    start, end, label = _get_period_range(period)

    _logger.info(f"Fetching {label} transactions for user {user_id}")
    txs = await prisma.transaction.find_many(
        where={
            "userId": user_id,
            "createdAt": {"gte": start, "lte": end},
        },
        order={"createdAt": "asc"},
    )
    return txs, label


def build_history_summary(label: str, txs: List[Transaction]) -> str:
    """Buat ringkasan teks utk history."""
    if not txs:
        return f"Tidak ada transaksi untuk periode {label}."

    total = sum(t.amount for t in txs)
    count = len(txs)

    lines = [
        f"Ringkasan transaksi {label}:",
        f"• Jumlah transaksi: {count}",
        f"• Total nominal (tanpa arah +/-): Rp {total:,.0f}",
        "",
    ]

    lines.append("Beberapa transaksi terakhir:")
    for tx in txs[-5:]:
        dt = tx.txDate or tx.createdAt
        date_str = dt.strftime("%Y-%m-%d")
        lines.append(
            f"- {date_str}: Rp {tx.amount:,.0f} [{tx.category}]"
        )

    return "\n".join(lines)


async def create_excel_report(
    prisma: Prisma,
    user_id: int,
    period: str,
) -> Tuple[Optional[str], Optional[str]]:
    """Generate file Excel utk transaksi user di periode tertentu."""
    txs, label = await get_transactions_for_period(prisma, user_id, period)
    if not txs:
        _logger.info(f"No transactions for Excel report ({label}) user {user_id}")
        return None, None

    rows = []
    for tx in txs:
        dt = tx.txDate or tx.createdAt
        rows.append(
            {
                "Tanggal": dt.strftime("%Y-%m-%d %H:%M"),
                "Jumlah": tx.amount,
                "Kategori": tx.category,
                "Intent": tx.intent,
                "Catatan": tx.note or "",
            }
        )

    df = pd.DataFrame(rows)

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    file_name = f"transaksi_{user_id}_{period}_{timestamp}.xlsx"
    file_path = EXPORTS_DIR / file_name

    df.to_excel(file_path, index=False)
    _logger.info(f"Excel report generated: {file_path}")

    return str(file_path), file_name