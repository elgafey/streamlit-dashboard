import streamlit as st
import pandas as pd
from fpdf import FPDF
from arabic_reshaper import reshape
from bidi.algorithm import get_display
from io import BytesIO

# Page Configuration
st.set_page_config(page_title="Ar Suhul - Multi-Page PDF", layout="wide")

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
# Multi-Page PDF Logic
# -----------------------------
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Ar Suhul - Monthly Statements', ln=True, align='C')
        self.ln(5)

def generate_multi_page_pdf(df_all, selected_partners):
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    for partner in selected_partners:
        # 1. Filter and calculate for each partner
        cust_df = df_all[df_all['partner_id'] == partner].sort_values(by='date')
        cust_df['Running_Balance'] = (cust_df['debit'] - cust_df['credit']).cumsum()
        
        # 2. Add a new page for each customer
        pdf.add_page()
        
        # Partner Name Header
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, f"Customer: {partner}", ln=True)
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 10, f"Total Balance: {cust_df['Running_Balance'].iloc[-1]:,.2f} EGP", ln=True)
        pdf.ln(5)
        
        # 3. Table Header
        pdf.set_fill_color(200, 220, 255)
        pdf.cell(30, 10, "Date", border=1, fill=True)
        pdf.cell(60, 10, "Move Name", border=1, fill=True)
        pdf.cell(30, 10, "Debit", border=1, fill=True)
        pdf.cell(30, 10, "Credit", border=1, fill=True)
        pdf.cell(40, 10, "Balance", border=1, fill=True)
        pdf.ln()
        
        # 4. Table Rows
        for _, row in cust_df.iterrows():
            pdf.cell(30, 8, str(row['date']), border=1)
            pdf.cell(60, 8, str(row['move_name']), border=1)
            pdf.cell(30, 8, f"{row['debit']:,.2f}", border=1)
            pdf.cell(30, 8, f"{row['credit']:,.2f}", border=1)
            pdf.cell(40, 8, f"{row['Running_Balance']:,.2f}", border=1)
            pdf.ln()
            
    return pdf.output()

# -----------------------------
# UI Layout
# -----------------------------
try:
    df_all = load_ar_suhul()
    partners = sorted(df_all['partner_id'].unique().tolist())
    
    st.sidebar.header("Batch Export Settings")
    selected_partners = st.sidebar.multiselect("Select Partners for PDF", options=partners)

    if selected_partners:
        # Main Button for Multi-Page PDF
        if st.sidebar.button("🚀 Generate All-in-One PDF"):
            pdf_output = generate_multi_page_pdf(df_all, selected_partners)
            st.sidebar.download_button(
                label="📥 Download Multi-Page PDF",
                data=bytes(pdf_output),
                file_name="All_Customers_Statements.pdf",
                mime="application/pdf"
            )
            st.success(f"PDF Generated successfully for {len(selected_partners)} partners!")

        # Display previews on screen
        for p in selected_partners:
            with st.expander(f"Preview: {p}"):
                pdf_df = df_all[df_all['partner_id'] == p].sort_values(by='date')
                pdf_df['Running_Balance'] = (pdf_df['debit'] - pdf_df['credit']).cumsum()
                st.dataframe(pdf_df[['date', 'move_name', 'debit', 'credit', 'Running_Balance']], use_container_width=True)

    else:
        st.info("Select customers from the sidebar to generate the multi-page PDF.")

except Exception as e:
    st.error(f"Error: {e}")
