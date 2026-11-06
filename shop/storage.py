"""SQLite storage: each write is atomic and guarded by the product version."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from shop.errors import ConflictError, NotFoundError, ValidationError
from shop.models import Sale, SalesReport, Shop


class SQLiteStore:
    def __init__(self, path: Path):
        self.path = Path(path)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL COLLATE NOCASE,
                    purchase_price INTEGER NOT NULL CHECK (purchase_price BETWEEN 0 AND 999999999999999),
                    sale_price INTEGER NOT NULL CHECK (sale_price BETWEEN 0 AND 999999999999999),
                    stock INTEGER NOT NULL CHECK (stock BETWEEN 0 AND 999999999),
                    version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
                    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))
                );
                CREATE UNIQUE INDEX IF NOT EXISTS active_product_name_idx
                    ON products(name) WHERE active = 1;
                CREATE TABLE IF NOT EXISTS sales (
                    id INTEGER PRIMARY KEY,
                    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
                    product_name TEXT NOT NULL,
                    quantity INTEGER NOT NULL CHECK (quantity > 0),
                    unit_price INTEGER NOT NULL CHECK (unit_price >= 0),
                    unit_cost INTEGER NOT NULL CHECK (unit_cost >= 0),
                    sold_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS sales_sold_at_idx ON sales(sold_at);
            """)

    @staticmethod
    def _product(row: sqlite3.Row) -> Shop:
        return Shop(
            row["id"],
            row["name"],
            row["purchase_price"],
            row["sale_price"],
            row["stock"],
            row["version"],
            bool(row["active"]),
        )

    @staticmethod
    def _sale(row: sqlite3.Row) -> Sale:
        return Sale(
            row["id"],
            row["product_id"],
            row["product_name"],
            row["quantity"],
            row["unit_price"],
            row["unit_cost"],
            datetime.fromisoformat(row["sold_at"]),
        )

    def _current(self, db: sqlite3.Connection, product_id: int) -> Shop:
        row = db.execute("SELECT * FROM products WHERE id = ? AND active = 1", (product_id,)).fetchone()
        if row is None:
            raise NotFoundError("کالای فعال پیدا نشد.")
        return self._product(row)

    @staticmethod
    def _check_version(product: Shop, version: int) -> None:
        if product.version != version:
            raise ConflictError("اطلاعات کالا تغییر کرده است؛ فهرست را تازه کنید.")

    def add_product(self, name: str, purchase_price: int, sale_price: int, stock: int) -> Shop:
        with self._connection() as db:
            try:
                cursor = db.execute(
                    "INSERT INTO products (name, purchase_price, sale_price, stock) VALUES (?, ?, ?, ?)",
                    (name, purchase_price, sale_price, stock),
                )
            except sqlite3.IntegrityError as exc:
                raise ValidationError("کالای فعالی با این نام وجود دارد.") from exc
            return self._current(db, cursor.lastrowid)

    def list_products(self, query: str = "") -> list[Shop]:
        with self._connection() as db:
            # Search in Python so %, _ and backslashes are literal characters.
            rows = db.execute("SELECT * FROM products WHERE active = 1 ORDER BY id DESC").fetchall()
            products = [self._product(row) for row in rows]
            return [p for p in products if query.casefold() in p.name.casefold()]

    def get_product(self, product_id: int) -> Shop:
        with self._connection() as db:
            return self._current(db, product_id)

    def edit_product(
        self, product_id: int, version: int, name: str, purchase_price: int, sale_price: int
    ) -> Shop:
        with self._connection() as db:
            current = self._current(db, product_id)
            self._check_version(current, version)
            try:
                changed = db.execute(
                    """UPDATE products SET name=?, purchase_price=?, sale_price=?, version=version+1
                              WHERE id=? AND version=? AND active=1""",
                    (name, purchase_price, sale_price, product_id, version),
                )
            except sqlite3.IntegrityError as exc:
                raise ValidationError("نام کالا تکراری است.") from exc
            if changed.rowcount != 1:
                raise ConflictError("اطلاعات کالا تغییر کرده است؛ فهرست را تازه کنید.")
            return self._current(db, product_id)

    def add_stock(self, product_id: int, version: int, quantity: int) -> Shop:
        with self._connection() as db:
            current = self._current(db, product_id)
            self._check_version(current, version)
            current.add_stock(quantity)
            try:
                changed = db.execute(
                    """UPDATE products SET stock=stock+?, version=version+1
                              WHERE id=? AND version=? AND active=1""",
                    (quantity, product_id, version),
                )
            except sqlite3.IntegrityError as exc:
                raise ValidationError("موجودی از حد مجاز بیشتر می‌شود.") from exc
            if changed.rowcount != 1:
                raise ConflictError("موجودی تغییر کرده است؛ دوباره بررسی کنید.")
            return self._current(db, product_id)

    def sell(self, product_id: int, version: int, quantity: int) -> Sale:
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            current = self._current(db, product_id)
            self._check_version(current, version)
            current.remove_stock(quantity)
            changed = db.execute(
                """UPDATE products SET stock=stock-?, version=version+1
                                   WHERE id=? AND version=? AND active=1 AND stock>=?""",
                (quantity, product_id, version, quantity),
            )
            if changed.rowcount != 1:
                raise ConflictError("موجودی تغییر کرده است؛ دوباره بررسی کنید.")
            sold_at = datetime.now(timezone.utc).isoformat(timespec="microseconds")
            cursor = db.execute(
                """INSERT INTO sales
                (product_id, product_name, quantity, unit_price, unit_cost, sold_at)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (product_id, current.name, quantity, current.sale_price, current.purchase_price, sold_at),
            )
            return Sale(
                cursor.lastrowid,
                product_id,
                current.name,
                quantity,
                current.sale_price,
                current.purchase_price,
                datetime.fromisoformat(sold_at),
            )

    def archive(self, product_id: int, version: int) -> None:
        with self._connection() as db:
            current = self._current(db, product_id)
            self._check_version(current, version)
            changed = db.execute(
                "UPDATE products SET active=0, version=version+1 WHERE id=? AND version=?",
                (product_id, version),
            )
            if changed.rowcount != 1:
                raise ConflictError("اطلاعات کالا تغییر کرده است؛ فهرست را تازه کنید.")

    def report(self, begin: datetime, finish: datetime) -> SalesReport:
        with self._connection() as db:
            rows = db.execute(
                """SELECT * FROM sales WHERE sold_at >= ? AND sold_at < ?
                                 ORDER BY sold_at DESC, id DESC""",
                (begin.isoformat(timespec="microseconds"), finish.isoformat(timespec="microseconds")),
            ).fetchall()
            sales = tuple(self._sale(row) for row in rows)
            return SalesReport(
                sum(s.quantity for s in sales),
                sum(s.revenue for s in sales),
                sum(s.quantity * s.unit_cost for s in sales),
                sales,
            )
