"""Excel sales report shared by both interfaces."""

from pathlib import Path

from shop.models import SalesReport
from shop.service import IRAN_TIME


def export_sales(report: SalesReport, path: Path) -> None:
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
    except ModuleNotFoundError as exc:
        raise RuntimeError("برای خروجی Excel، ابتدا openpyxl را نصب کنید.") from exc

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "گزارش فروش"
    sheet.sheet_view.rightToLeft = True
    sheet.append(
        (
            "زمان فروش (ایران)",
            "شناسه کالا",
            "نام کالا",
            "تعداد",
            "قیمت واحد (ریال)",
            "مبلغ کل (ریال)",
        )
    )
    for sale in report.sales:
        sheet.append(
            (
                sale.sold_at.astimezone(IRAN_TIME).strftime("%Y-%m-%d %H:%M:%S"),
                sale.product_id,
                sale.product_name,
                sale.quantity,
                sale.unit_price,
                sale.revenue,
            )
        )
        # Product names that begin with "=" must stay text, not Excel formulas.
        sheet.cell(sheet.max_row, 3).data_type = "s"
    sheet.append(("جمع", "", "", report.quantity, "", report.revenue))

    for column, width in {"A": 23, "B": 14, "C": 32, "D": 12, "E": 21, "F": 21}.items():
        sheet.column_dimensions[column].width = width
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:F{sheet.max_row - 1}"
    for cell in (*sheet[1], *sheet[sheet.max_row]):
        cell.fill = PatternFill("solid", fgColor="DCECF4")
        cell.font = Font(name="Tahoma", bold=True, color="19324A")
    for row in sheet:
        for cell in row:
            cell.alignment = Alignment(horizontal="right")
    for row in sheet.iter_rows(min_row=2, min_col=4, max_col=6):
        for cell in row:
            cell.number_format = "#,##0"
    workbook.save(Path(path))
