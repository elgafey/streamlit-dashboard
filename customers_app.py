import streamlit as st
import pandas as pd
from weasyprint import HTML
import io

# 1. Page Configuration
st.set_page_config(page_title="Suhul Albeeah | Financial Reports", layout="wide")

@st.cache_data 
def load_data():
    try:
        url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/ar_suhul.csv"
        df = pd.read_csv(url)
        df['date'] = pd.to_datetime(df['date'].str.split(' GMT').str[0], errors='coerce')
        # Account filtering to match Odoo records
        target_accounts = [1209001, 1209002, 1211000, 1213000]
        df = df[df['account_code'].isin(target_accounts)]
        df["debit"] = pd.to_numeric(df["debit"], errors="coerce").fillna(0)
        df["credit"] = pd.to_numeric(df["credit"], errors="coerce").fillna(0)
        df["net"] = df["debit"] - df["credit"]
        df['partner_id'] = df['partner_id'].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"Data Load Error: {e}")
        return pd.DataFrame()

def generate_pdf_multi_page(df_filtered, selected_partners):
    """Generate Odoo-style PDF with each partner on a new page"""
    html_content = """
    <html dir="rtl" lang="ar">
    <head>
        <meta charset="utf-8">
        <style>
            @page { size: A4; margin: 1cm; }
            body { font-family: 'Arial', sans-serif; direction: rtl; color: #333; }
            .page-container { page-break-after: always; }
            .header { border-bottom: 3px solid #1a237e; margin-bottom: 20px; padding-bottom: 10px; }
            .company-name { color: #1a237e; font-size: 22px; font-weight: bold; }
            .report-title { text-align: center; font-size: 20px; margin: 20px 0; background: #f5f5f5; padding: 10px; }
            table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 11px; }
            th { background-color: #1a237e; color: white; padding: 10px; border: 1px solid #ddd; }
            td { padding: 8px; border: 1px solid #ddd; text-align: center; }
            .summary-box { margin-top: 20px; border: 2px solid #1a237e; width: 280px; float: left; padding: 15px; }
            .clearfix { clear: both; }
        </style>
    </head>
    <body>
    """

    for partner in selected_partners:
        cust_df = df_filtered[df_filtered['partner_id'] == partner].sort_values('date')
        if cust_df.empty: continue
        
        running_balance = 0
        html_content += f"""
        <div class="page-container">
            <div class="header">
                <div class="company-name">شركة سهول البيئة لتدوير المواد الأولية</div>
                <div>VAT Number: 300451393600003</div>
            </div>
            <div class="report-title">Partner Ledger</div>
            <div style="font-size: 14px; margin-bottom: 20px;">
                <strong>Partner:</strong> {partner}<br>
                <strong>Date:</strong> {pd.Timestamp.now().strftime('%Y-%m-%d')}
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Description</th>
                        <th>Debit</th>
                        <th>Credit</th>
                        <th>Balance</th>
                    </tr>
                </thead>
                <tbody>
        """
        for _, row in cust_df.iterrows():
            running_balance += row['net']
            html_content += f"""
                    <tr>
                        <td>{row['date'].strftime('%Y-%m-%d')}</td>
                        <td style="text-align: right;">{row['move_name']}</td>
                        <td>{row['debit']:,.2f}</td>
                        <td>{row['credit']:,.2f}</td>
                        <td>{running_balance:,.2f}</td>
                    </tr>
            """
        html_content += f"""
                </tbody>
            </table>
            <div class="summary-box">
                <div>Total Debit: <strong>{cust_df['debit'].sum():,.2f}</strong></div>
                <div>Total Credit: <strong>{cust_df['credit'].sum():,.2f}</strong></div>
                <div style="font-size: 16px; border-top: 1px solid #000; margin-top: 5px;">
                    Net Balance: <strong>{cust_df['net'].sum():,.2f}</strong>
                </div>
            </div>
            <div class="clearfix"></div>
        </div>
        """
    html_content += "</body></html>"
    return HTML(string=html_content).write_pdf()

# --- Streamlit UI ---
df = load_data()

if not df.empty:
    tab1, tab2 = st.tabs(["📑 Detailed Ledgers", "⚖️ Trial Balance"])
    
    with tab1:
        st.title("Customer Reports (Odoo Style)")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            date_range = st.date_input("Select Period:", [df['date'].min(), df['date'].max()], key="d_range")
        with col2:
            all_partners = sorted(df['partner_id'].unique().tolist())
            selected_partners = st.multiselect("Select Partners to Export:", options=all_partners)
            if st.checkbox("Select All Partners"):
                selected_partners = all_partners

        if selected_partners:
            # Filter Data
            mask = (df['date'] >= pd.Timestamp(date_range[0])) & \
                   (df['date'] <= pd.Timestamp(date_range[1])) & \
                   (df['partner_id'].isin(selected_partners))
            filtered_df = df[mask].copy()

            # --- ركز هنا: إعادة إظهار الجداول على الشاشة للمراجعة ---
            st.divider()
            for partner in selected_partners:
                partner_data = filtered_df[filtered_df['partner_id'] == partner].sort_values('date')
                if not partner_data.empty:
                    with st.expander(f"Preview Ledger: {partner}", expanded=True):
                        # عرض إجماليات سريعة للعميل
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Debit", f"{partner_data['debit'].sum():,.2f}")
                        m2.metric("Credit", f"{partner_data['credit'].sum():,.2f}")
                        m3.metric("Net Balance", f"{partner_data['net'].sum():,.2f}")
                        
                        # عرض الجدول بالكامل
                        st.dataframe(partner_data[['date', 'move_name', 'debit', 'credit', 'net']], 
                                     use_container_width=True, hide_index=True)

            if st.button("🚀 Export All to PDF (Multi-page)"):
                with st.spinner("Generating PDF..."):
                    try:
                        pdf_data = generate_pdf_multi_page(filtered_df, selected_partners)
                        st.download_button("📥 Download PDF Report", pdf_data, "Customer_Statements.pdf")
                    except Exception as e:
                        st.error(f"Engine Error: {e}. Check packages.txt")

    with tab2:
        st.title("Annual Trial Balance")
        years = sorted(df['date'].dt.year.dropna().unique().astype(int).tolist(), reverse=True)
        sel_year = st.selectbox("Financial Year:", years)
        
        # Trial Balance Logic
        opening = df[df['date'].dt.year < sel_year].groupby('partner_id')['net'].sum().reset_index(name='Opening')
        period = df[df['date'].dt.year == sel_year].groupby('partner_id')['net'].sum().reset_index(name='Movement')
        tb = pd.merge(df[['partner_id']].drop_duplicates(), opening, on='partner_id', how='left')
        tb = pd.merge(tb, period, on='partner_id', how='left').fillna(0)
        tb['Ending Balance'] = tb['Opening'] + tb['Movement']
        
        st.dataframe(tb.sort_values('Ending Balance', ascending=False), use_container_width=True)
