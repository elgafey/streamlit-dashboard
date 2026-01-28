def generate_pdf(df_all, selected_partners):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    for partner in selected_partners:
        cust_df = df_all[df_all['partner_id'] == partner].copy().sort_values(by='date')
        if cust_df.empty: continue
        
        cust_df['Running_Balance'] = (cust_df['debit'] - cust_df['credit']).cumsum()
        pdf.add_page()
        
        # --- الهيدر الاحترافي (Header) ---
        pdf.set_font("Helvetica", 'B', 12)
        pdf.cell(0, 6, "شركة سهول البيئة لتدوير المواد الأولية", ln=True, align='L')
        pdf.set_font("Helvetica", '', 9)
        pdf.cell(0, 5, "الدائري الشرقي الفرعي - حي الريان", ln=True, align='L')
        pdf.cell(0, 5, "Riyadh RUH 14213, Saudi Arabia", ln=True, align='L')
        pdf.cell(0, 5, "VAT Number: 300451393600003", ln=True, align='L')
        
        # عنوان كشف الحساب
        pdf.ln(5)
        pdf.set_font("Helvetica", 'B', 16)
        pdf.cell(0, 10, "PARTNER LEDGER", ln=True, align='C')
        pdf.set_font("Helvetica", 'B', 12)
        pdf.cell(0, 10, f"Customer: {clean_text(partner)}", ln=True, align='L')
        
        # الرصيد النهائي في الهيدر
        final_bal = cust_df['Running_Balance'].iloc[-1]
        pdf.cell(0, 8, f"Final Balance: {final_bal:,.2f} EGP", ln=True, align='L')
        pdf.ln(5)
        
        # --- جدول البيانات ---
        pdf.set_font("Helvetica", 'B', 10); pdf.set_fill_color(240, 240, 240)
        cols = [("Date", 30), ("Move Name", 70), ("Debit", 30), ("Credit", 30), ("Balance", 30)]
        for h, w in cols:
            pdf.cell(w, 10, h, 1, 0, 'C', True)
        pdf.ln()
        
        pdf.set_font("Helvetica", '', 9)
        for _, row in cust_df.iterrows():
            pdf.cell(30, 8, row['date'].strftime('%Y-%m-%d'), 1)
            pdf.cell(70, 8, clean_text(row['move_name'])[:40], 1)
            pdf.cell(30, 8, f"{row['debit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['credit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['Running_Balance']:,.2f}", 1, 1, 'R')
            
    return bytes(pdf.output(dest='S'))
