import csv
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from shop.errors import ConflictError, ValidationError
from shop.export import export_sales
from shop.service import IRAN_TIME, ShopService
from shop.storage import SQLiteStore


class ShopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "shop.db"
        self.service = ShopService(SQLiteStore(self.path))

    def test_sale_updates_stock_and_preserves_price_snapshot(self):
        product = self.service.add_product("شیر", 50, 80, 5)
        sale = self.service.sell(product.id, product.version, 2)
        self.assertEqual(self.service.get_product(product.id).stock, 3)
        updated = self.service.get_product(product.id)
        self.service.edit_product(product.id, updated.version, "شیر", 60, 100)
        day = sale.sold_at.astimezone(IRAN_TIME).date().isoformat()
        report = self.service.report(day, day)
        self.assertEqual((report.quantity, report.revenue, report.profit), (2, 160, 60))

    def test_insufficient_stock_has_no_partial_sale(self):
        product = self.service.add_product("چای", 10, 20, 1)
        with self.assertRaises(ValidationError):
            self.service.sell(product.id, product.version, 2)
        self.assertEqual(self.service.get_product(product.id).stock, 1)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM sales").fetchone()[0], 0)

    def test_stale_version_cannot_overwrite_or_sell(self):
        product = self.service.add_product("برنج", 10, 20, 4)
        self.service.add_stock(product.id, product.version, 1)
        with self.assertRaises(ConflictError):
            self.service.sell(product.id, product.version, 1)
        with self.assertRaises(ConflictError):
            self.service.edit_product(product.id, product.version, "برنج", 10, 30)
        self.assertEqual(self.service.get_product(product.id).stock, 5)

    def test_archive_allows_remaining_stock_and_preserves_sales(self):
        product = self.service.add_product("نان", 5, 10, 3)
        sale = self.service.sell(product.id, product.version, 1)
        self.service.archive(product.id, self.service.get_product(product.id).version)
        self.assertEqual(self.service.list_products(), [])
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(
                db.execute("SELECT stock, active FROM products WHERE id = ?", (product.id,)).fetchone(),
                (2, 0),
            )
        day = sale.sold_at.astimezone(IRAN_TIME).date().isoformat()
        self.assertEqual(self.service.report(day, day).revenue, 10)

    def test_input_and_search(self):
        self.service.add_product("  چای   سبز ", "۱٬۰۰۰", "2,000", 3)
        self.assertEqual(self.service.list_products("چای سبز")[0].name, "چای سبز")
        self.assertEqual(self.service.list_products("%"), [])
        with self.assertRaises(ValidationError):
            self.service.add_product("چای سبز", 1, 2, 1)
        with self.assertRaises(ValidationError):
            self.service.add_product("قند", "1.5", 2, 1)
        with self.assertRaises(ValidationError):
            self.service.report("2026-02-30", "2026-03-01")
        with self.assertRaises(ValidationError):
            self.service.report("2026-03-02", "2026-03-01")
        with self.assertRaises(ValidationError):
            self.service.report("0001-01-01", "0001-01-02")

    def test_zero_stock_archive_and_reuse_name(self):
        first = self.service.add_product("آب", 1, 2, 0)
        self.service.archive(first.id, first.version)
        second = self.service.add_product("آب", 3, 4, 2)
        self.assertNotEqual(first.id, second.id)

    def test_report_csv_contains_snapshot_and_total(self):
        product = self.service.add_product("کیک", 3, 7, 2)
        sale = self.service.sell(product.id, product.version, 1)
        day = sale.sold_at.astimezone(IRAN_TIME).date().isoformat()
        path = Path(self.temp.name) / "report.csv"
        export_sales(self.service.report(day, day), path)
        with path.open(encoding="utf-8-sig", newline="") as source:
            rows = list(csv.reader(source))
        self.assertEqual(rows[1][2:4], ["کیک", "1"])
        self.assertEqual(rows[-1][-2:], ["7", "4"])


if __name__ == "__main__":
    unittest.main()
