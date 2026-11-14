from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from shop.errors import ValidationError
from shop.utils import hash_password


class UserRole(Enum):
    ADMIN = "admin"
    SELLER = "seller"
    BUYER = "buyer"


@dataclass
class User:
    id: int
    name: str
    username: str
    password: str
    role: UserRole = UserRole.BUYER

    def check_password(self, password):
        return self.password == hash_password(password)


@dataclass(frozen=True, slots=True)
class Product:
    id: int
    name: str
    purchase_price: int
    sale_price: int
    stock: int
    active: bool

    def add_stock(self, quantity):
        if quantity <= 0:
            raise ValidationError("تعداد افزایش موجودی باید مثبت باشد")
        from dataclasses import replace

        return replace(self, stock=self.stock + quantity)

    def remove_stock(self, quantity):
        if quantity <= 0:
            raise ValidationError("تعداد فروش باید مثبت باشد")
        if quantity > self.stock:
            raise ValidationError("موجودی کالا برای این فروش کافی نیست")
        from dataclasses import replace

        return replace(self, stock=self.stock - quantity)


@dataclass(frozen=True, slots=True)
class Sale:
    id: int
    user_id: int
    user_username: str
    product_id: int
    product_name: str
    quantity: int
    unit_price: int
    sold_at: datetime

    @property
    def revenue(self):
        return self.quantity * self.unit_price


@dataclass(frozen=True, slots=True)
class SalesReport:
    quantity: int
    revenue: int
    sales: tuple[Sale, ...]
