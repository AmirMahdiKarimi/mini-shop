"""Persian Tkinter interface for inventory, sales and reports."""

import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, simpledialog, ttk

from shop.errors import ConflictError, ShopError
from shop.export import export_sales
from shop.models import Shop
from shop.service import IRAN_TIME, ShopService

INK = "#19324a"
MUTED = "#61788b"
BG = "#f3f7fa"
CARD = "#ffffff"
ACCENT = "#087f8c"
ACCENT_DARK = "#066773"
CORAL = "#d15b50"


def money(value: int) -> str:
    return f"{value:,} ریال"


class ProductPicker(ttk.Frame):
    """Searchable product list for a single transaction workflow."""

    def __init__(self, parent, service: ShopService, on_select):
        super().__init__(parent, style="Card.TFrame", padding=18)
        self.service = service
        self.on_select = on_select
        self.selected_id: int | None = None
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.query = tk.StringVar()
        search = ttk.Entry(self, textvariable=self.query, justify="right")
        search.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        ttk.Label(self, text="جست‌وجوی کالا", style="Card.TLabel", anchor="e").grid(
            row=0, column=1, sticky="e", padx=(12, 0), pady=(0, 12)
        )
        self.query.trace_add("write", lambda *_: self.refresh())

        columns = ("stock", "price", "name")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="browse", height=6)
        for column, title, width in (
            ("stock", "موجودی", 100),
            ("price", "قیمت فروش (ریال)", 160),
            ("name", "نام کالا", 350),
        ):
            self.tree.heading(column, text=title, anchor="e")
            self.tree.column(column, width=width, anchor="e", stretch=column == "name")
        self.tree.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _on_select(self, _event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        self.selected_id = int(selection[0])
        self.on_select(self.service.get_product(self.selected_id))

    def refresh(self) -> None:
        products = self.service.list_products(self.query.get())
        for item in self.tree.get_children():
            self.tree.delete(item)
        for product in products:
            self.tree.insert(
                "",
                "end",
                iid=str(product.id),
                values=(product.stock, f"{product.sale_price:,}", product.name),
            )
        if self.selected_id is not None and str(self.selected_id) in self.tree.get_children():
            self.tree.selection_set(str(self.selected_id))
            self.on_select(self.service.get_product(self.selected_id))
        else:
            self.selected_id = None
            self.on_select(None)

    def select_product(self, product_id: int) -> None:
        self.query.set("")
        self.tree.selection_set(str(product_id))
        self.tree.see(str(product_id))
        self._on_select()


class ShopApp(tk.Tk):
    def __init__(self, service: ShopService):
        super().__init__()
        self.service = service
        self.selected: Shop | None = None
        self.sale_selected: Shop | None = None
        self.title("فروشگاه من | مدیریت کالا و فروش")
        self.geometry("1120x730")
        self.minsize(1050, 730)
        self.configure(bg=BG)
        self._style()
        self._layout()
        self.refresh_products()
        self.refresh_report()

    def _style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=CARD)
        style.configure("TLabel", background=BG, foreground=INK, font=("Tahoma", 10))
        style.configure("Card.TLabel", background=CARD, foreground=INK, font=("Tahoma", 10))
        style.configure("Muted.TLabel", background=CARD, foreground=MUTED, font=("Tahoma", 9))
        style.configure("TEntry", padding=7, font=("Tahoma", 10))
        style.configure(
            "TButton",
            padding=(16, 9),
            font=("Tahoma", 10),
            background="#e8f0f3",
            foreground=INK,
            borderwidth=0,
        )
        style.map("TButton", background=[("active", "#d8e9ed")])
        style.configure("Primary.TButton", background=ACCENT, foreground="white")
        style.map("Primary.TButton", background=[("active", ACCENT_DARK)])
        style.configure("Danger.TButton", foreground=CORAL)
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure(
            "TNotebook.Tab", padding=(12, 7), font=("Tahoma", 9), background="#dfe9ed", foreground=MUTED
        )
        style.map(
            "TNotebook.Tab",
            padding=[("selected", (28, 14))],
            font=[("selected", ("Tahoma", 11, "bold"))],
            background=[("selected", CARD)],
            foreground=[("selected", ACCENT)],
        )
        style.configure(
            "Treeview",
            rowheight=36,
            font=("Tahoma", 10),
            background=CARD,
            fieldbackground=CARD,
            foreground=INK,
            borderwidth=0,
        )
        style.configure(
            "Treeview.Heading", font=("Tahoma", 10, "bold"), background="#e9f1f4", foreground=INK, padding=8
        )
        style.map("Treeview", background=[("selected", "#d7eff1")], foreground=[("selected", INK)])

    def _layout(self) -> None:
        header = tk.Frame(self, bg=INK, padx=28, pady=21)
        header.pack(fill="x")
        tk.Label(header, text="فروشگاه من", bg=INK, fg="white", font=("Tahoma", 20, "bold"), anchor="e").pack(
            fill="x"
        )
        tk.Label(
            header,
            text="مدیریت ساده و دقیق موجودی، فروش و گزارش‌ها",
            bg=INK,
            fg="#a9ced7",
            font=("Tahoma", 10),
            anchor="e",
        ).pack(fill="x", pady=(5, 0))

        body = ttk.Frame(self, padding=(24, 18))
        body.pack(fill="both", expand=True)
        self.tabs = ttk.Notebook(body)
        self.tabs.pack(fill="both", expand=True)
        self.products_tab = ttk.Frame(self.tabs)
        self.sales_tab = ttk.Frame(self.tabs)
        self.report_tab = ttk.Frame(self.tabs)
        self.tabs.add(self.products_tab, text="کالاها")
        self.tabs.add(self.sales_tab, text="ثبت فروش")
        self.tabs.add(self.report_tab, text="گزارش فروش")
        self._products_view()
        self._sales_view()
        self._report_view()
        self.sales_picker.refresh()

        self.status = tk.StringVar(value="آماده")
        tk.Label(
            self,
            textvariable=self.status,
            bg="#e7eff2",
            fg=MUTED,
            font=("Tahoma", 9),
            anchor="e",
            padx=26,
            pady=8,
        ).pack(fill="x")

    def _card(self, parent, **kwargs):
        frame = ttk.Frame(parent, style="Card.TFrame", padding=18, **kwargs)
        return frame

    def _label(self, parent, text, *, muted=False):
        return ttk.Label(parent, text=text, style="Muted.TLabel" if muted else "Card.TLabel", anchor="e")

    def _entry_row(self, parent, label, variable, row):
        self._label(parent, label).grid(row=row, column=1, sticky="e", pady=7, padx=(8, 0))
        entry = ttk.Entry(parent, textvariable=variable, justify="right")
        entry.grid(row=row, column=0, sticky="ew", pady=7)
        return entry

    def _products_view(self) -> None:
        tab = self.products_tab
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)
        toolbar = self._card(tab)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(8, 12))
        toolbar.columnconfigure(0, weight=1)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh_products())
        ttk.Entry(toolbar, textvariable=self.search_var, justify="right").grid(
            row=0, column=0, sticky="ew", padx=(0, 12)
        )
        self._label(toolbar, "جست‌وجوی نام کالا").grid(row=0, column=1, sticky="e")
        ttk.Button(toolbar, text="تازه‌سازی", command=self.refresh_products).grid(
            row=0, column=2, padx=(12, 0)
        )

        content = ttk.Frame(tab)
        content.grid(row=1, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(0, weight=1)
        table_card = self._card(content)
        table_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        table_card.columnconfigure(0, weight=1)
        table_card.rowconfigure(1, weight=1)
        self._label(table_card, "فهرست کالاها").grid(row=0, column=0, sticky="e", pady=(0, 12))
        columns = ("stock", "sale", "purchase", "name", "id")
        self.products_tree = ttk.Treeview(table_card, columns=columns, show="headings", selectmode="browse")
        headers = {
            "stock": "موجودی",
            "sale": "قیمت فروش",
            "purchase": "قیمت خرید",
            "name": "نام کالا",
            "id": "شناسه",
        }
        widths = {"stock": 70, "sale": 125, "purchase": 125, "name": 180, "id": 65}
        for column in columns:
            self.products_tree.heading(column, text=headers[column], anchor="e")
            self.products_tree.column(column, width=widths[column], anchor="e", stretch=column == "name")
        self.products_tree.grid(row=1, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(table_card, orient="vertical", command=self.products_tree.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.products_tree.configure(yscrollcommand=scrollbar.set)
        self.products_tree.bind("<<TreeviewSelect>>", self._select_product)

        form = self._card(content, width=310)
        form.grid(row=0, column=1, sticky="ns")
        form.grid_propagate(False)
        form.columnconfigure(0, weight=1)
        self._label(form, "مشخصات کالا").grid(row=0, column=0, columnspan=2, sticky="e", pady=(0, 14))
        self.name_var = tk.StringVar()
        self.purchase_var = tk.StringVar()
        self.sale_var = tk.StringVar()
        self.stock_var = tk.StringVar()
        self.name_entry = self._entry_row(form, "نام", self.name_var, 1)
        self._entry_row(form, "خرید (ریال)", self.purchase_var, 2)
        self._entry_row(form, "فروش (ریال)", self.sale_var, 3)
        self.stock_entry = self._entry_row(form, "تعداد اولیهٔ کالای جدید", self.stock_var, 4)
        self._label(form, "برای ویرایش، یک کالا را از فهرست انتخاب کنید.", muted=True).grid(
            row=5, column=0, columnspan=2, sticky="e", pady=(8, 12)
        )
        self.create_button = ttk.Button(
            form, text="افزودن کالای جدید", style="Primary.TButton", command=self.add_product
        )
        self.create_button.grid(row=6, column=0, columnspan=2, sticky="ew", pady=4)
        self.edit_button = ttk.Button(form, text="ذخیرهٔ ویرایش", command=self.edit_product)
        self.edit_button.grid(row=7, column=0, columnspan=2, sticky="ew", pady=4)
        self.add_stock_button = ttk.Button(form, text="افزایش موجودی", command=self.add_stock)
        self.add_stock_button.grid(row=8, column=0, columnspan=2, sticky="ew", pady=4)
        self.archive_button = ttk.Button(
            form, text="بایگانی کالا", style="Danger.TButton", command=self.archive_product
        )
        self.archive_button.grid(row=9, column=0, columnspan=2, sticky="ew", pady=4)
        ttk.Button(form, text="پاک کردن فرم", command=self.clear_form).grid(
            row=10, column=0, columnspan=2, sticky="ew", pady=4
        )
        self._set_product_mode(selected=False)

    def _sales_view(self) -> None:
        tab = self.sales_tab
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(0, weight=1)
        self.sales_picker = ProductPicker(tab, self.service, self._select_sale_product)
        self.sales_picker.grid(row=0, column=0, sticky="nsew", pady=(8, 12))
        panel = self._card(tab)
        panel.grid(row=1, column=0, sticky="ew")
        panel.columnconfigure(0, weight=1)
        self._label(panel, "ثبت فروش کالا").grid(row=0, column=0, columnspan=2, sticky="e", pady=(0, 12))
        self._label(
            panel, "کالا را از فهرست بالا انتخاب کنید. قیمت لحظهٔ فروش در تاریخچه ثبت می‌شود.", muted=True
        ).grid(row=1, column=0, columnspan=2, sticky="e", pady=(0, 14))
        self.sale_selection = tk.StringVar(value="کالایی انتخاب نشده است")
        self._label(panel, "کالای انتخابی:").grid(row=2, column=1, sticky="e")
        ttk.Label(panel, textvariable=self.sale_selection, style="Card.TLabel", anchor="e").grid(
            row=2, column=0, sticky="ew", pady=7
        )
        self.sale_quantity = tk.StringVar()
        self._entry_row(panel, "تعداد فروش", self.sale_quantity, 3)
        ttk.Button(panel, text="ثبت فروش", style="Primary.TButton", command=self.sell).grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=(15, 0)
        )

    def _report_view(self) -> None:
        tab = self.report_tab
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(2, weight=1)
        filters = self._card(tab)
        filters.grid(row=0, column=0, sticky="ew", pady=(8, 12))
        today = datetime.now(IRAN_TIME).date().isoformat()
        self.start_var = tk.StringVar(value=today)
        self.end_var = tk.StringVar(value=today)
        self._label(filters, "از تاریخ (میلادی)").pack(side="right", padx=(10, 4))
        ttk.Entry(filters, textvariable=self.start_var, width=16, justify="center").pack(
            side="right", padx=(0, 18)
        )
        self._label(filters, "تا تاریخ (میلادی)").pack(side="right", padx=(10, 4))
        ttk.Entry(filters, textvariable=self.end_var, width=16, justify="center").pack(
            side="right", padx=(0, 18)
        )
        ttk.Button(filters, text="نمایش گزارش", style="Primary.TButton", command=self.refresh_report).pack(
            side="right"
        )
        ttk.Button(filters, text="خروجی CSV", command=self.export_report).pack(side="left")

        summary = self._card(tab)
        summary.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        self.summary_var = tk.StringVar()
        ttk.Label(
            summary,
            textvariable=self.summary_var,
            style="Card.TLabel",
            anchor="e",
            font=("Tahoma", 11, "bold"),
        ).pack(fill="x")

        history = self._card(tab)
        history.grid(row=2, column=0, sticky="nsew")
        history.columnconfigure(0, weight=1)
        history.rowconfigure(1, weight=1)
        self._label(history, "جزئیات فروش").grid(row=0, column=0, sticky="e", pady=(0, 10))
        columns = ("total", "price", "quantity", "product", "time")
        self.report_tree = ttk.Treeview(history, columns=columns, show="headings")
        for column, title, width in [
            ("total", "مبلغ کل", 140),
            ("price", "قیمت واحد", 140),
            ("quantity", "تعداد", 75),
            ("product", "نام کالا", 220),
            ("time", "زمان فروش", 165),
        ]:
            self.report_tree.heading(column, text=title, anchor="e")
            self.report_tree.column(column, anchor="e", width=width, stretch=column == "product")
        self.report_tree.grid(row=1, column=0, sticky="nsew")

    def _select_product(self, _event=None) -> None:
        selection = self.products_tree.selection()
        if not selection:
            return
        product = self.service.get_product(int(selection[0]))
        self._display_product(product)

    def _display_product(self, product: Shop) -> None:
        self.selected = product
        self.name_var.set(product.name)
        self.purchase_var.set(str(product.purchase_price))
        self.sale_var.set(str(product.sale_price))
        self.stock_var.set("")
        self._set_product_mode(selected=True)

    def _select_sale_product(self, product: Shop | None) -> None:
        if product is None or self.sale_selected is None or self.sale_selected.id != product.id:
            self.sale_quantity.set("")
        self.sale_selected = product
        self.sale_selection.set(
            f"{product.name} | موجودی {product.stock} | {money(product.sale_price)}"
            if product
            else "کالایی انتخاب نشده است"
        )

    def _set_product_mode(self, *, selected: bool) -> None:
        self.stock_entry.configure(state="disabled" if selected else "normal")
        self.create_button.configure(state="disabled" if selected else "normal")
        action_state = "normal" if selected else "disabled"
        self.edit_button.configure(state=action_state)
        self.add_stock_button.configure(state=action_state)
        self.archive_button.configure(state=action_state)

    def clear_form(self) -> None:
        self.selected = None
        self._set_product_mode(selected=False)
        for variable in (self.name_var, self.purchase_var, self.sale_var, self.stock_var):
            variable.set("")
        self.products_tree.selection_remove(self.products_tree.selection())
        self.name_entry.focus_set()

    def _selected(self) -> Shop:
        if self.selected is None:
            raise ShopError("ابتدا یک کالا را از فهرست انتخاب کنید.")
        return self.selected

    def _action(self, operation, success: str) -> None:
        try:
            operation()
        except ConflictError as exc:
            self.refresh_products()
            self.clear_form()
            self.sales_picker.refresh()
            messagebox.showwarning("اطلاعات تغییر کرده", str(exc), parent=self)
        except ShopError as exc:
            messagebox.showwarning("عملیات انجام نشد", str(exc), parent=self)
        else:
            self.refresh_products()
            self.sales_picker.refresh()
            self.refresh_report()
            self.status.set(success)
            messagebox.showinfo("عملیات موفق", success, parent=self)

    def add_product(self) -> None:
        def operation():
            self.service.add_product(
                self.name_var.get(), self.purchase_var.get(), self.sale_var.get(), self.stock_var.get()
            )
            self.clear_form()

        self._action(operation, "کالا با موفقیت اضافه شد.")

    def edit_product(self) -> None:
        def operation():
            product = self._selected()
            self.service.edit_product(
                product.id, product.version, self.name_var.get(), self.purchase_var.get(), self.sale_var.get()
            )
            self.clear_form()

        self._action(operation, "مشخصات کالا با موفقیت به‌روز شد.")

    def add_stock(self) -> None:
        product = self._selected()
        quantity = simpledialog.askstring(
            "افزایش موجودی",
            f"{product.name} | موجودی فعلی: {product.stock}\nتعداد برای افزودن:",
            parent=self,
        )
        if quantity is None:
            return

        def operation():
            self.service.add_stock(product.id, product.version, quantity)

        self._action(operation, "موجودی با موفقیت افزایش یافت.")

    def sell(self) -> None:
        revenue = None

        def operation():
            nonlocal revenue
            product = self.sale_selected
            if product is None:
                raise ShopError("ابتدا یک کالا را از فهرست فروش انتخاب کنید.")
            sale = self.service.sell(product.id, product.version, self.sale_quantity.get())
            revenue = sale.revenue
            self.sale_quantity.set("")

        self._action(operation, "فروش با موفقیت ثبت شد.")
        if revenue is not None:
            self.status.set(f"فروش ثبت شد: {money(revenue)}")

    def archive_product(self) -> None:
        try:
            product = self._selected()
        except ShopError as exc:
            messagebox.showwarning("انتخاب کالا", str(exc), parent=self)
            return
        if messagebox.askyesno(
            "بایگانی کالا",
            f"«{product.name}» با موجودی {product.stock} بایگانی شود؟\nسابقهٔ فروش حفظ می‌شود.",
            parent=self,
        ):

            def operation():
                self.service.archive(product.id, product.version)
                self.clear_form()

            self._action(operation, "کالا با موفقیت بایگانی شد.")

    def refresh_products(self) -> None:
        selected_id = self.selected.id if self.selected else None
        for item in self.products_tree.get_children():
            self.products_tree.delete(item)
        products = self.service.list_products(self.search_var.get())
        for product in products:
            self.products_tree.insert(
                "",
                "end",
                iid=str(product.id),
                values=(
                    product.stock,
                    f"{product.sale_price:,}",
                    f"{product.purchase_price:,}",
                    product.name,
                    product.id,
                ),
            )
        if selected_id and str(selected_id) in self.products_tree.get_children():
            self.products_tree.selection_set(str(selected_id))
            self._display_product(self.service.get_product(selected_id))
        elif selected_id:
            self.clear_form()
        self.status.set(f"{len(products)} کالا نمایش داده می‌شود.")

    def refresh_report(self) -> None:
        try:
            report = self.service.report(self.start_var.get(), self.end_var.get())
        except ShopError as exc:
            messagebox.showwarning("بازهٔ گزارش", str(exc), parent=self)
            return
        self.summary_var.set(
            f"تعداد فروخته‌شده: {report.quantity:,}    |    درآمد: {money(report.revenue)}"
            f"    |    سود ناخالص: {money(report.profit)}"
        )
        for item in self.report_tree.get_children():
            self.report_tree.delete(item)
        for sale in report.sales:
            self.report_tree.insert(
                "",
                "end",
                values=(
                    f"{sale.revenue:,}",
                    f"{sale.unit_price:,}",
                    sale.quantity,
                    sale.product_name,
                    sale.sold_at.astimezone(IRAN_TIME).strftime("%Y-%m-%d %H:%M"),
                ),
            )

    def export_report(self) -> None:
        try:
            report = self.service.report(self.start_var.get(), self.end_var.get())
        except ShopError as exc:
            messagebox.showwarning("بازهٔ گزارش", str(exc), parent=self)
            return
        destination = filedialog.asksaveasfilename(
            parent=self,
            title="ذخیرهٔ گزارش فروش",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile="sales-report.csv",
        )
        if not destination:
            return
        try:
            export_sales(report, destination)
        except OSError as exc:
            messagebox.showerror("خطا در ذخیره", str(exc), parent=self)
        else:
            self.status.set("گزارش CSV ذخیره شد.")


def run(service: ShopService) -> None:
    ShopApp(service).mainloop()
