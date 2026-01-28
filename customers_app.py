import streamlit as st
import pandas as pd
from fpdf import FPDF
import re
from io import BytesIO

# --- Page Configuration ---
st.set_page_config(page_title="Ar Suhul - Professional Statements", layout="wide")

st.title("👥 Customer Account Statements")
st.markdown("---")

# --- Function to clean text (Removes Arabic & replaces 'false') ---
def clean_for_pdf(text):
    text_str = str(text).strip()
    # Check if text is false or empty
    if not text_str or text_str.lower() in ['false', 'none', 'nan', '0']:
        return "Internal Entry / Opening Balance"
    # Remove non-ASCII characters to prevent PDF crashes
    return re.sub(r'[^\x00-\x7F]+', ' ', text_str).strip()

# -----------------------------
# Data Loading & Cleaning Logic
# -----------------------------
@st.cache_data 
def load_ar_suhul():
    url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/ar_suhul.csv"
    df = pd.read_csv(url, encoding='utf-8')
    
    # 1. Fix Duplication: Remove rows that are identical in key fields
    df = df.drop_duplicates(subset=['date', 'move_name', 'debit', 'credit', 'partner_id'])
    
    # 2. Date Formatting
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    return df.dropna(subset=["date"])

# -----------------------------
# Multi-Page PDF Generation Logic
# -----------------------------
def generate_pdf(df_all, selected_partners):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    for partner in selected_partners:
        # Filter data for each customer individually
        cust_df = df_all[df_all['partner_id'] == partner].sort_values(by='date')
        
        # 3. Calculate Running Balance
        cust_df['Running_Balance'] = (cust_df['debit'] - cust_df['credit']).cumsum()
        
        # Add a new page for each customer
        pdf.add_page()
        
        # Report Header
        pdf.set_font("Helvetica", 'B', 16)
        pdf.cell(0, 10, f"Statement: {clean_for_pdf(partner)}", ln=True, align='C')
        pdf.set_font("Helvetica", '', 12)
        pdf.cell(0, 10, f"Total Outstanding: {cust_df['Running_Balance'].iloc[-1]:,.2f} EGP", ln=True, align='C')
        pdf.ln(10)
        
        # Table Header Styling
        pdf.set_font("Helvetica", 'B', 10)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(30, 10, "Date", 1, 0, 'C', True)
        pdf.cell(70, 10, "Description", 1, 0, 'C', True)
        pdf.cell(30, 10, "Debit", 1, 0, 'C', True)
        pdf.cell(30, 10, "Credit", 1, 0, 'C', True)
        pdf.cell(30, 10, "Balance", 1, 1, 'C', True)
        
        # Table Body Content
        pdf.set_font("Helvetica", '', 9)
        for _, row in cust_df.iterrows():
            pdf.cell(30, 8, str(row['date']), 1)
            # Replace 'false' with clean text
            pdf.cell(70, 8, clean_for_pdf(row['move_name'])[:40], 1)
            pdf.cell(30, 8, f"{row['debit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['credit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['Running_Balance']:,.2f}", 1, 1, 'R')

    return pdf.output()

# -----------------------------
# User Interface (Streamlit)
# -----------------------------
try:
    df_all = load_ar_suhul()
    
    # Sidebar for bulk selection
    st.sidebar.header("Batch Export Options")
    partners = sorted(df_all['partner_id'].unique().tolist())
    selected_partners = st.sidebar.multiselect("Select Customers for PDF", options=partners)

    if selected_partners:
        # Action Buttons
        if st.sidebar.button("🚀 Generate Combined PDF"):
            with st.spinner('Preparing Multi-Page Document...'):
                pdf_bytes = generate_pdf(df_all, selected_partners)
                st.sidebar.download_button(
                    label="📥 Download Statements PDF",
                    data=bytes(pdf_bytes),
                    file_name="All_Customer_Statements.pdf",
                    mime="application/pdf"
                )
            st.success(f"Success! {len(selected_partners)} customer pages generated.")

        # On-screen Previews
        for p in selected_partners:
            with st.expander(f"Live Preview - {p}"):
                p_df = df_all[df_all['partner_id'] == p].sort_values(by='date')
                p_df['Running_Balance'] = (p_df['debit'] - p_df['credit']).cumsum()
                st.dataframe(p_df[['date', 'move_name', 'debit', 'credit', 'Running_Balance']], use_container_width=True)
    else:
        st.info("Choose one or more customers from the sidebar to start.")

except Exception as e:
    st.error(f"System Error: {e}")
