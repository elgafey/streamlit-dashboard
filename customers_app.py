import streamlit as st
import pandas as pd
from fpdf import FPDF
import re

# إعدادات الصفحة
st.set_page_config(page_title="Ar Suhul - Smart Filter", layout="wide")

st.title("👥 Customer Account Statements")
st.markdown("---")

def clean_text(text):
    t = str(text).strip()
    if t.lower() in ['false', 'none', 'nan', '']:
        return "Journal Entry"
    return re.sub(r'[^\x00-\x7F]+', ' ', t).strip()

@st.cache_data 
def load_and_clean_data():
    url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/ar_suhul.csv"
    # منع التكرار والـ false تماماً
    df = pd.read_csv(url, encoding='utf-8', na_filter=False)
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df["debit"] = pd.to_numeric(df["debit"], errors="coerce").fillna(0)
    df["credit"] = pd.to_numeric(df["credit"], errors="coerce").fillna(0)
    df = df.drop_duplicates()
    return df

def generate_pdf(df_all, selected_partners):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    for partner in selected_partners:
        cust_df = df_all[df_all['partner_id'] == partner].copy().sort_values(by='date')
        cust_df['Running_Balance'] = (cust_df['debit'] - cust_df['credit']).cumsum()
        pdf.add_page()
        pdf.set_font("Helvetica", 'B', 16)
        pdf.cell(0, 10, f"Statement: {clean_text(partner)}", ln=True, align='C')
        pdf.set_font("Helvetica", '', 12)
        pdf.cell(0, 10, f"Final Balance: {cust_df['Running_Balance'].iloc[-1]:,.2f} EGP", ln=True, align='C')
        pdf.ln(10)
        # الجدول
        pdf.set_font("Helvetica", 'B', 10); pdf.set_fill_color(240, 240, 240)
        pdf.cell(30, 10, "Date", 1, 0, 'C', True)
        pdf.cell(70, 10, "Description", 1, 0, 'C', True)
        pdf.cell(30, 10, "Debit", 1, 0, 'C', True)
        pdf.cell(30, 10, "Credit", 1, 0, 'C', True)
        pdf.cell(30, 10, "Balance", 1, 1, 'C', True)
        pdf.set_font("Helvetica", '', 9)
        for _, row in cust_df.iterrows():
            pdf.cell(30, 8, str(row['date']), 1)
            pdf.cell(70, 8, clean_text(row['move_name'])[:40], 1)
            pdf.cell(30, 8, f"{row['debit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['credit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['Running_Balance']:,.2f}", 1, 1, 'R')
    return pdf.output()

# --- المنطق الرئيسي ---
try:
    df_main = load_and_clean_data()
    partners = sorted(df_main['partner_id'].unique().tolist())
    
    # الفلتر الذكي في الجنب
    st.sidebar.header("🔍 Search Filter")
    search_query = st.sidebar.text_input("Type Customer Name:", "")
    
    filtered_list = [p for p in partners if search_query.lower() in p.lower()]
    
    selected_partners = st.sidebar.multiselect(
        "Select Result(s):", 
        options=filtered_list,
        default=[]
    )

    if st.sidebar.checkbox("Select All Results"):
        selected_partners = filtered_list

    if selected_partners:
        if st.sidebar.button("🚀 Generate PDF"):
            pdf_out = generate_pdf(df_main, selected_partners)
            st.sidebar.download_button("📥 Download Now", data=bytes(pdf_out), file_name="Statements.pdf")
        
        for p in selected_partners:
            with st.expander(f"Preview: {p}", expanded=True):
                p_df = df_main[df_main['partner_id'] == p].copy().sort_values(by='date')
                p_df['Running_Balance'] = (p_df['debit'] - p_df['credit']).cumsum()
                st.table(p_df[['date', 'move_name', 'debit', 'credit', 'Running_Balance']])
    else:
        st.info("💡 Use the sidebar to search and select customers.")

except Exception as e:
    st.error(f"Error: {e}")
