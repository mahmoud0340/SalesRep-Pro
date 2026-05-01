import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# رابط ملفك الخاص الذي أرسلته
SHEET_URL = "https://docs.google.com/spreadsheets/d/1UD9Q1c4wl07nWbY6RwcrO5DASuDav97bGJHIZdNk10I/edit?usp=sharing"

def send_data_to_sheets(new_row_dict):
    try:
        # إنشاء اتصال مع جوجل شيت باستخدام الأسرار الموجودة في secrets.toml
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # قراءة البيانات الحالية (للتأكد من الإضافة في سطر جديد)
        try:
            existing_data = conn.read(spreadsheet=SHEET_URL)
        except:
            # إذا كان الشيت فارغاً تماماً
            existing_data = pd.DataFrame()
        
        # تحويل البيانات الجديدة إلى DataFrame
        new_df = pd.DataFrame([new_row_dict])
        
        # دمج البيانات
        updated_df = pd.concat([existing_data, new_df], ignore_index=True)
        
        # رفع التحديث
        conn.update(spreadsheet=SHEET_URL, data=updated_df)
        return True
    except Exception as e:
        st.error(f"خطأ في المزامنة: {e}")
        return False