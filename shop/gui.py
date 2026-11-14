import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, simpledialog, ttk

from shop.errors import AuthenticationUserError, ShopError
from shop.export import export_sales
from shop.models import UserRole
from shop.utils import IRAN_TIME


class ShopApp(tk.Tk):
    def __init__(self, service):
        super().__init__()
        self.service = service
        self.user = None
        self.sale_products = []
        self.title("ورود به فروشگاه")
        self.geometry("420x320")
        self.resizable(False, False)
        self.username = tk.StringVar()
        self.password = tk.StringVar()
        self.login_error = tk.StringVar()
        self.login_frame = ttk.Frame(self, padding=28)
        self.login_frame.pack(fill="both", expand=True)
        ttk.Label(self.login_frame, text="ورود به فروشگاه", font=("Tahoma", 17, "bold")).pack(pady=(8, 24))
        ttk.Label(self.login_frame, text="نام کاربری").pack(anchor="e")
        username_entry = ttk.Entry(self.login_frame, textvariable=self.username, justify="right")
        username_entry.pack(fill="x", pady=(4, 14))
        ttk.Label(self.login_frame, text="رمز عبور").pack(anchor="e")
        password_entry = ttk.Entry(self.login_frame, textvariable=self.password, show="*", justify="right")
        password_entry.pack(fill="x", pady=(4, 16))
        password_entry.bind("<Return>", lambda _event: self._login())
        ttk.Button(self.login_frame, text="ورود", command=self._login).pack(fill="x")
        ttk.Label(self.login_frame, textvariable=self.login_error, foreground="#b42318").pack(pady=12)
        username_entry.focus_set()

    def _login(self):
        try:
            user = self.service.login(self.username.get().strip(), self.password.get())
        except AuthenticationUserError as exc:
            self.password.set("")
            self.login_error.set(str(exc))
            return
        self.user = user
        self.password.set("")
        self.login_frame.destroy()
        self._build_main()

    def _build_main(self):
        self.title("فروشگاه من")
        self.resizable(True, True)
        self.geometry("1000x650")
        self.minsize(900, 660)
        style = ttk.Style(self)
        style.configure("TNotebook.Tab", padding=(12, 7), font=("Tahoma", 10))
        style.map("TNotebook.Tab", padding=[("selected", (24, 12))])
        tk.Label(
            self,
            text="مدیریت فروشگاه",
            bg="#19324a",
            fg="white",
            font=("Tahoma", 16, "bold"),
            pady=14,
            anchor="e",
        ).pack(fill="x")

        tabs = ttk.Notebook(self)
        tabs.pack(fill="both", expand=True, padx=16, pady=12)
        self.products_tab = ttk.Frame(tabs, padding=12)
        self.sales_tab = ttk.Frame(tabs, padding=12)
        self.report_tab = ttk.Frame(tabs, padding=12)
        if self.user.role in (UserRole.SELLER, UserRole.ADMIN):
            tabs.add(self.products_tab, text="کالاها")
            self._products_view()
        tabs.add(self.sales_tab, text="ثبت خرید")
        self._sales_view()
        if self.user.role == UserRole.ADMIN:
            tabs.add(self.report_tab, text="گزارش فروش")
            self._report_view()
        self.refresh()

    def _products_view(self):
        tab = self.products_tab
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)
        self.search = tk.StringVar()
        ttk.Label(tab, text="جست‌وجوی کالا").grid(row=0, column=1, sticky="e")
        ttk.Entry(tab, textvariable=self.search, justify="right").grid(row=0, column=0, sticky="ew")
        columns = (("stock", "موجودی"), ("sale", "فروش"), ("purchase", "خرید"), ("name", "نام کالا"))
        self.products_tree = ttk.Treeview(
            tab, columns=[key for key, _ in columns], show="headings", selectmode="browse"
        )
        for key, title in columns:
            self.products_tree.heading(key, text=title, anchor="e")
            self.products_tree.column(key, anchor="e", width=110 if key != "name" else 170)
        self.products_tree.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=10)
        self.search.trace_add("write", lambda *_: self.refresh_products())
        actions = ttk.Frame(tab)
        actions.grid(row=2, column=0, columnspan=2, sticky="e")
        for label, action in (
            ("افزودن کالا", self.add_product),
            ("ویرایش", self.edit_product),
            ("افزایش موجودی", self.add_stock),
            ("حذف کالا", self.archive_product),
        ):
            ttk.Button(actions, text=label, command=action).pack(side="right", padx=4)

    def _sales_view(self):
        tab = self.sales_tab
        ttk.Label(tab, text="کالا").pack(anchor="e")
        self.sale_choice = ttk.Combobox(tab, state="readonly", justify="right")
        self.sale_choice.pack(fill="x", pady=8)
        self.sale_quantity = tk.StringVar()
        ttk.Label(tab, text="تعداد خرید").pack(anchor="e")
        ttk.Entry(tab, textvariable=self.sale_quantity, justify="right").pack(fill="x", pady=8)
        ttk.Button(tab, text="ثبت خرید", command=self.sell).pack(anchor="e")

    def _report_view(self):
        tab = self.report_tab
        today = datetime.now(IRAN_TIME).date().isoformat()
        self.start, self.end = tk.StringVar(value=today), tk.StringVar(value=today)
        filters = ttk.Frame(tab)
        filters.pack(fill="x", pady=8)
        for label, variable in (("از تاریخ میلادی", self.start), ("تا تاریخ میلادی", self.end)):
            ttk.Label(filters, text=label).pack(side="right", padx=5)
            ttk.Entry(filters, textvariable=variable, width=14).pack(side="right", padx=5)
        ttk.Button(filters, text="نمایش", command=self.show_report).pack(side="right", padx=5)
        ttk.Button(filters, text="خروجی Excel", command=self.export_report).pack(side="right", padx=5)
        self.summary = tk.StringVar()
        ttk.Label(tab, textvariable=self.summary, font=("Tahoma", 12, "bold")).pack(anchor="e", pady=12)
        columns = (
            ("amount", "مبلغ (ریال)", 140),
            ("quantity", "تعداد", 80),
            ("name", "کالا", 190),
            ("date", "زمان فروش", 160),
        )
        self.sales_tree = ttk.Treeview(tab, columns=[key for key, _, _ in columns], show="headings")
        for key, title, width in columns:
            self.sales_tree.heading(key, text=title, anchor="e")
            self.sales_tree.column(key, width=width, anchor="e")
        self.sales_tree.pack(fill="both", expand=True)

    def _selected_product(self):
        selection = self.products_tree.selection()
        if not selection:
            messagebox.showwarning("انتخاب کالا", "ابتدا کالا را از فهرست انتخاب کنید", parent=self)
            return None
        return self.service.get_product(int(selection[0]))

    def _ask_product(self, product=None):
        values = []
        fields = (("نام", "name"), ("قیمت خرید", "purchase_price"), ("قیمت فروش", "sale_price"))
        for label, attribute in fields:
            current = getattr(product, attribute) if product else ""
            value = simpledialog.askstring(label, label, initialvalue=str(current), parent=self)
            if value is None:
                return None
            values.append(value)
        if product is None:
            stock = simpledialog.askstring("تعداد اولیه", "تعداد اولیه", initialvalue="0", parent=self)
            if stock is None:
                return None
            values.append(stock)
        return values

    def refresh_products(self):
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

    def refresh(self):
        if self.user.role in (UserRole.SELLER, UserRole.ADMIN):
            self.refresh_products()
        self.sale_products = self.service.list_products()
        self.sale_choice["values"] = [
            f"{p.name} | موجودی {p.stock} | {p.sale_price:,} ریال" for p in self.sale_products
        ]
        self.sale_choice.set("")
        self.sale_quantity.set("")
        if self.user.role == UserRole.ADMIN:
            self.show_report()

    def _run(self, action, success):
        try:
            action()
        except ShopError as exc:
            messagebox.showwarning("عملیات انجام نشد", str(exc), parent=self)
            return
        self.refresh()
        messagebox.showinfo("عملیات موفق", success, parent=self)

    def add_product(self):
        values = self._ask_product()
        if values is not None:
            self._run(lambda: self.service.add_product(*values), "کالا با موفقیت اضافه شد")

    def edit_product(self):
        product = self._selected_product()
        if product:
            values = self._ask_product(product)
            if values is not None:
                self._run(
                    lambda: self.service.edit_product(product.id, *values), "مشخصات کالا با موفقیت به‌روز شد"
                )

    def add_stock(self):
        product = self._selected_product()
        if product:
            quantity = simpledialog.askstring(
                "افزایش موجودی", f"{product.name} | موجودی فعلی: {product.stock}\nتعداد افزایش:", parent=self
            )
            if quantity is not None:
                self._run(
                    lambda: self.service.add_stock(product.id, quantity), "موجودی با موفقیت افزایش یافت"
                )

    def sell(self):
        index = self.sale_choice.current()
        if index < 0:
            messagebox.showwarning("انتخاب کالا", "ابتدا کالای موردنظر را انتخاب کنید", parent=self)
            return
        self._run(
            lambda: self.service.sell(self.user.id, self.sale_products[index].id, self.sale_quantity.get()),
            "خرید با موفقیت ثبت شد",
        )

    def archive_product(self):
        product = self._selected_product()
        if product and messagebox.askyesno(
            "حذف کالا", f"«{product.name}» با موجودی {product.stock} از فهرست حذف شود؟", parent=self
        ):
            self._run(lambda: self.service.archive(product.id), "کالا با موفقیت حذف شد")

    def show_report(self):
        self.summary.set("")
        self.sales_tree.delete(*self.sales_tree.get_children())
        try:
            report = self.service.report(self.start.get(), self.end.get())
        except ShopError as exc:
            messagebox.showwarning("بازهٔ گزارش", str(exc), parent=self)
            return None
        self.summary.set(f"تعداد فروخته‌شده: {report.quantity:,}    |    درآمد: {report.revenue:,} ریال")
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
        return report

    def export_report(self):
        report = self.show_report()
        if report is None:
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
                messagebox.showinfo("عملیات موفق", "گزارش ذخیره شد", parent=self)


def run(service):
    ShopApp(service).mainloop()
