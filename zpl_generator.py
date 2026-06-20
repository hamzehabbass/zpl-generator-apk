import json
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog


def get_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


DATA_FILE = os.path.join(get_base_dir(), "goods_spec.json")

DEFAULT_ZPL_LAYOUT = {
    "goods_spec_x": 55,
    "goods_spec_y": 55,
    "bl_x": 55,
    "bl_y": 80,
    "count_x": 70,
    "count_y": 105,
    "barcode_x": 70,
    "barcode_y": 120,
    "barcode_module_width": 2,
    "barcode_height": 100,
}


def normalize_data_store(raw):
    base = {
        "password": "admin",
        "specs": [],
        "zpl_layout": DEFAULT_ZPL_LAYOUT.copy(),
    }
    if not isinstance(raw, dict):
        return base

    if isinstance(raw.get("password"), str) and raw.get("password"):
        base["password"] = raw["password"]
    if isinstance(raw.get("specs"), list):
        base["specs"] = raw["specs"]

    raw_layout = raw.get("zpl_layout") if isinstance(raw.get("zpl_layout"), dict) else {}
    for key, default in DEFAULT_ZPL_LAYOUT.items():
        try:
            val = int(raw_layout.get(key, default))
        except (TypeError, ValueError):
            val = default
        if key in ("barcode_module_width", "barcode_height") and val < 1:
            val = default
        if key not in ("barcode_module_width", "barcode_height") and val < 0:
            val = default
        base["zpl_layout"][key] = val

    return base


def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return normalize_data_store(json.load(f))
        except Exception:
            return normalize_data_store(None)
    return normalize_data_store(None)


def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save data: {e}")
        return False


data_store = load_data()

# Company branding
COMPANY_NAME = "Vehrad Transport and Haulage Company Limited"

# Try to load a logo image from the app folder (logo.png or logo.gif). If PIL is
# available use it to resize; otherwise try Tkinter's PhotoImage directly.
def load_logo():
    base = get_base_dir()
    for fname in ("logo.png", "logo.gif", "logo.ico"):
        path = os.path.join(base, fname)
        if os.path.exists(path):
            try:
                from PIL import Image, ImageTk
                img = Image.open(path)
                # target height 48 px, preserve aspect
                h = 48
                w = int(img.width * (h / img.height))
                img = img.resize((w, h), Image.LANCZOS)
                return ImageTk.PhotoImage(img)
            except Exception:
                try:
                    return tk.PhotoImage(file=path)
                except Exception:
                    return None
    return None

LOGO_IMAGE = load_logo()


def generate_zpl():
    try:
        bl_number = bl_var.get().strip()
        total_qty = int(qty_var.get().strip())
        goods_spec = spec_var.get().strip()

        if not bl_number:
            raise ValueError("BL Number is required.")
        if not goods_spec:
            raise ValueError("Goods Specification is required.")
        if total_qty <= 0:
            raise ValueError("Total Quantity must be greater than zero.")

        layout = data_store.get("zpl_layout", DEFAULT_ZPL_LAYOUT)
        max_digits = len(str(total_qty))
        zpl_blocks = []

        for i in range(1, total_qty + 1):
            counter = str(i).zfill(max_digits)
            suffix_length = 12 - len(counter) - 1
            barcode_base = bl_number[-suffix_length:] if suffix_length > 0 else ""
            barcode_value = f"{barcode_base},{counter}"

            # Ensure displayed BL has a single 'BL-' prefix
            display_bl = bl_number if bl_number.upper().startswith("BL-") else f"BL-{bl_number}"

            zpl = (
                "^XA\n"
                "^CI28\n"
                "^RB88^FS\n"
                f"^RFW,A^FD{barcode_value}^FS\n"
                f"^FT{layout['goods_spec_x']},{layout['goods_spec_y']}^A0N,25^FD{goods_spec}^FS\n"
                f"^FT{layout['bl_x']},{layout['bl_y']}^A0N,25^FD{display_bl}^FS\n"
                f"^FT{layout['count_x']},{layout['count_y']}^A0N,25^FD{i} of {total_qty}^FS\n"
                f"^FO{layout['barcode_x']},{layout['barcode_y']}^BY{layout['barcode_module_width']}^BCN,{layout['barcode_height']},Y,N,N^FD{barcode_value}^FS\n"
                "^XZ"
            )
            zpl_blocks.append(zpl)

        output_text.config(state="normal")
        output_text.delete("1.0", tk.END)
        output_text.insert(tk.END, "\n\n".join(zpl_blocks))
        output_text.config(state="disabled")
        status_label.config(text=f"✓ Generated {total_qty} ZPL label(s)")

    except ValueError as ve:
        messagebox.showerror("Invalid Input", str(ve))
    except Exception as exc:
        messagebox.showerror("Error", f"An unexpected error occurred:\n{exc}")


