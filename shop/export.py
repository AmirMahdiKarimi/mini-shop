"""CSV output independent of either interface."""

import csv
from pathlib import Path

from shop.models import SalesReport
from shop.service import IRAN_TIME


def _spreadsheet_text(value: str) -> str:
    """Keep user-entered product names as text in spreadsheet programs."""
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value


def export_sales(report: SalesReport, path: Path) -> None:
    # UTF-8 BOM makes Persian text open correctly in common spreadsheet apps.
    with Path(path).open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(
            (
                "زمان فروش (ایران)",
                "شناسه کالا",
                "نام کالا",
                "تعداد",
                "قیمت واحد (ریال)",
                "مبلغ کل (ریال)",
                "سود ناخالص (ریال)",
            )
        )
        for sale in report.sales:
            writer.writerow(
                (
                    sale.sold_at.astimezone(IRAN_TIME).strftime("%Y-%m-%d %H:%M:%S"),
                    sale.product_id,
                    _spreadsheet_text(sale.product_name),
                    sale.quantity,
                    sale.unit_price,
                    sale.revenue,
                    sale.quantity * (sale.unit_price - sale.unit_cost),
                )
            )
        writer.writerow(("جمع", "", "", report.quantity, "", report.revenue, report.profit))
