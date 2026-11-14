import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from shop.errors import NotFoundError, NotFoundUserError, ValidationError, ValidationUserError
from shop.models import Product, Sale, SalesReport, User, UserRole


class SQLiteStore:
    def __init__(self, path):
        self.path = Path(path)

    @contextmanager
    def _connection(self):
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self):
        with self._connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL COLLATE NOCASE,
                    username TEXT NOT NULL COLLATE NOCASE,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS user_username_idx
                    ON users(username);
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL COLLATE NOCASE,
                    purchase_price INTEGER NOT NULL CHECK (purchase_price BETWEEN 0 AND 999999999999999),
                    sale_price INTEGER NOT NULL CHECK (sale_price BETWEEN 0 AND 999999999999999),
                    stock INTEGER NOT NULL CHECK (stock BETWEEN 0 AND 999999999),
                    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))
                );
                CREATE UNIQUE INDEX IF NOT EXISTS active_product_name_idx
                    ON products(name) WHERE active = 1;
                CREATE TABLE IF NOT EXISTS sales (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
                    user_username TEXT NOT NULL,
                    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
                    product_name TEXT NOT NULL,
                    quantity INTEGER NOT NULL CHECK (quantity > 0),
                    unit_price INTEGER NOT NULL CHECK (unit_price >= 0),
                    sold_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS sales_sold_at_idx ON sales(sold_at);
            """)

    @staticmethod
    def _user(row):
        return User(
            row["id"],
            row["name"],
            row["username"],
            row["password"],
            UserRole(row["role"]),
        )

    @staticmethod
    def _product(row):
        return Product(
            row["id"],
            row["name"],
            row["purchase_price"],
            row["sale_price"],
            row["stock"],
            bool(row["active"]),
        )

    @staticmethod
    def _sale(row):
        return Sale(
            row["id"],
            row["user_id"],
            row["user_username"],
            row["product_id"],
            row["product_name"],
            row["quantity"],
            row["unit_price"],
            datetime.fromisoformat(row["sold_at"]),
        )

    def get_user_by_username(self, username):
        with self._connection() as db:
            user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            if user:
                return self._user(user)
            raise NotFoundUserError("کاربر یافت نشد")

    def add_user(self, name, username, password, role):
        with self._connection() as db:
            try:
                cursor = db.execute(
                    "INSERT INTO users (name, username, password, role) VALUES (?, ?, ?, ?)",
                    (name, username, password, role.value),
                )
            except sqlite3.IntegrityError as exc:
                raise ValidationUserError("این یوزرنیم از قبل وجود دارد") from exc
            return self._current_user(db, cursor.lastrowid)

    def list_users(self, query=""):
        with self._connection() as db:
            rows = db.execute("SELECT * FROM users ORDER BY id DESC").fetchall()
            users = [self._user(row) for row in rows]
            return [u for u in users if query.casefold() in u.username.casefold()]

    def _current_user(self, db, user_id):
        row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            raise NotFoundError("کاربر پیدا نشد")
        return self._user(row)

    def _current(self, db, product_id):
        row = db.execute("SELECT * FROM products WHERE id = ? AND active = 1", (product_id,)).fetchone()
        if row is None:
            raise NotFoundError("کالای فعال پیدا نشد")
        return self._product(row)

    def add_product(self, name, purchase_price, sale_price, stock):
        with self._connection() as db:
            try:
                cursor = db.execute(
                    "INSERT INTO products (name, purchase_price, sale_price, stock) VALUES (?, ?, ?, ?)",
                    (name, purchase_price, sale_price, stock),
                )
            except sqlite3.IntegrityError as exc:
                raise ValidationError("کالای فعالی با این نام وجود دارد") from exc
            return self._current(db, cursor.lastrowid)

    def list_products(self, query=""):
        with self._connection() as db:
            rows = db.execute("SELECT * FROM products WHERE active = 1 ORDER BY id DESC").fetchall()
            products = [self._product(row) for row in rows]
            return [p for p in products if query.casefold() in p.name.casefold()]

    def get_product(self, product_id):
        with self._connection() as db:
            return self._current(db, product_id)

    def edit_product(self, product_id, name, purchase_price, sale_price):
        with self._connection() as db:
            try:
                changed = db.execute(
                    """UPDATE products SET name=?, purchase_price=?, sale_price=?
                       WHERE id=? AND active=1""",
                    (name, purchase_price, sale_price, product_id),
                )
            except sqlite3.IntegrityError as exc:
                raise ValidationError("نام کالا تکراری است") from exc
            if changed.rowcount != 1:
                raise NotFoundError("کالای فعال پیدا نشد")
            return self._current(db, product_id)

    def add_stock(self, product_id, quantity):
        with self._connection() as db:
            try:
                changed = db.execute(
                    "UPDATE products SET stock=stock+? WHERE id=? AND active=1",
                    (quantity, product_id),
                )
            except sqlite3.IntegrityError as exc:
                raise ValidationError("موجودی از حد مجاز بیشتر می‌شود") from exc
            if changed.rowcount != 1:
                raise NotFoundError("کالای فعال پیدا نشد")
            return self._current(db, product_id)

    def sell(self, user_id, product_id, quantity):
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            current = self._current(db, product_id)
            current_user = self._current_user(db, user_id)
            current.remove_stock(quantity)
            changed = db.execute(
                "UPDATE products SET stock=stock-? WHERE id=? AND active=1 AND stock>=?",
                (quantity, product_id, quantity),
            )
            if changed.rowcount != 1:
                raise ValidationError("موجودی کالا برای این فروش کافی نیست")
            sold_at = datetime.now(timezone.utc).isoformat(timespec="microseconds")
            cursor = db.execute(
                """INSERT INTO sales
                   (user_id, user_username, product_id, product_name, quantity, unit_price, sold_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    user_id,
                    current_user.username,
                    product_id,
                    current.name,
                    quantity,
                    current.sale_price,
                    sold_at,
                ),
            )
            return Sale(
                cursor.lastrowid,
                user_id,
                current_user.username,
                product_id,
                current.name,
                quantity,
                current.sale_price,
                datetime.fromisoformat(sold_at),
            )

    def archive(self, product_id):
        with self._connection() as db:
            changed = db.execute(
                "UPDATE products SET active=0 WHERE id=? AND active=1",
                (product_id,),
            )
            if changed.rowcount != 1:
                raise NotFoundError("کالای فعال پیدا نشد")

    def report(self, begin, finish):
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
                sales,
            )
