import streamlit as st
import pandas as pd
from fpdf import FPDF
from io import BytesIO

# Page Configuration
st.set_page_config(page_title="Ar Suhul - Account Statements", layout="wide")

st.title("👥 Customer Account Statements")
st.markdown("---")

# -----------------------------
# Data Loading
# -----------------------------
@st.cache_data 
def load_ar_suhul():
    url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/ar_suhul.csv"
    df = pd.read_csv(url, encoding='utf-8')
    # Convert date and ensure sorting 
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    return df.dropna(subset=["date"])

# -----------------------------
# PDF Generation (Multi-Page)
# -----------------------------
def generate_pdf(df_all, selected_partners):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    for partner in selected_partners:
        # Filter and calculate for the specific partner
        cust_df = df_all[df_all['partner_id'] == partner].sort_values(by='date')
        cust_df['Running_Balance'] = (cust_df['debit'] - cust_df['credit']).cumsum()
        
        # Add a fresh page for each customer
        pdf.add_page()
        
        # Statement Header
        pdf.set_font("Helvetica", 'B', 16)
        pdf.cell(0, 10, f"Statement of Account: {partner}", ln=True, align='C')
        pdf.set_font("Helvetica", '', 12)
        pdf.cell(0, 10, f"Final Outstanding Balance: {cust_df['Running_Balance'].iloc[-1]:,.2f} EGP", ln=True, align='C')
        pdf.ln(10)
        
        # Table Header
        pdf.set_font("Helvetica", 'B', 10)
        pdf.set_fill_color(240, 240, 240) # Light grey background
        pdf.cell(35, 10, "Date", 1, 0, 'C', True)
        pdf.cell(65, 10, "Movement Name", 1, 0, 'C', True)
        pdf.cell(30, 10, "Debit", 1, 0, 'C', True)
        pdf.cell(30, 10, "Credit", 1, 0, 'C', True)
        pdf.cell(30, 10, "Balance", 1, 1, 'C', True)
        
        # Table Body
        pdf.set_font("Helvetica", '', 9)
        for _, row in cust_df.iterrows():
            pdf.cell(35, 8, str(row['date']), 1)
            pdf.cell(65, 8, str(row['move_name'])[:35], 1) # Trim very long names
            pdf.cell(30, 8, f"{row['debit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['credit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['Running_Balance']:,.2f}", 1, 1, 'R')

    return pdf.output()

# -----------------------------
# User Interface
# -----------------------------
try:
    df_all = load_ar_suhul()
    
    # Selection Sidebar
    st.sidebar.header("Export Controls")
    partners = sorted(df_all['partner_id'].unique().tolist())
    selected_partners = st.sidebar.multiselect("Choose Customers for PDF Export", options=partners)

    if selected_partners:
        # Export Button
        if st.sidebar.button("Generate Combined PDF"):
            with st.spinner('Compiling Multi-Page PDF...'):
                pdf_output = generate_pdf(df_all, selected_partners)
                st.sidebar.download_button(
                    label="📥 Download PDF Statement",
                    data=bytes(pdf_output),
                    file_name="Customer_Batch_Statements.pdf",
                    mime="application/pdf"
                )
            st.success(f"Success! Generated {len(selected_partners)} pages.")

        # Screen Preview
        for p in selected_partners:
            with st.expander(f"View Statement: {p}"):
                p_df = df_all[df_all['partner_id'] == p].sort_values(by='date')
                p_df['Running_Balance'] = (p_df['debit'] - p_df['credit']).cumsum()
                st.dataframe(p_df[['date', 'move_name', 'debit', 'credit', 'Running_Balance']], use_container_width=True)
    else:
        st.info("Select one or more customers from the sidebar to generate the multi-page report.")

except Exception as e:
    st.error(f"Error loading or processing data: {e}")
