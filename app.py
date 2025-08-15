import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from io import BytesIO
from contextlib import contextmanager

# DATABASE SETUP
DB_NAME = "inventory.db"

@contextmanager
def db_connection():
    conn = sqlite3.connect(DB_NAME)
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                quantity INTEGER,
                price REAL
            )
        """)
        conn.commit()

def view_inventory():
    with db_connection() as conn:
        return pd.read_sql("SELECT * FROM inventory", conn)

def add_item(name, quantity, price):
    with db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO inventory (name, quantity, price) VALUES (?, ?, ?)", (name, quantity, price))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

def update_item(item_id, quantity, price):
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE inventory SET quantity=?, price=? WHERE id=?", (quantity, price, item_id))
        conn.commit()

def delete_item(item_id):
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM inventory WHERE id=?", (item_id,))
        conn.commit()

def get_low_stock_items(threshold=5):
    with db_connection() as conn:
        return pd.read_sql(f"SELECT * FROM inventory WHERE quantity < {threshold}", conn)

# STREAMLIT CONFIG
st.set_page_config(page_title="Inventory Dashboard", layout="wide")
init_db()

# HEADER
st.markdown("<h1 style='text-align: center;color:blue; font-family:cambria'>Inventory Management System</h1>", unsafe_allow_html=True)

# DARK MODE TOGGLE (chart + basic UI simulation)
dark_mode = st.sidebar.toggle("🌙 Enable Dark Mode", value=False)
chart_template = "plotly_dark" if dark_mode else "plotly_white"

# Simulated dark theme using CSS (Streamlit doesn't support full toggle natively)
if dark_mode:
    st.markdown("""
        <style>
            .stApp, .main {
                background-color: #1e1e1e;
                color: white;
            }
            .stButton>button {
                background-color: #444444;
                color: white;
                border: 1px solid white;
            }
            .stTextInput > div > div > input,
            .stNumberInput > div > div > input {
                background-color: #2d2d2d;
                color: white;
            }
            .stSelectbox > div > div {
                background-color: #2d2d2d;
                color: white;
            }
            .stDownloadButton>button {
                background-color: #444444;
                color: white;
            }
        </style>
    """, unsafe_allow_html=True)

# METRICS
df = view_inventory()
total_items = df["quantity"].sum() if not df.empty else 0
total_value = (df["quantity"] * df["price"]).sum() if not df.empty else 0
low_stock_count = len(get_low_stock_items())

col1, col2, col3 = st.columns(3)
col1.metric("📦 Total Stock Units", f"{total_items:,}")
col2.metric("💰 Total Inventory Value", f"₹{total_value:,.2f}")
col3.metric("⚠️ Low Stock Items", low_stock_count)

# MENU
menu = st.tabs(["📋 View Inventory", "➕ Add Item", "✏️ Update Item", "🗑️ Delete Item", "📊 Reports", "📥 Import / Export"])

# VIEW INVENTORY
with menu[0]:
    st.subheader("Current Inventory")
    if not df.empty:
        search = st.text_input("🔍 Search by Item Name")
        filtered_df = df[df["name"].str.contains(search, case=False)] if search else df
        st.dataframe(filtered_df, use_container_width=True)
    else:
        st.info("No items in inventory.")

# ADD ITEM
with menu[1]:
    st.subheader("Add New Item")
    name = st.text_input("Item Name")
    qty = st.number_input("Quantity", min_value=0, step=1)
    price = st.number_input("Price", min_value=0.0, step=0.01)
    if st.button("Add Item"):
        if name and qty >= 0 and price >= 0:
            if add_item(name, qty, price):
                st.success(f"Item '{name}' added successfully!")
            else:
                st.warning(f"Item '{name}' already exists!")
        else:
            st.error("Please fill all fields correctly.")

# UPDATE ITEM
with menu[2]:
    st.subheader("Update Item")
    if not df.empty:
        item = st.selectbox("Select Item", df["name"])
        item_id = int(df[df["name"] == item]["id"].values[0])
        current_qty = int(df[df["name"] == item]["quantity"].values[0])
        new_qty = st.number_input("New Quantity", min_value=0, step=1, value=current_qty)
        new_price = st.number_input("New Price", min_value=0.0, step=0.01)
        if st.button("Update Item"):
            update_item(item_id, new_qty, new_price)
            st.success(f"Item '{item}' updated successfully!")
        restock_qty = st.number_input("Add to Quantity", min_value=0, step=1)
        if st.button("Restock Item"):
            update_item(item_id, current_qty + restock_qty, new_price)
            st.success(f"Item '{item}' restocked by {restock_qty} units.")
    else:
        st.warning("No items available to update.")

# DELETE ITEM
with menu[3]:
    st.subheader("Delete Item")
    if not df.empty:
        item = st.selectbox("Select Item to Delete", df["name"])
        item_id = int(df[df["name"] == item]["id"].values[0])
        if st.button("Delete Item"):
            delete_item(item_id)
            st.success(f"Item '{item}' deleted successfully!")
    else:
        st.warning("No items to delete.")

# REPORTS
with menu[4]:
    st.subheader("Inventory Reports")
    if not df.empty:
        fig1 = px.bar(df, x="name", y="quantity", title="Stock Quantity by Item", template=chart_template)
        fig2 = px.pie(df, names="name", values="quantity", title="Stock Distribution", template=chart_template)
        fig3 = px.bar(df, x="name", y=(df["quantity"] * df["price"]), labels={"y": "Total Value"}, title="Inventory Value by Item", template=chart_template)
        col1, col2 = st.columns(2)
        col1.plotly_chart(fig1, use_container_width=True)
        col2.plotly_chart(fig2, use_container_width=True)
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("No data to display in reports.")

# IMPORT/EXPORT
with menu[5]:
    st.subheader("📥 Import from Excel")
    uploaded_file = st.file_uploader("Upload Excel File (.xlsx)", type=["xlsx"])
    if uploaded_file:
        try:
            excel_df = pd.read_excel(uploaded_file)
            if all(col in excel_df.columns for col in ["Name", "Quantity", "Price"]):
                added_count = 0
                for _, row in excel_df.iterrows():
                    success = add_item(row["Name"], int(row["Quantity"]), float(row["Price"]))
                    if success:
                        added_count += 1
                st.success(f"Imported {added_count} new items successfully!")
            else:
                st.error("Excel must have columns: Name, Quantity, Price")
        except Exception as e:
            st.error(f"Error reading file: {e}")

    st.subheader("📤 Export to Excel")
    if st.button("Download Inventory as Excel"):
        if not df.empty:
            output = BytesIO()
            df.to_excel(output, index=False)
            output.seek(0)
            st.download_button("Download File", output, file_name="inventory_export.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.warning("No inventory data to export.")

    st.subheader("📤 Export as CSV")
    if st.button("Download Inventory as CSV"):
        if not df.empty:
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV", csv, "inventory.csv", "text/csv")
        else:
            st.warning("No inventory data to export.")
