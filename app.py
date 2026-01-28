import streamlit as st
import pandas as pd
from io import BytesIO

# -----------------------------
# Load CSV from GitHub
# -----------------------------
url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/raw_material_daily.csv"
df = pd.read_csv(url)

# Convert date column to datetime
df["date"] = pd.to_datetime(df["date"])

# -----------------------------
# Streamlit UI
# -----------------------------
st.title("📦 Raw Material Daily Consumption Report")
st.write(")")

# -----------------------------
# Filters
# -----------------------------
st.sidebar.header("Filters")

# Day filter
unique_days = sorted(df["date"].dt.date.unique())
selected_day = st.sidebar.selectbox("اختر اليوم", ["All"] + [str(d) for d in unique_days])

if selected_day != "All":
    df = df[df["date"].dt.date == pd.to_datetime(selected_day).date()]

# -----------------------------
# Display Table
# -----------------------------
st.subheader("📊 Daily Raw Material Usage")
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

