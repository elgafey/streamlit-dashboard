import streamlit as st
import pandas as pd
from fpdf import FPDF
import re

# Page Settings
st.set_page_config(page_title="Ar Suhul - Account Statements", layout="wide")

st.title("Customer Account Statements")
st.markdown("---")

# --- Function to clean text from Arabic for PDF ---
def clean_for_pdf(text):
    if not text or pd.isna(text):
        return ""
    # This regex removes any character that is not a standard English letter, number, or symbol
    # It replaces Arabic letters with an empty space to prevent PDF crashes
    return re.sub(r'[^\x00-\x7F]+', ' ', str(text)).strip()

# -----------------------------
# Data Loading
# -----------------------------
@st.cache_data 
def load_ar_suhul():
    url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/ar_suhul.csv"
    df = pd.read_csv(url, encoding='utf-8')
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    return df.dropna(subset=["date"])

# -----------------------------
# Multi-Page PDF Generation
# -----------------------------
def generate_pdf(df_all, selected_partners):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    for partner in selected_partners:
        # Filter and sort data for each partner
        cust_df = df_all[df_all['partner_id'] == partner].sort_values(by='date')
        cust_df['Running_Balance'] = (cust_df['debit'] - cust_df['credit']).cumsum()
        
        pdf.add_page()
        
        # Header - We clean the partner name here
        pdf.set_font("Helvetica", 'B', 16)
        clean_partner = clean_for_pdf(partner)
        pdf.cell(0, 10, f"Statement: {clean_partner}", ln=True, align='C')
        pdf.set_font("Helvetica", '', 12)
        pdf.cell(0, 10, f"Current Balance: {cust_df['Running_Balance'].iloc[-1]:,.2f} EGP", ln=True, align='C')
        pdf.ln(10)
        
        # Table Header
        pdf.set_font("Helvetica", 'B', 10)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(35, 10, "Date", 1, 0, 'C', True)
        pdf.cell(65, 10, "Description", 1, 0, 'C', True)
        pdf.cell(30, 10, "Debit", 1, 0, 'C', True)
        pdf.cell(30, 10, "Credit", 1, 0, 'C', True)
        pdf.cell(30, 10, "Balance", 1, 1, 'C', True)
        
        # Table Rows
        pdf.set_font("Helvetica", '', 9)
        for _, row in cust_df.iterrows():
            pdf.cell(35, 8, str(row['date']), 1)
            # We clean the move_name from any Arabic characters like "ش" or "م"
            clean_move = clean_for_pdf(row['move_name'])
            pdf.cell(65, 8, clean_move[:35], 1) 
            pdf.cell(30, 8, f"{row['debit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['credit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['Running_Balance']:,.2f}", 1, 1, 'R')

    return pdf.output()

# -----------------------------
# UI Elements
# -----------------------------
try:
    df_all = load_ar_suhul()
    partners = sorted(df_all['partner_id'].unique().tolist())
    
    st.sidebar.header("Export Options")
    selected_partners = st.sidebar.multiselect("Select Customers", options=partners)

    if selected_partners:
        if st.sidebar.button("Generate All Statements PDF"):
            pdf_bytes = generate_pdf(df_all, selected_partners)
            st.sidebar.download_button(
                label="📥 Download PDF",
                data=bytes(pdf_bytes),
                file_name="Batch_Statements.pdf",
                mime="application/pdf"
            )
            st.success(f"Generated {len(selected_partners)} pages successfully!")
        
        # Display data on screen
        for p in selected_partners:
            with st.expander(f"Preview: {p}"):
                p_df = df_all[df_all['partner_id'] == p].sort_values(by='date')
                p_df['Running_Balance'] = (p_df['debit'] - p_df['credit']).cumsum()
                st.dataframe(p_df[['date', 'move_name', 'debit', 'credit', 'Running_Balance']], use_container_width=True)
    else:
        st.info("Select customers from the sidebar to start.")

except Exception as e:
    st.error(f"Error: {e}")
