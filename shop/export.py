from pathlib import Path

from shop.utils import IRAN_TIME


def export_sales(report, path):
    try:
        from openpyxl import Workbook
    except ModuleNotFoundError as exc:
        raise RuntimeError("برای خروجی Excel، ابتدا openpyxl را نصب کنید") from exc

    workbook = Workbook()
    sheet = workbook.active
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
        sheet.cell(sheet.max_row, 3).data_type = "s"
    sheet.append(("جمع", "", "", report.quantity, "", report.revenue))
    workbook.save(Path(path))
