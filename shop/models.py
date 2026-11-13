"""Domain objects shared by both interfaces."""

from dataclasses import dataclass
from datetime import datetime

from shop.errors import ValidationError


@dataclass(frozen=True, slots=True)
class Shop:
    """A product in the shop."""

    id: int
    name: str
    purchase_price: int
    sale_price: int
    stock: int

    def add_stock(self, quantity: int) -> "Shop":
        if quantity <= 0:
            raise ValidationError("تعداد افزایش موجودی باید مثبت باشد.")
        from dataclasses import replace

        return replace(self, stock=self.stock + quantity)

    def remove_stock(self, quantity: int) -> "Shop":
        if quantity <= 0:
            raise ValidationError("تعداد فروش باید مثبت باشد.")
        if quantity > self.stock:
            raise ValidationError("موجودی کالا برای این فروش کافی نیست.")
        from dataclasses import replace

        return replace(self, stock=self.stock - quantity)


@dataclass(frozen=True, slots=True)
class Sale:
    id: int
    product_id: int
    product_name: str
    quantity: int
    unit_price: int
    sold_at: datetime

    @property
    def revenue(self) -> int:
        return self.quantity * self.unit_price


@dataclass(frozen=True, slots=True)
class SalesReport:
    quantity: int
    revenue: int
    sales: tuple[Sale, ...]
