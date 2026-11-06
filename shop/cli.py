"""Interactive text interface using the same service as the GUI."""

from datetime import datetime
from pathlib import Path

from shop.errors import ShopError
from shop.export import export_sales
from shop.service import IRAN_TIME, ShopService


def _choose(service: ShopService):
    products = service.list_products()
    if not products:
        print("هنوز کالایی ثبت نشده است.")
        return None
    for product in products:
        print(f"{product.id}: {product.name} | موجودی {product.stock} | فروش {product.sale_price:,} ریال")
    product_id = int(input("شناسهٔ کالا: ").strip())
    return service.get_product(product_id)


def run(service: ShopService) -> None:
    menu = "\n۱ افزودن | ۲ موجودی | ۳ فروش | ۴ جست‌وجو | ۵ گزارش | ۶ ویرایش | ۷ بایگانی | ۰ خروج"
    while True:
        print(menu)
        choice = input("انتخاب: ").strip()
        if choice in ("0", "۰"):
            return
        try:
            if choice in ("1", "۱"):
                product = service.add_product(
                    input("نام: "), input("قیمت خرید (ریال): "), input("قیمت فروش (ریال): "), input("تعداد: ")
                )
                print(f"کالا با شناسهٔ {product.id} ثبت شد.")
            elif choice in ("2", "۲"):
                product = _choose(service)
                if product:
                    updated = service.add_stock(product.id, input("تعداد افزایش: "))
                    print(f"موجودی جدید: {updated.stock}")
            elif choice in ("3", "۳"):
                product = _choose(service)
                if product:
                    sale = service.sell(product.id, input("تعداد فروش: "))
                    print(f"فروش ثبت شد. مبلغ: {sale.revenue:,} ریال")
            elif choice in ("4", "۴"):
                for product in service.list_products(input("بخشی از نام: ")):
                    print(
                        f"{product.id}: {product.name} | موجودی {product.stock} | فروش {product.sale_price:,}"
                    )
            elif choice in ("5", "۵"):
                today = datetime.now(IRAN_TIME).date().isoformat()
                start = input(f"از تاریخ YYYY-MM-DD [{today}]: ").strip() or today
                end = input(f"تا تاریخ YYYY-MM-DD [{today}]: ").strip() or today
                report = service.report(start, end)
                for sale in report.sales:
                    print(
                        f"{sale.sold_at.astimezone(IRAN_TIME):%Y-%m-%d %H:%M} | "
                        f"{sale.product_name} | {sale.quantity} × {sale.unit_price:,}"
                    )
                print(f"تعداد: {report.quantity} | درآمد: {report.revenue:,} ریال")
                export_path = input("مسیر خروجی CSV (خالی = بدون خروجی): ").strip()
                if export_path:
                    export_sales(report, Path(export_path))
                    print("فایل گزارش ذخیره شد.")
            elif choice in ("6", "۶"):
                product = _choose(service)
                if product:
                    updated = service.edit_product(
                        product.id,
                        input(f"نام [{product.name}]: ").strip() or product.name,
                        input(f"خرید [{product.purchase_price}]: ").strip() or product.purchase_price,
                        input(f"فروش [{product.sale_price}]: ").strip() or product.sale_price,
                    )
                    print(f"کالای {updated.name} ویرایش شد.")
            elif choice in ("7", "۷"):
                product = _choose(service)
                if product and input("برای بایگانی «بله» بنویسید: ").strip() == "بله":
                    service.archive(product.id)
                    print("بایگانی شد.")
            else:
                print("گزینهٔ نامعتبر.")
        except (ShopError, ValueError) as exc:
            print(f"خطا: {exc if isinstance(exc, ShopError) else 'شناسه باید عدد صحیح باشد.'}")
        except OSError as exc:
            print(f"ذخیرهٔ فایل انجام نشد: {exc}")
