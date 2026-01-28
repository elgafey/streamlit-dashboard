import streamlit as st
import pandas as pd
from io import BytesIO

# -----------------------------
# Load CSV from GitHub
# -----------------------------
url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/raw_material_daily.csv"
df = pd.read_csv(url)

# -----------------------------
# Fix date column safely
# -----------------------------
# 1) تحويل التاريخ لنص (عشان لو فيه قيم ناقصة أو غريبة)
df["date"] = df["date"].astype(str).str.strip()

# 2) تحويل التاريخ لـ datetime بدون ما يقع
df["date"] = pd.to_datetime(df["date"], errors="coerce")

# 3) حذف الصفوف اللي فيها تاريخ بايظ
df = df.dropna(subset=["date"])

# -----------------------------
# Streamlit UI
# -----------------------------
st.title("📦 Raw Material Daily Report")
st.write("")

# -----------------------------
# Filters
# -----------------------------
st.sidebar.header("Filters")

# Date Range Picker
start_date, end_date = st.sidebar.date_input(
    "Date From → To",
    value=[df["date"].min(), df["date"].max()],
    min_value=df["date"].min(),
    max_value=df["date"].max()
)

# -----------------------------
# Convert Streamlit dates to datetime
# -----------------------------
start_date = pd.to_datetime(start_date)
end_date = pd.to_datetime(end_date)

# -----------------------------
# Apply filter
# -----------------------------
df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]

# -----------------------------
# Display Table
# -----------------------------
st.subheader("📊 Raw Material Usage (Filtered)")
st.dataframe(df, use_container_width=True)

# -----------------------------
# Download as Excel
# -----------------------------
def to_excel(df):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine="xlsxwriter")
    df.to_excel(writer, index=False, sheet_name="RawMaterialDaily")
    writer.close()
    processed_data = output.getvalue()
    return processed_data

excel_file = to_excel(df)

st.download_button(
    label="⬇️ Download Excel",
    data=excel_file,
    file_name="raw_material_daily.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
