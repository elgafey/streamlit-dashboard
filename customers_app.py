import streamlit as st
import pandas as pd
from weasyprint import HTML
import io

# 1. إعدادات الصفحة
st.set_page_config(page_title="Suhul Albeeah | Odoo Reporting", layout="wide")

@st.cache_data 
def load_data():
    try:
        url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/ar_suhul.csv"
        df = pd.read_csv(url)
        df['date'] = pd.to_datetime(df['date'].str.split(' GMT').str[0], errors='coerce')
        # فلترة الحسابات لمطابقة أرقام أودو
        target_accounts = [1209001, 1209002, 1211000, 1213000]
        df = df[df['account_code'].isin(target_accounts)]
        df["debit"] = pd.to_numeric(df["debit"], errors="coerce").fillna(0)
        df["credit"] = pd.to_numeric(df["credit"], errors="coerce").fillna(0)
        df["net"] = df["debit"] - df["credit"]
        df['partner_id'] = df['partner_id'].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

def generate_odoo_style_pdf(df_filtered, partner_name):
    """توليد PDF باستخدام HTML/CSS لدعم كامل للعربي (مثل أودو)"""
    
    # تصميم الجدول والتقرير
    html_content = f"""
    <html dir="rtl" lang="ar">
    <head>
        <meta charset="utf-8">
        <style>
            @page {{ size: A4; margin: 1cm; }}
            body {{ font-family: 'Arial', sans-serif; direction: rtl; color: #333; }}
            .header {{ border-bottom: 2px solid #1a237e; margin-bottom: 20px; padding-bottom: 10px; }}
            .company-name {{ color: #1a237e; font-size: 24px; font-weight: bold; }}
            .report-title {{ text-align: center; font-size: 20px; margin: 20px 0; background: #f5f5f5; padding: 10px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 12px; }}
            th {{ background-color: #1a237e; color: white; padding: 10px; border: 1px solid #ddd; }}
            td {{ padding: 8px; border: 1px solid #ddd; text-align: center; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            .summary-box {{ margin-top: 20px; border: 1px solid #1a237e; width: 300px; float: left; padding: 10px; }}
            .footer {{ position: fixed; bottom: 0; width: 100%; text-align: center; font-size: 10px; color: #777; }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="company-name">شركة سهول البيئة لتدوير المواد الأولية</div>
            <div>الرقم الضريبي: 300451393600003</div>
        </div>

        <div class="report-title">كشف حساب شريك (Partner Ledger)</div>
        
        <div style="margin-bottom: 20px;">
            <strong>اسم العميل:</strong> {partner_name}<br>
            <strong>تاريخ التقرير:</strong> {pd.Timestamp.now().strftime('%Y-%m-%d')}
        </div>

        <table>
            <thead>
                <tr>
                    <th>التاريخ</th>
                    <th>البيان (Move Name)</th>
                    <th>مدين</th>
                    <th>دائن</th>
                    <th>الرصيد الجاري</th>
                </tr>
            </thead>
            <tbody>
    """
    
    running_balance = 0
    for _, row in df_filtered.sort_values('date').iterrows():
        running_balance += row['net']
        html_content += f"""
                <tr>
                    <td>{row['date'].strftime('%Y-%m-%d')}</td>
                    <td style="text-align: right;">{row['move_name']}</td>
                    <td>{row['debit']:,.2f}</td>
                    <td>{row['credit']:,.2f}</td>
                    <td style="font-weight: bold;">{running_balance:,.2f}</td>
                </tr>
        """
    
    html_content += f"""
            </tbody>
        </table>

        <div class="summary-box">
            <div style="display: flex; justify-content: space-between;">
                <span>إجمالي المدين:</span> <strong>{df_filtered['debit'].sum():,.2f}</strong>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span>إجمالي الدائن:</span> <strong>{df_filtered['credit'].sum():,.2f}</strong>
            </div>
            <hr>
            <div style="display: flex; justify-content: space-between; font-size: 16px;">
                <span>الرصيد النهائي:</span> <strong>{df_filtered['net'].sum():,.2f}</strong>
            </div>
        </div>

        <div class="footer">
            تم استخراج هذا التقرير من النظام المالي لشركة سهول البيئة
        </div>
    </body>
    </html>
    """
    
    # تحويل الـ HTML إلى PDF
    return HTML(string=html_content).write_pdf()

# --- واجهة Streamlit ---
df = load_data()

if not df.empty:
    tab1, tab2 = st.tabs(["📑 كشوف الحسابات", "⚖️ ميزان المراجعة"])
    
    with tab1:
        st.markdown("### 📝 استخراج كشف حساب (Odoo Style)")
        
        c1, c2 = st.columns([1, 2])
        with c1:
            # فلتر تاريخ مستقل
            d_range = st.date_input("اختر الفترة:", [df['date'].min(), df['date'].max()], key="ledger_date")
        with c2:
            all_partners = sorted(df['partner_id'].unique().tolist())
            selected = st.multiselect("اختر الشركاء:", options=all_partners)
            
        if selected:
            # فلترة البيانات
            mask = (df['date'] >= pd.Timestamp(d_range[0])) & \
                   (df['date'] <= pd.Timestamp(d_range[1])) & \
                   (df['partner_id'].isin(selected))
            filtered_df = df[mask].copy()

            # عرض ملخص سريع
            m1, m2, m3 = st.columns(3)
            m1.metric("إجمالي مدين", f"{filtered_df['debit'].sum():,.2f}")
            m2.metric("إجمالي دائن", f"{filtered_df['credit'].sum():,.2f}")
            m3.metric("صافي الرصيد", f"{filtered_df['net'].sum():,.2f}")

            if st.button("🚀 طباعة التقرير الاحترافي (PDF)"):
                with st.spinner("جاري إنشاء التقرير بأسلوب أودو..."):
                    try:
                        # سنطبع التقرير لأول عميل مختار كمثال أو ندمجهم
                        pdf_bytes = generate_odoo_style_pdf(filtered_df, ", ".join(selected))
                        st.download_button(
                            label="📥 تحميل ملف PDF",
                            data=pdf_bytes,
                            file_name=f"Suhul_Ledger_{d_range[0]}.pdf",
                            mime="application/pdf"
                        )
                    except Exception as e:
                        st.error(f"خطأ في المحرك: {e}")
                        st.info("تأكد من وجود ملف packages.txt في GitHub وتثبيت WeasyPrint")

    with tab2:
        st.markdown("### ⚖️ ميزان المراجعة السنوي")
        years = sorted(df['date'].dt.year.dropna().unique().astype(int).tolist(), reverse=True)
        sel_year = st.selectbox("اختر السنة المالية:", years, key="tb_year")
        
        # حساب ميزان المراجعة
        init = df[df['date'].dt.year < sel_year].groupby('partner_id')['net'].sum().reset_index(name='افتتاحي')
        peri = df[df['date'].dt.year == sel_year].groupby('partner_id')['net'].sum().reset_index(name='حركة الفترة')
        tb = pd.merge(df[['partner_id']].drop_duplicates(), init, on='partner_id', how='left')
        tb = pd.merge(tb, peri, on='partner_id', how='left').fillna(0)
        tb['الرصيد الختامي'] = tb['افتتاحي'] + tb['حركة الفترة']
        
        st.dataframe(tb.sort_values('الرصيد الختامي', ascending=False).style.format("{:,.2f}", subset=['افتتاحي', 'حركة الفترة', 'الرصيد الختامي']), 
                     use_container_width=True)
else:
    st.error("لم يتم تحميل أي بيانات، يرجى التحقق من المصدر.")
