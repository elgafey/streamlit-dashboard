import streamlit as st
import pandas as pd
from fpdf import FPDF
import re

# ... (Load data function remains the same)

def clean_text(text):
    """Removes non-ASCII characters (like Arabic) to prevent PDF crashes"""
    if not text or pd.isna(text):
        return ""
    # This regex keeps only English letters, numbers, and basic punctuation
    return re.sub(r'[^\x00-\x7F]+', '?', str(text))

def generate_pdf(df_all, selected_partners):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    for partner in selected_partners:
        cust_df = df_all[df_all['partner_id'] == partner].sort_values(by='date')
        cust_df['Running_Balance'] = (cust_df['debit'] - cust_df['credit']).cumsum()
        
        pdf.add_page()
        
        # Header - Cleaning the partner name just in case
        pdf.set_font("Helvetica", 'B', 16)
        pdf.cell(0, 10, f"Statement: {clean_text(partner)}", ln=True, align='C')
        pdf.ln(10)
        
        # Table Header
        pdf.set_font("Helvetica", 'B', 10)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(35, 10, "Date", 1, 0, 'C', True)
        pdf.cell(65, 10, "Movement", 1, 0, 'C', True)
        pdf.cell(30, 10, "Debit", 1, 0, 'C', True)
        pdf.cell(30, 10, "Credit", 1, 0, 'C', True)
        pdf.cell(30, 10, "Balance", 1, 1, 'C', True)
        
        # Table Body
        pdf.set_font("Helvetica", '', 9)
        for _, row in cust_df.iterrows():
            pdf.cell(35, 8, str(row['date']), 1)
            # Cleaning the movement name to remove Arabic "م" or other characters
            pdf.cell(65, 8, clean_text(row['move_name'])[:35], 1) 
            pdf.cell(30, 8, f"{row['debit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['credit']:,.2f}", 1, 0, 'R')
            pdf.cell(30, 8, f"{row['Running_Balance']:,.2f}", 1, 1, 'R')

    return pdf.output()