def clear_all():
    bl_var.set("")
    qty_var.set("")
    spec_var.set("")
    output_text.config(state="normal")
    output_text.delete("1.0", tk.END)
    output_text.config(state="disabled")
    status_label.config(text="Ready")


def copy_output():
    try:
        text_content = output_text.get("1.0", tk.END)
        if text_content.strip():
            root.clipboard_clear()
            root.clipboard_append(text_content)
            messagebox.showinfo("Success", "Output copied to clipboard!")
        else:
            messagebox.showwarning("Empty", "Nothing to copy. Generate ZPL first.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to copy: {e}")


def admin_login():
    pwd = simpledialog.askstring("Admin Login", "Enter admin password:", show="*")
    if pwd is None:
        return
    if pwd == data_store.get("password", "admin"):
        open_admin_panel()
    else:
        messagebox.showerror("Access Denied", "Incorrect password")


def open_admin_panel():
    panel = tk.Toplevel(root)
    panel.title("Admin - Manage Goods Specifications")
    panel.geometry("560x650")
    panel.transient(root)

    panel.columnconfigure(0, weight=1)
    panel.rowconfigure(0, weight=1)

    listbox = tk.Listbox(panel, selectmode=tk.SINGLE, font=("Arial", 10))
    listbox.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 0))

    for s in data_store.get("specs", []):
        listbox.insert(tk.END, s)

    entry_var = tk.StringVar()
    entry = ttk.Entry(panel, textvariable=entry_var, font=("Arial", 10))
    entry.grid(row=1, column=0, sticky="ew", padx=10, pady=8)

    btn_frame = ttk.Frame(panel)
    btn_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=8)
    btn_frame.columnconfigure((0, 1, 2, 3), weight=1)

    layout_vars = {}
    zpl_fields = [
        ("Goods Spec X", "goods_spec_x", 0),
        ("Goods Spec Y", "goods_spec_y", 0),
        ("BL X", "bl_x", 0),
        ("BL Y", "bl_y", 0),
        ("Count X", "count_x", 0),
        ("Count Y", "count_y", 0),
        ("Barcode X", "barcode_x", 0),
        ("Barcode Y", "barcode_y", 0),
        ("Barcode Module Width", "barcode_module_width", 1),
        ("Barcode Height", "barcode_height", 1),
    ]
    current_layout = data_store.get("zpl_layout", DEFAULT_ZPL_LAYOUT)
    for label, key, _ in zpl_fields:
        layout_vars[key] = tk.StringVar(value=str(current_layout.get(key, DEFAULT_ZPL_LAYOUT[key])))

    def add_spec():
        v = entry_var.get().strip()
        if not v:
            messagebox.showwarning("Empty", "Enter a specification to add")
            return
        if v in data_store.get("specs", []):
            messagebox.showinfo("Exists", "That specification already exists")
            return
        data_store.setdefault("specs", []).append(v)
        listbox.insert(tk.END, v)
        entry_var.set("")

    def edit_spec():
        sel = listbox.curselection()
        if not sel:
            messagebox.showwarning("Select", "Select an item to edit")
            return
        idx = sel[0]
        v = entry_var.get().strip()
        if not v:
            messagebox.showwarning("Empty", "Enter a specification")
            return
        data_store["specs"][idx] = v
        listbox.delete(idx)
        listbox.insert(idx, v)

    def delete_spec():
        sel = listbox.curselection()
        if not sel:
            messagebox.showwarning("Select", "Select an item to delete")
            return
        idx = sel[0]
        if messagebox.askyesno("Confirm", "Delete selected specification?"):
            listbox.delete(idx)
            data_store["specs"].pop(idx)

    def save_and_close():
        try:
            updated_layout = {}
            for label, key, min_value in zpl_fields:
                raw_value = layout_vars[key].get().strip()
                value = int(raw_value)
                if value < min_value:
                    raise ValueError(f"{label} must be >= {min_value}.")
                updated_layout[key] = value
            data_store["zpl_layout"] = updated_layout
        except ValueError as err:
            messagebox.showerror("Invalid Layout", str(err))
            return

        if save_data(data_store):
            spec_combobox['values'] = data_store.get('specs', [])
            panel.destroy()
            messagebox.showinfo("Saved", "Specifications saved")

    def on_select(evt):
        sel = listbox.curselection()
        if sel:
            entry_var.set(listbox.get(sel[0]))

    listbox.bind('<<ListboxSelect>>', on_select)

    add_btn = ttk.Button(btn_frame, text="Add", command=add_spec)
    add_btn.grid(row=0, column=0, sticky="ew", padx=3)
    edit_btn = ttk.Button(btn_frame, text="Edit", command=edit_spec)
    edit_btn.grid(row=0, column=1, sticky="ew", padx=3)
    del_btn = ttk.Button(btn_frame, text="Delete", command=delete_spec)
    del_btn.grid(row=0, column=2, sticky="ew", padx=3)
    save_btn = ttk.Button(btn_frame, text="Save", command=save_and_close)
    save_btn.grid(row=0, column=3, sticky="ew", padx=3)

    # Password change area
    pw_frame = ttk.LabelFrame(panel, text="Admin Password", padding=8)
    pw_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=8)
    pw_var = tk.StringVar()
    pw_entry = ttk.Entry(pw_frame, textvariable=pw_var, show='*')
    pw_entry.grid(row=0, column=0, sticky="ew", padx=(0,10))

    def change_password():
        new = pw_var.get().strip()
        if not new:
            messagebox.showwarning("Empty", "Enter a new password")
            return
        data_store['password'] = new
        pw_var.set("")
        messagebox.showinfo("Password", "Password updated. Save to persist.")

    pw_btn = ttk.Button(pw_frame, text="Set Password", command=change_password)
    pw_btn.grid(row=0, column=1)

    # ZPL layout area
    zpl_frame = ttk.LabelFrame(panel, text="ZPL Layout Settings", padding=8)
    zpl_frame.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 10))
    zpl_frame.columnconfigure(1, weight=1)

    for row_idx, (label, key, _) in enumerate(zpl_fields):
        ttk.Label(zpl_frame, text=label).grid(row=row_idx, column=0, sticky="w", padx=(0, 8), pady=2)
        ttk.Entry(zpl_frame, textvariable=layout_vars[key], width=12).grid(
            row=row_idx, column=1, sticky="w", pady=2
        )


