import streamlit as st
import pandas as pd
from fpdf import FPDF
import re

# 1. إعداد الصفحة
st.set_page_config(page_title="Suhul Albeeah - Matching Odoo", layout="wide")

def clean_text(text):
    t = str(text).strip()
    if not t or t.lower() in ['none', 'nan']: return "Entry"
    return re.sub(r'[^\x00-\x7F]+', ' ', t).strip()

@st.cache_data 
def load_data():
    try:
        url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/ar_suhul.csv"
        df = pd.read_csv(url, encoding='utf-8')
        
        # تنظيف البيانات الأساسية
        df['date'] = df['date'].str.split(' GMT').str[0]
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df["debit"] = pd.to_numeric(df["debit"], errors="coerce").fillna(0)
        df["credit"] = pd.to_numeric(df["credit"], errors="coerce").fillna(0)
        
        # --- مطابقة أودو (Odoo Matching) ---
        # الفلترة بناءً على الحسابات اللي في الصورة لضمان تطابق الإجمالي
        target_accounts = [1209001, 1209002, 1211000, 1213000]
        df = df[df['account_code'].isin(target_accounts)]
        
        df["net"] = df["debit"] - df["credit"]
        df['partner_id'] = df['partner_id'].astype(str).str.strip()
        return df
    except:
        return pd.DataFrame()

def generate_pdf(df_all, selected_partners):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    for partner in selected_partners:
        cust_df = df_all[df_all['partner_id'] == partner].copy().sort_values(by='date')
        if cust_df.empty: continue
        cust_df['Running_Balance'] = cust_df['net'].cumsum()
        
        pdf.add_page()
        # الهيدر الجديد لتجنب الأخطاء
        pdf.set_font("Helvetica", 'B', 14)
        pdf.cell(0, 8, "SUHUL ALBEEAH", ln=True, align='L')
        pdf.set_font("Helvetica", '', 10)
        pdf.cell(0, 5, "Environmental Plains for Raw Material Recycling", ln=True, align='L')
        pdf.cell(0, 5, "VAT Number: 300451393600003", ln=True, align='L')
        pdf.ln(5)
        
        pdf.set_font("Helvetica", 'B', 16)
        pdf.cell(0, 10, "PARTNER LEDGER", ln=True, align='C')
        pdf.set_font("Helvetica", 'B', 12)
        pdf.cell(0, 10, f"Customer: {clean_text(partner)}", ln=True)
        
        # الجدول
        pdf.set_font("Helvetica", 'B', 10); pdf.set_fill_color(240, 240, 240)
        cols = [("Date", 30), ("Description", 70), ("Debit", 30), ("Credit", 30), ("Balance", 30)]
        for h, w in cols: pdf.cell(w, 10, h, 1, 0, 'C', True)
        pdf.ln()
        
        pdf.set_font("Helvetica", '', 9)
        for _, row in cust_df.iterrows():
            d = row['date'].strftime('%Y-%m-%d') if pd.notnull(row['date']) else "N/A"
            pdf.cell(30, 8, d, 1)
            pdf.cell(70, 8, clean_text(row['move_name'])[:40], 1)
            pdf.cell(30, 8, f"{row['debit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['credit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['Running_Balance']:,.2f}", 1, 1, 'R')
    return bytes(pdf.output(dest='S'))

# --- Logic ---
df = load_data()

if not df.empty:
    st.sidebar.title("Fiscal Control")
    available_years = sorted(df['date'].dt.year.dropna().unique().astype(int).tolist(), reverse=True)
    selected_year = st.sidebar.selectbox("Year for Trial Balance:", available_years)
    
    tab1, tab2 = st.tabs(["📑 Ledger", "⚖️ Trial Balance"])

    with tab1:
        st.subheader("Individual Statements")
        all_p = sorted(df['partner_id'].unique().tolist())
        select_all = st.checkbox("Select All (Matching Total)")
        selected = all_p if select_all else st.multiselect("Pick Customers:", options=all_p)

        if selected:
            # الداشبورد مطابق لأودو
            stats_df = df[df['partner_id'].isin(selected)]
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Debit", f"{stats_df['debit'].sum():,.2f}")
            m2.metric("Total Credit", f"{stats_df['credit'].sum():,.2f}")
            m3.metric("Net Balance", f"{stats_df['net'].sum():,.2f}")
            
            if st.sidebar.button(f"Generate PDF ({len(selected)})"):
                st.session_state['pdf_blob'] = generate_pdf(df, selected)
            
            if 'pdf_blob' in st.session_state:
                st.sidebar.download_button("📥 Download PDF", st.session_state['pdf_blob'], "Suhul_Report.pdf")

            for p in selected[:3]:
                with st.expander(f"Preview: {p}"):
                    p_df = df[df['partner_id'] == p].copy().sort_values(by='date')
                    p_df['Running_Balance'] = p_df['net'].cumsum()
                    st.table(p_df[['date', 'move_name', 'debit', 'credit', 'Running_Balance']].tail(10))

    with tab2:
        st.subheader(f"Trial Balance - Year {selected_year}")
        all_entities = df[['partner_id']].drop_duplicates()
        
        init_df = df[df['date'].dt.year < selected_year].groupby('partner_id')['net'].sum().reset_index()
        init_df.columns = ['partner_id', 'Initial Balance']
        
        peri_df = df[df['date'].dt.year == selected_year].groupby('partner_id')['net'].sum().reset_index()
        peri_df.columns = ['partner_id', 'Period Balance']
        
        tb_df = pd.merge(all_entities, init_df, on='partner_id', how='left')
        tb_df = pd.merge(tb_df, peri_df, on='partner_id', how='left')
        tb_df[['Initial Balance', 'Period Balance']] = tb_df[['Initial Balance', 'Period Balance']].fillna(0)
        tb_df['Ending Balance'] = tb_df['Initial Balance'] + tb_df['Period Balance']
        
        st.dataframe(tb_df.sort_values(by='Ending Balance', ascending=False).style.format({
            'Initial Balance': '{:,.2f}', 'Period Balance': '{:,.2f}', 'Ending Balance': '{:,.2f}'
        }), use_container_width=True)
        
        st.divider()
        t1, t2, t3 = st.columns(3)
        t1.metric("Total Opening", f"{tb_df['Initial Balance'].sum():,.2f}")
        t2.metric("Total Period", f"{tb_df['Period Balance'].sum():,.2f}")
        t3.metric("Total Final", f"{tb_df['Ending Balance'].sum():,.2f}")
else:
    st.error("Check CSV link.")
