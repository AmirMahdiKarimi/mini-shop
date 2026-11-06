"""Small Tkinter interface for the same operations as the text menu."""

import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, simpledialog, ttk

from shop.errors import ShopError
from shop.export import export_sales
from shop.service import IRAN_TIME, ShopService


class ShopApp(tk.Tk):
    def __init__(self, service: ShopService):
        super().__init__()
        self.service = service
        self.selected = None
        self.sale_products = []
        self.title("فروشگاه من")
        self.geometry("1000x650")
        self.minsize(900, 600)
        self.configure(bg="#f3f7fa")
        self._style()

        tk.Label(
            self,
            text="مدیریت فروشگاه",
            bg="#19324a",
            fg="white",
            font=("Tahoma", 18, "bold"),
            padx=22,
            pady=18,
            anchor="e",
        ).pack(fill="x")
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=18, pady=16)
        self.products_tab = ttk.Frame(self.tabs, padding=14)
        self.sales_tab = ttk.Frame(self.tabs, padding=14)
        self.report_tab = ttk.Frame(self.tabs, padding=14)
        for tab, title in (
            (self.products_tab, "کالاها"),
            (self.sales_tab, "ثبت فروش"),
            (self.report_tab, "گزارش فروش"),
        ):
            self.tabs.add(tab, text=title)
        self._products_view()
        self._sales_view()
        self._report_view()
        self.refresh()

    def _style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#f3f7fa")
        style.configure("TLabel", background="#f3f7fa", foreground="#19324a", font=("Tahoma", 10))
        style.configure("TButton", padding=8, font=("Tahoma", 10))
        style.configure("TEntry", padding=6)
        style.configure("TNotebook.Tab", padding=(12, 7), font=("Tahoma", 9))
        style.map(
            "TNotebook.Tab", padding=[("selected", (28, 14))], font=[("selected", ("Tahoma", 11, "bold"))]
        )
        style.configure("Treeview", rowheight=30, font=("Tahoma", 10))
        style.configure("Treeview.Heading", font=("Tahoma", 10, "bold"))

    @staticmethod
    def _entry(parent, label: str, variable: tk.StringVar, row: int):
        ttk.Label(parent, text=label).grid(row=row, column=1, sticky="e", padx=8, pady=5)
        entry = ttk.Entry(parent, textvariable=variable, justify="right")
        entry.grid(row=row, column=0, sticky="ew", pady=5)
        return entry

    def _products_view(self) -> None:
        tab = self.products_tab
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)
        self.search = tk.StringVar()
        ttk.Label(tab, text="جست‌وجوی نام کالا").grid(row=0, column=1, sticky="e", padx=8)
        ttk.Entry(tab, textvariable=self.search, justify="right").grid(row=0, column=0, sticky="ew")

        columns = ("stock", "sale", "purchase", "name")
        self.products_tree = ttk.Treeview(tab, columns=columns, show="headings", selectmode="browse")
        for column, title, width in (
            ("stock", "موجودی", 75),
            ("sale", "فروش", 105),
            ("purchase", "خرید", 105),
            ("name", "نام کالا", 180),
        ):
            self.products_tree.heading(column, text=title, anchor="e")
            self.products_tree.column(column, width=width, anchor="e", stretch=column == "name")
        self.products_tree.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        self.products_tree.bind("<<TreeviewSelect>>", self._select_product)
        self.search.trace_add("write", lambda *_: self.refresh_products())

        form = ttk.Frame(tab, padding=(16, 12))
        form.grid(row=1, column=1, sticky="ns", pady=(12, 0))
        form.columnconfigure(0, weight=1)
        ttk.Label(form, text="مشخصات کالا", font=("Tahoma", 11, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="e", pady=(0, 12)
        )
        self.name = tk.StringVar()
        self.purchase = tk.StringVar()
        self.price = tk.StringVar()
        self.initial_stock = tk.StringVar()
        self._entry(form, "نام", self.name, 1)
        self._entry(form, "خرید (ریال)", self.purchase, 2)
        self._entry(form, "فروش (ریال)", self.price, 3)
        self.initial_entry = self._entry(form, "تعداد اولیه", self.initial_stock, 4)
        for row, title, command in (
            (5, "افزودن کالا", self.add_product),
            (6, "ذخیرهٔ ویرایش", self.edit_product),
            (7, "افزایش موجودی", self.add_stock),
            (8, "حذف کالا", self.archive_product),
            (9, "پاک کردن فرم", self.clear_form),
        ):
            button = ttk.Button(form, text=title, command=command)
            button.grid(row=row, column=0, columnspan=2, sticky="ew", pady=3)
            if row == 5:
                self.add_button = button

    def _sales_view(self) -> None:
        tab = self.sales_tab
        tab.columnconfigure(0, weight=1)
        ttk.Label(tab, text="کالای موردنظر را همین‌جا انتخاب کنید.").grid(row=0, column=0, sticky="e", pady=12)
        self.sale_choice = ttk.Combobox(tab, state="readonly", justify="right")
        self.sale_choice.grid(row=1, column=0, sticky="ew", pady=8)
        self.sale_quantity = tk.StringVar()
        self._entry(tab, "تعداد فروش", self.sale_quantity, 2)
        ttk.Button(tab, text="ثبت فروش", command=self.sell).grid(row=3, column=0, sticky="e", pady=12)

    def _report_view(self) -> None:
        tab = self.report_tab
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(2, weight=1)
        today = datetime.now(IRAN_TIME).date().isoformat()
        self.start = tk.StringVar(value=today)
        self.end = tk.StringVar(value=today)
        filters = ttk.Frame(tab)
        filters.grid(row=0, column=0, sticky="e", pady=8)
        for label, variable in (("از تاریخ میلادی", self.start), ("تا تاریخ میلادی", self.end)):
            ttk.Label(filters, text=label).pack(side="right", padx=6)
            ttk.Entry(filters, textvariable=variable, width=14, justify="center").pack(side="right", padx=6)
        ttk.Button(filters, text="نمایش", command=self.show_report).pack(side="right", padx=6)
        ttk.Button(filters, text="خروجی Excel", command=self.export_report).pack(side="right", padx=6)
        self.summary = tk.StringVar()
        ttk.Label(tab, textvariable=self.summary, font=("Tahoma", 11, "bold")).grid(
            row=1, column=0, sticky="e", pady=12
        )
        columns = ("amount", "quantity", "name", "date")
        self.sales_tree = ttk.Treeview(tab, columns=columns, show="headings")
        for column, title in (
            ("amount", "مبلغ (ریال)"),
            ("quantity", "تعداد"),
            ("name", "کالا"),
            ("date", "تاریخ فروش"),
        ):
            self.sales_tree.heading(column, text=title, anchor="e")
            self.sales_tree.column(column, anchor="e")
        self.sales_tree.grid(row=2, column=0, sticky="nsew")

    def _select_product(self, _event=None) -> None:
        selected = self.products_tree.selection()
        if not selected:
            return
        self.selected = self.service.get_product(int(selected[0]))
        self.name.set(self.selected.name)
        self.purchase.set(str(self.selected.purchase_price))
        self.price.set(str(self.selected.sale_price))
        self.initial_stock.set("")
        self.initial_entry.configure(state="disabled")
        self.add_button.configure(state="disabled")

    def clear_form(self) -> None:
        self.selected = None
        self.initial_entry.configure(state="normal")
        self.add_button.configure(state="normal")
        for variable in (self.name, self.purchase, self.price, self.initial_stock):
            variable.set("")
        self.products_tree.selection_remove(self.products_tree.selection())

    def _chosen_product(self):
        if self.selected is None:
            raise ShopError("ابتدا کالا را از فهرست انتخاب کنید.")
        return self.selected

    def _run(self, operation, success: str) -> None:
        try:
            operation()
        except ShopError as exc:
            messagebox.showwarning("عملیات انجام نشد", str(exc), parent=self)
        else:
            self.refresh()
            messagebox.showinfo("عملیات موفق", success, parent=self)

    def refresh(self) -> None:
        self.refresh_products()
        products = self.service.list_products()
        selected_id = None
        if self.sale_choice.current() >= 0 and self.sale_choice.current() < len(self.sale_products):
            selected_id = self.sale_products[self.sale_choice.current()].id
        self.sale_products = products
        self.sale_choice["values"] = [
            f"{p.name} | موجودی {p.stock} | {p.sale_price:,} ریال" for p in products
        ]
        self.sale_choice.set("")
        if selected_id is not None:
            for index, product in enumerate(products):
                if product.id == selected_id:
                    self.sale_choice.current(index)
                    break
        self.show_report()

    def refresh_products(self) -> None:
        selected_id = self.selected.id if self.selected else None
        self.products_tree.delete(*self.products_tree.get_children())
        for product in self.service.list_products(self.search.get()):
            self.products_tree.insert(
                "",
                "end",
                iid=str(product.id),
                values=(
                    product.stock,
                    f"{product.sale_price:,}",
                    f"{product.purchase_price:,}",
                    product.name,
                ),
            )
        if selected_id is not None and str(selected_id) in self.products_tree.get_children():
            self.products_tree.selection_set(str(selected_id))
            self._select_product()
        elif selected_id is not None:
            self.clear_form()

    def add_product(self) -> None:
        def save():
            self.service.add_product(
                self.name.get(), self.purchase.get(), self.price.get(), self.initial_stock.get()
            )
            self.clear_form()

        self._run(save, "کالا با موفقیت اضافه شد.")

    def edit_product(self) -> None:
        def save():
            product = self._chosen_product()
            self.service.edit_product(product.id, self.name.get(), self.purchase.get(), self.price.get())
            self.clear_form()

        self._run(save, "مشخصات کالا با موفقیت به‌روز شد.")

    def add_stock(self) -> None:
        try:
            product = self._chosen_product()
        except ShopError as exc:
            messagebox.showwarning("انتخاب کالا", str(exc), parent=self)
            return
        quantity = simpledialog.askstring(
            "افزایش موجودی", f"{product.name} | موجودی فعلی: {product.stock}\nتعداد افزایش:", parent=self
        )
        if quantity is not None:
            self._run(lambda: self.service.add_stock(product.id, quantity), "موجودی با موفقیت افزایش یافت.")

    def sell(self) -> None:
        index = self.sale_choice.current()
        if index < 0:
            messagebox.showwarning("انتخاب کالا", "ابتدا کالای موردنظر را انتخاب کنید.", parent=self)
            return
        product = self.sale_products[index]

        def save():
            self.service.sell(product.id, self.sale_quantity.get())
            self.sale_quantity.set("")

        self._run(save, "فروش با موفقیت ثبت شد.")

    def archive_product(self) -> None:
        try:
            product = self._chosen_product()
        except ShopError as exc:
            messagebox.showwarning("انتخاب کالا", str(exc), parent=self)
            return
        if messagebox.askyesno(
            "حذف کالا", f"«{product.name}» با موجودی {product.stock} از فهرست حذف شود؟", parent=self
        ):

            def save():
                self.service.archive(product.id)
                self.clear_form()

            self._run(save, "کالا با موفقیت حذف شد.")

    def show_report(self) -> None:
        try:
            report = self.service.report(self.start.get(), self.end.get())
        except ShopError as exc:
            messagebox.showwarning("بازهٔ گزارش", str(exc), parent=self)
            return
        self.summary.set(f"تعداد فروخته‌شده: {report.quantity:,}    |    درآمد: {report.revenue:,} ریال")
        self.sales_tree.delete(*self.sales_tree.get_children())
        for sale in report.sales:
            self.sales_tree.insert(
                "",
                "end",
                values=(
                    f"{sale.revenue:,}",
                    sale.quantity,
                    sale.product_name,
                    sale.sold_at.astimezone(IRAN_TIME).strftime("%Y-%m-%d %H:%M"),
                ),
            )

    def export_report(self) -> None:
        try:
            report = self.service.report(self.start.get(), self.end.get())
        except ShopError as exc:
            messagebox.showwarning("بازهٔ گزارش", str(exc), parent=self)
            return
        path = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile="sales-report.xlsx",
        )
        if path:
            try:
                export_sales(report, path)
            except (OSError, RuntimeError) as exc:
                messagebox.showerror("خطا در ذخیره", str(exc), parent=self)
            else:
                messagebox.showinfo("عملیات موفق", "گزارش ذخیره شد.", parent=self)


def run(service: ShopService) -> None:
    ShopApp(service).mainloop()
