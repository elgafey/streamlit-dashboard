import streamlit as st
import pandas as pd

# إعدادات الصفحة
st.set_page_config(page_title="Ar Suhul - Customer Balances", layout="wide")

st.title("👥 كشوف حسابات عملاء السهول")
st.markdown("---")

# -----------------------------
# دالة تحميل البيانات
# -----------------------------
@st.cache_data 
def load_ar_suhul():
    # الرابط الخاص بجدول ارصدة السهول
    url = "https://raw.githubusercontent.com/elgafey/sql-data/refs/heads/main/ar_suhul.csv"
    df = pd.read_csv(url, encoding='utf-8')
    
    # تحويل التاريخ والتأكد من جودته
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    return df.dropna(subset=["date"])

try:
    df_all = load_ar_suhul()

    # -----------------------------
    # الفلاتر الجانبية
    # -----------------------------
    st.sidebar.header("🔍 خيارات العرض")
    
    # استخراج قائمة العملاء الفريدة
    partners = sorted(df_all['partner_id'].unique().tolist())
    selected_partner = st.sidebar.selectbox("اختر العميل", options=[""] + partners)

    if selected_partner:
        # 1. تصفية البيانات للعميل المحدد وترتيبها بالأقدم
        cust_df = df_all[df_all['partner_id'] == selected_partner].sort_values(by='date')

        # ------------------------------------------------
        # 2. حساب الرصيد التراكمي (المجمع) - منطق البايثون
        # ------------------------------------------------
        # نقوم بجمع (المدين - الدائن) لكل سطر مضافاً إليه السطور السابقة
        cust_df['Running_Balance'] = (cust_df['debit'] - cust_df['credit']).cumsum()

        # 3. عرض إجمالي المديونية الحالية كبطاقة قياس
        current_bal = cust_df['Running_Balance'].iloc[-1]
        st.metric(label=f"إجمالي رصيد {selected_partner}", value=f"{current_bal:,.2f} EGP")

        st.divider()

        # 4. تنسيق الجدول للعرض المحاسبي
        # ترتيب الأعمدة وتغيير أسمائها لتكون واضحة للمستخدم
        display_df = cust_df[['date', 'move_name', 'debit', 'credit', 'Running_Balance']].copy()
        display_df.columns = ['التاريخ', 'رقم الحركة', 'مدين (عليه)', 'دائن (له)', 'الرصيد المجمع']

        # 5. عرض الجدول مع تمييز الأرقام
        st.subheader(f"تفاصيل حركة حساب: {selected_partner}")
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        # 6. زر التحميل بصيغة CSV تدعم العربية
        csv_file = display_df.to_csv(index=False).encode('utf-8-sig')
        st.sidebar.download_button(
            label="⬇️ تحميل كشف الحساب",
            data=csv_file,
            file_name=f"Statement_{selected_partner}.csv",
            mime="text/csv"
        )
    else:
        st.info("💡 يرجى اختيار اسم العميل من القائمة الجانبية لعرض كشف الحساب المفصل.")

except Exception as e:
    st.error(f"❌ حدث خطأ أثناء تحميل البيانات: {e}")
    st.info("تأكد من تحديث ملف ar_suhul.csv على GitHub.")
