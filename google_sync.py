import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# الرابط الخاص بك
SHEET_URL = "https://docs.google.com/spreadsheets/d/1UD9Q1c4wl07nWbY6RwcrO5DASuDav97bGJHIZdNk10I/edit?usp=sharing"

def send_data_to_sheets(new_row_dict):
    try:
        # الاتصال بجوجل شيت
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # قراءة البيانات الحالية (نحدد اسم الورقة Sheet1 لضمان الدقة)
        try:
            existing_data = conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1")
        except:
            existing_data = pd.DataFrame()
        
        # تحويل الصف الجديد لـ DataFrame
        new_df = pd.DataFrame([new_row_dict])
        
        # دمج الصف الجديد مع القديم
        if not existing_data.empty:
            updated_df = pd.concat([existing_data, new_df], ignore_index=True)
        else:
            updated_df = new_df
            
        # تحديث الملف بالكامل
        conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=updated_df)
        return True
    except Exception as e:
        # طباعة الخطأ في الكونسول لتشخيصه
        print(f"DEBUG: Google Sheets Error -> {e}")
        return False