root = tk.Tk()
root.title("ZPL Label Generator")
root.geometry("1000x750")
root.minsize(750, 550)

# Configure style
style = ttk.Style()
style.theme_use('clam')

# Configure grid weights
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=0)
root.rowconfigure(1, weight=1)
root.rowconfigure(2, weight=0)

# Title Bar (logo + company name + app title)
title_frame = tk.Frame(root, bg="#2E75B6", height=80)
title_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
title_frame.columnconfigure(0, weight=0)
title_frame.columnconfigure(1, weight=1)

# Logo (optional)
if LOGO_IMAGE:
    try:
        logo_label = tk.Label(title_frame, image=LOGO_IMAGE, bg="#2E75B6")
        logo_label.grid(row=0, column=0, rowspan=2, sticky="w", padx=16, pady=8)
        try:
            root.iconphoto(False, LOGO_IMAGE)
        except Exception:
            pass
    except Exception:
        pass

# Text block
text_block = tk.Frame(title_frame, bg="#2E75B6")
text_block.grid(row=0, column=1, sticky="w", padx=(12, 20), pady=8)
text_block.columnconfigure(0, weight=1)

company_label = tk.Label(text_block, text=COMPANY_NAME, font=("Segoe UI", 14, "bold"), bg="#2E75B6", fg="white")
company_label.grid(row=0, column=0, sticky="w")

