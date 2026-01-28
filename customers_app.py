import streamlit as st
import pandas as pd
from io import BytesIO

# Page Configuration
st.set_page_config(page_title="Ar Suhul - Customer Statements", layout="wide")

st.title("👥 Customer Account Statements - Ar Suhul")
st.markdown("---")

# -----------------------------
# Data Loading Function
# -----------------------------
@st.cache_data 
def load_ar_suhul():
    # URL to the CSV file on GitHub
    url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/ar_suhul.csv"
    df = pd.read_csv(url, encoding='utf-8')
    
    # Process dates to ensure correct sorting
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    return df.dropna(subset=["date"])

# -----------------------------
# PDF/Excel Generation Logic
# -----------------------------
def to_excel(df_to_download, sheet_name):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df_to_download.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue()

try:
    df_all = load_ar_suhul()

    # Sidebar: Bulk Selection
    st.sidebar.header("🔍 Selection & Printing")
    partners = sorted(df_all['partner_id'].unique().tolist())
    
    # Multiselect to allow choosing multiple clients for bulk printing
    selected_partners = st.sidebar.multiselect("Select Customers for Statements", options=partners)

    if selected_partners:
        st.info(f"Generating individual statements for {len(selected_partners)} customers...")

        for partner in selected_partners:
            # 1. Filter and sort for the current partner
            cust_df = df_all[df_all['partner_id'] == partner].sort_values(by='date')

            # 2. Calculate Running Balance
            cust_df['Running_Balance'] = (cust_df['debit'] - cust_df['credit']).cumsum()

            # 3. UI Section for each partner
            with st.expander(f"📄 Statement: {partner}", expanded=True):
                # Metrics for the specific partner
                current_bal = cust_df['Running_Balance'].iloc[-1]
                st.metric(label="Current Balance", value=f"{current_bal:,.2f} EGP")
                
                # Table Preview
                display_df = cust_df[['date', 'move_name', 'debit', 'credit', 'Running_Balance']]
                st.dataframe(display_df, use_container_width=True, hide_index=True)

                # 4. Individual Download Button (The core requirement)
                # This ensures each client gets their own separate file
                excel_data = to_excel(display_df, sheet_name="Statement")
                st.download_button(
                    label=f"⬇️ Download {partner} Statement",
                    data=excel_data,
                    file_name=f"Statement_{partner}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"btn_{partner}" # Unique key for each button
                )
    else:
        st.warning("Please select one or more customers from the sidebar to view and download statements.")

except Exception as e:
    st.error(f"Error loading data: {e}")
