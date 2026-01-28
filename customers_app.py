import streamlit as st
import pandas as pd
import pdfkit
from io import BytesIO

st.set_page_config(page_title="Customer PDF Report", layout="wide")

# -----------------------------
# Load Data
# -----------------------------
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/raw_material_daily.csv"
    df = pd.read_csv(url, encoding="utf-8")
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df = df.dropna(subset=["date"])
    return df

df = load_data()

# -----------------------------
# English-only cleaner
# -----------------------------
def keep_english(text):
    if not isinstance(text, str):
        return text
    if "/" in text:
        return text.split("/")[0].strip()
    return "".join(ch for ch in text if not ("\u0600" <= ch <= "\u06FF")).strip()

df["partner_id"] = df["partner_id"].apply(keep_english)
df["product_name"] = df["product_name"].apply(keep_english)

# -----------------------------
# Sidebar Filters
# -----------------------------
st.sidebar.header("Filters")

min_date = df["date"].min()
max_date = df["date"].max()

date_input = st.sidebar.date_input(
    "Select Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if isinstance(date_input, (list, tuple)) and len(date_input) == 2:
    start_date, end_date = date_input
else:
    start_date = end_date = date_input

mask = (df["date"] >= start_date) & (df["date"] <= end_date)
df_filtered = df.loc[mask]

st.title("📦 Customer Report")

st.dataframe(df_filtered, use_container_width=True)

# -----------------------------
# PDF Generator
# -----------------------------
def generate_customers_pdf(df):
    customers = df["partner_id"].dropna().unique()

    html = """
    <html>
    <head>
        <style>
            body { font-family: Arial; margin: 40px; }
            h1 { text-align: center; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
            .page-break { page-break-after: always; }
        </style>
    </head>
    <body>
    """

    for i, cust in enumerate(customers):
        cust_df = df[df["partner_id"] == cust]

        html += f"<h1>Customer: {cust}</h1>"
        html += cust_df.to_html(index=False)

        if i < len(customers) - 1:
            html += '<div class="page-break"></div>'

    html += "</body></html>"

    pdf = pdfkit.from_string(html, False)
    return pdf

# -----------------------------
# Button to generate PDF
# -----------------------------
st.sidebar.subheader("PDF Export")

if st.sidebar.button("Generate PDF (One Page Per Customer)"):
    pdf_bytes = generate_customers_pdf(df_filtered)

    st.sidebar.download_button(
        label="📄 Download Customers PDF",
        data=pdf_bytes,
        file_name="customers_report.pdf",
        mime="application/pdf"
    )
