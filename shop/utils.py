import hashlib
import re
from datetime import date, timedelta, timezone

from shop.errors import ValidationError, ValidationUserError

IRAN_TIME = timezone(timedelta(hours=3, minutes=30))
MAX_AMOUNT = 10**15 - 1
MAX_STOCK = 10**9 - 1


def parse_integer(value, label, *, minimum, maximum):
    raw = str(value).strip().replace(",", "").replace("٬", "")
    if raw and raw.isdecimal() and len(raw) <= 20:
        number = int(raw)
        if minimum <= number <= maximum:
            return number
    raise ValidationError(f"{label} باید عدد صحیح بین {minimum:,} و {maximum:,} باشد")


def clean_name(value):
    name = " ".join(value.split())
    if not name or len(name) > 100:
        raise ValidationError("نام کالا باید بین ۱ تا ۱۰۰ نویسه باشد")
    return name


def parse_day(value):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValidationError("تاریخ را به شکل YYYY-MM-DD وارد کنید")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError("تاریخ واردشده معتبر نیست") from exc


def validated_role(value):
    from shop.models import UserRole

    try:
        return UserRole(value)
    except (TypeError, ValueError) as exc:
        raise ValidationUserError("نقش کاربر معتبر نیست") from exc


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()
