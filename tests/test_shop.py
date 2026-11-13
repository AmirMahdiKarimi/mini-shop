import sqlite3
import tempfile
import unittest
from contextlib import closing
from importlib.util import find_spec
from pathlib import Path

from shop.errors import ValidationError
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
        sale = self.service.sell(product.id, 2)
        self.assertEqual(self.service.get_product(product.id).stock, 3)
        self.service.edit_product(product.id, "شیر", 60, 100)
        day = sale.sold_at.astimezone(IRAN_TIME).date().isoformat()
        report = self.service.report(day, day)
        self.assertEqual((report.quantity, report.revenue), (2, 160))

    def test_insufficient_stock_has_no_partial_sale(self):
        product = self.service.add_product("چای", 10, 20, 1)
        with self.assertRaises(ValidationError):
            self.service.sell(product.id, 2)
        self.assertEqual(self.service.get_product(product.id).stock, 1)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM sales").fetchone()[0], 0)

    def test_stock_change_never_goes_negative(self):
        product = self.service.add_product("برنج", 10, 20, 4)
        self.service.add_stock(product.id, 1)
        self.service.sell(product.id, 5)
        with self.assertRaises(ValidationError):
            self.service.sell(product.id, 1)
        self.assertEqual(self.service.get_product(product.id).stock, 0)

    def test_archive_allows_remaining_stock_and_preserves_sales(self):
        product = self.service.add_product("نان", 5, 10, 3)
        sale = self.service.sell(product.id, 1)
        self.service.archive(product.id)
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

    def test_numeric_boundaries(self):
        product = self.service.add_product("آب", 0, 0, 0)
        self.assertEqual(product.stock, 0)
        for quantity in (0, -1, "1.5", "9" * 30):
            with self.subTest(quantity=quantity), self.assertRaises(ValidationError):
                self.service.add_stock(product.id, quantity)
        with self.assertRaises(ValidationError):
            self.service.sell(product.id, 0)
        with self.assertRaises(ValidationError):
            self.service.add_product("قند", 10**15, 1, 1)

    def test_zero_stock_archive_and_reuse_name(self):
        first = self.service.add_product("آب", 1, 2, 0)
        self.service.archive(first.id)
        second = self.service.add_product("آب", 3, 4, 2)
        self.assertNotEqual(first.id, second.id)

    @unittest.skipUnless(find_spec("openpyxl"), "openpyxl is not installed")
    def test_report_excel_contains_snapshot_and_total(self):
        from openpyxl import load_workbook

        product = self.service.add_product("کیک", 3, 7, 2)
        sale = self.service.sell(product.id, 1)
        formula_name = self.service.add_product("=1+1", 1, 1, 1)
        second_sale = self.service.sell(formula_name.id, 1)
        days = [item.sold_at.astimezone(IRAN_TIME).date().isoformat() for item in (sale, second_sale)]
        path = Path(self.temp.name) / "report.xlsx"
        export_sales(self.service.report(min(days), max(days)), path)
        workbook = load_workbook(path)
        sheet = workbook.active
        self.assertEqual({sheet["C2"].value, sheet["C3"].value}, {"کیک", "=1+1"})
        formula_cell = sheet["C2"] if sheet["C2"].value == "=1+1" else sheet["C3"]
        self.assertEqual(formula_cell.data_type, "s")
        self.assertEqual(sheet["F4"].value, 8)


if __name__ == "__main__":
    unittest.main()
