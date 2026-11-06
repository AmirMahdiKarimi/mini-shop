"""Input validation and use cases, independent of Tkinter and input()."""

import re
from datetime import date, datetime, time, timedelta, timezone

from shop.errors import ValidationError
from shop.models import SalesReport, Shop
from shop.storage import SQLiteStore

IRAN_TIME = timezone(timedelta(hours=3, minutes=30))
MAX_AMOUNT = 10**15 - 1
MAX_STOCK = 10**9 - 1


def parse_integer(value: str | int, label: str, *, minimum: int, maximum: int) -> int:
    raw = str(value).strip().replace(",", "").replace("٬", "")
    if raw and raw.isdecimal() and len(raw) <= 20:
        number = int(raw)
        if minimum <= number <= maximum:
            return number
    raise ValidationError(f"{label} باید عدد صحیح بین {minimum:,} و {maximum:,} باشد.")


def clean_name(value: str) -> str:
    name = " ".join(value.split())
    if not name or len(name) > 100:
        raise ValidationError("نام کالا باید بین ۱ تا ۱۰۰ نویسه باشد.")
    return name


def parse_day(value: str) -> date:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValidationError("تاریخ را به شکل YYYY-MM-DD وارد کنید.")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError("تاریخ واردشده معتبر نیست.") from exc


class ShopService:
    def __init__(self, store: SQLiteStore):
        self.store = store
        self.store.initialize()

    def add_product(
        self, name: str, purchase_price: str | int, sale_price: str | int, stock: str | int
    ) -> Shop:
        return self.store.add_product(
            clean_name(name),
            parse_integer(purchase_price, "قیمت خرید", minimum=0, maximum=MAX_AMOUNT),
            parse_integer(sale_price, "قیمت فروش", minimum=0, maximum=MAX_AMOUNT),
            parse_integer(stock, "تعداد اولیه", minimum=0, maximum=MAX_STOCK),
        )

    def list_products(self, query: str = "") -> list[Shop]:
        return self.store.list_products(" ".join(query.split()))

    def get_product(self, product_id: int) -> Shop:
        return self.store.get_product(product_id)

    def edit_product(
        self, product_id: int, name: str, purchase_price: str | int, sale_price: str | int
    ) -> Shop:
        return self.store.edit_product(
            product_id,
            clean_name(name),
            parse_integer(purchase_price, "قیمت خرید", minimum=0, maximum=MAX_AMOUNT),
            parse_integer(sale_price, "قیمت فروش", minimum=0, maximum=MAX_AMOUNT),
        )

    def add_stock(self, product_id: int, quantity: str | int) -> Shop:
        return self.store.add_stock(
            product_id, parse_integer(quantity, "تعداد افزایش", minimum=1, maximum=MAX_STOCK)
        )

    def sell(self, product_id: int, quantity: str | int):
        return self.store.sell(
            product_id, parse_integer(quantity, "تعداد فروش", minimum=1, maximum=MAX_STOCK)
        )

    def archive(self, product_id: int) -> None:
        self.store.archive(product_id)

    def report(self, start: str, end: str) -> SalesReport:
        first, last = parse_day(start), parse_day(end)
        if first > last:
            raise ValidationError("تاریخ شروع نباید بعد از پایان باشد.")
        if first == date.min:
            raise ValidationError("تاریخ شروع خارج از بازهٔ پشتیبانی است.")
        if last == date.max:
            raise ValidationError("تاریخ پایان خارج از بازهٔ پشتیبانی است.")
        # Half-open UTC bounds preserve both requested local calendar days.
        begin = datetime.combine(first, time.min, IRAN_TIME).astimezone(timezone.utc)
        finish = datetime.combine(last + timedelta(days=1), time.min, IRAN_TIME).astimezone(timezone.utc)
        return self.store.report(begin, finish)