title_label = tk.Label(text_block, text="ZPL Label Generator", font=("Segoe UI", 11), bg="#2E75B6", fg="#E8F0F7")
title_label.grid(row=1, column=0, sticky="w")

# Main Content
content_frame = ttk.Frame(root)
content_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=15)
content_frame.columnconfigure(0, weight=0)
content_frame.columnconfigure(1, weight=1)
content_frame.rowconfigure(1, weight=1)

# Left Panel - Input Section
input_panel = ttk.LabelFrame(content_frame, text="📝 Input Data", padding=15)
input_panel.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 10))
input_panel.columnconfigure(1, weight=1)

bl_var = tk.StringVar()
qty_var = tk.StringVar()
spec_var = tk.StringVar()
qty_var.set('1')

# BL Number
bl_label = ttk.Label(input_panel, text="BL Number *", font=("Arial", 11, "bold"))
bl_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
bl_entry = ttk.Entry(input_panel, textvariable=bl_var, font=("Arial", 10), width=25)
bl_entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 15))

# Total Quantity
qty_label = ttk.Label(input_panel, text="Total Quantity *", font=("Arial", 11, "bold"))
qty_label.grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 8))
qty_spinbox = ttk.Spinbox(input_panel, from_=1, to=9999, textvariable=qty_var, font=("Arial", 10), width=25)
qty_spinbox.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 15))

# Goods Specification
spec_label = ttk.Label(input_panel, text="Goods Specification *", font=("Arial", 11, "bold"))
spec_label.grid(row=4, column=0, columnspan=2, sticky="w", pady=(0, 8))
# Editable combobox for goods spec (admin-managed)
spec_combobox = ttk.Combobox(input_panel, textvariable=spec_var, font=("Arial", 10), width=25)
spec_combobox.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 20))
spec_combobox['values'] = data_store.get('specs', [])
spec_combobox['state'] = 'normal'

# Buttons
button_frame = ttk.Frame(input_panel)
button_frame.grid(row=6, column=0, columnspan=2, sticky="ew")
button_frame.columnconfigure(0, weight=1)
button_frame.columnconfigure(1, weight=1)

generate_button = ttk.Button(button_frame, text="🔧 Generate ZPL", command=generate_zpl)
generate_button.grid(row=0, column=0, sticky="ew", padx=(0, 5))

clear_button = ttk.Button(button_frame, text="🗑️ Clear", command=clear_all)
clear_button.grid(row=0, column=1, sticky="ew", padx=(5, 0))

# Right Panel - Output Section
output_panel = ttk.LabelFrame(content_frame, text="📤 Generated ZPL Output", padding=10)
output_panel.grid(row=0, column=1, rowspan=2, sticky="nsew")
output_panel.columnconfigure(0, weight=1)
output_panel.rowconfigure(0, weight=1)

# Output Text with Scrollbars
output_text = tk.Text(output_panel, wrap="none", state="disabled", font=("Courier New", 9), bg="#F5F5F5", fg="#1F1F1F")
output_text.grid(row=0, column=0, sticky="nsew")

scrollbar_y = ttk.Scrollbar(output_panel, orient="vertical", command=output_text.yview)
scrollbar_y.grid(row=0, column=1, sticky="ns")
output_text.configure(yscrollcommand=scrollbar_y.set)

scrollbar_x = ttk.Scrollbar(output_panel, orient="horizontal", command=output_text.xview)
scrollbar_x.grid(row=1, column=0, sticky="ew")
output_text.configure(xscrollcommand=scrollbar_x.set)

# Bottom Action Bar
action_frame = ttk.Frame(root)
action_frame.grid(row=2, column=0, sticky="nsew", padx=15, pady=10)
action_frame.columnconfigure(0, weight=0)
action_frame.columnconfigure(1, weight=0)
action_frame.columnconfigure(2, weight=1)

admin_button = ttk.Button(action_frame, text="🔒 Admin", command=admin_login)
admin_button.grid(row=0, column=0, sticky="w")

copy_button = ttk.Button(action_frame, text="📋 Copy Output", command=copy_output)
copy_button.grid(row=0, column=1, sticky="w", padx=(8,0))

status_label = ttk.Label(action_frame, text="Ready", font=("Arial", 9), foreground="#666666")
status_label.grid(row=0, column=2, sticky="e")

root.mainloop()
