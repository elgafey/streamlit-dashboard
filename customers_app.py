import streamlit as st
import pandas as pd
from weasyprint import HTML
import io

# 1. Page Configuration
st.set_page_config(page_title="Suhul Albeeah | Secure Portal", layout="wide")

# --- Multi-User Authentication Logic ---
def check_password():
    """Returns True if the user had the correct password and sets their role."""
    
    # تعريف المستخدمين وصلاحياتهم
    USERS = {
        "admin": {"password": "admin2026", "role": "Administrator"},
        "accountant": {"password": "user2026", "role": "User"}
    }

    def password_entered():
        user = st.session_state["username"].lower()
        pwd = st.session_state["password"]
        if user in USERS and USERS[user]["password"] == pwd:
            st.session_state["password_correct"] = True
            st.session_state["user_role"] = USERS[user]["role"]
            st.session_state["display_name"] = user.capitalize()
            del st.session_state["password"] 
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("Suhul Albeeah Financial Portal")
        st.subheader("Login to access the system")
        st.text_input("Username", on_change=password_entered, key="username")
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.title("Suhul Albeeah Financial Portal")
        st.text_input("Username", on_change=password_entered, key="username")
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        st.error("❌ Invalid username or password")
        return False
    else:
        return True

@st.cache_data 
def load_data():
    try:
        url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/ar_suhul.csv"
        df = pd.read_csv(url)
        df['date'] = pd.to_datetime(df['date'].str.split(' GMT').str[0], errors='coerce')
        # Filter for Odoo consistency
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
    """Odoo-style PDF engine."""
    html_content = """<html dir="rtl" lang="ar"><head><meta charset="utf-8"><style>
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
    .clearfix { clear: both; }</style></head><body>"""
    
    for partner in selected_partners:
        cust_df = df_filtered[df_filtered['partner_id'] == partner].sort_values('date')
        if cust_df.empty: continue
        rb = 0
        html_content += f"""<div class="page-container"><div class="header"><div class="company-name">Suhul Albeeah Co.</div></div>
        <div class="report-title">Partner Ledger</div><p>Partner: {partner}</p><table><thead><tr>
        <th>Date</th><th>Description</th><th>Debit</th><th>Credit</th><th>Balance</th></tr></thead><tbody>"""
        for _, row in cust_df.iterrows():
            rb += row['net']
            html_content += f"<tr><td>{row['date'].strftime('%Y-%m-%d')}</td><td>{row['move_name']}</td><td>{row['debit']:,.2f}</td><td>{row['credit']:,.2f}</td><td>{rb:,.2f}</td></tr>"
        html_content += f"</tbody></table><div class='summary-box'>Final Balance: <strong>{rb:,.2f}</strong></div><div class='clearfix'></div></div>"
    
    html_content += "</body></html>"
    return HTML(string=html_content).write_pdf()

# --- Main Application Logic ---
if check_password():
    # Sidebar Info
    st.sidebar.title(f"Welcome, {st.session_state['display_name']}")
    st.sidebar.info(f"Role: {st.session_state['user_role']}")
    if st.sidebar.button("Log Out"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

    df = load_data()
    if not df.empty:
        tab1, tab2 = st.tabs(["📑 Detailed Ledgers", "⚖️ Trial Balance"])
        
        with tab1:
            st.title("Customer Statements")
            c1, c2 = st.columns([1, 2])
            with c1:
                date_range = st.date_input("Period:", [df['date'].min(), df['date'].max()], key="dr_main")
            with c2:
                partners = sorted(df['partner_id'].unique().tolist())
                selected = st.multiselect("Select Partners:", options=partners)

            if selected:
                mask = (df['date'] >= pd.Timestamp(date_range[0])) & (df['date'] <= pd.Timestamp(date_range[1])) & (df['partner_id'].isin(selected))
                filtered_df = df[mask].copy()

                for p in selected:
                    p_data = filtered_df[filtered_df['partner_id'] == p].sort_values('date').copy()
                    if not p_data.empty:
                        p_data['Running Balance'] = p_data['net'].cumsum() #
                        with st.expander(f"Ledger: {p}", expanded=True):
                            st.dataframe(p_data[['date', 'move_name', 'debit', 'credit', 'Running Balance']], use_container_width=True, hide_index=True)

                # صلاحية الطباعة للأدمن فقط
                if st.session_state["user_role"] == "Administrator":
                    if st.button("Generate PDF Report"):
                        with st.spinner("Processing..."):
                            pdf_bytes = generate_pdf_multi_page(filtered_df, selected)
                            st.download_button("📥 Download PDF", pdf_bytes, "Reports.pdf")
                else:
                    st.warning("⚠️ Export to PDF is restricted to Administrators only.")

        with tab2:
            st.title("Trial Balance")
            years = sorted(df['date'].dt.year.dropna().unique().astype(int).tolist(), reverse=True)
            sel_year = st.selectbox("Year:", years)
            
            movement = df[df['date'].dt.year == sel_year].groupby('partner_id')['net'].sum().reset_index(name='Movement')
            st.dataframe(movement.sort_values('Movement', ascending=False), use_container_width=True)
