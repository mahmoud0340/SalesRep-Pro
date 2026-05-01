import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# رابط الشيت الخاص بك
SHEET_URL = "https://docs.google.com/spreadsheets/d/1UD9Q1c4wl07nWbY6RwcrO5DASuDav97bGJHIZdNk10I/edit?usp=sharing"

def send_data_to_sheets(data_list):
    """
    وظيفة الدالة: استقبال قائمة (List) من الفواتير من لوحة الإدارة
    ورفعها دفعة واحدة إلى جوجل شيت.
    """
    try:
        if not data_list:
            return False
            
        # إنشاء الاتصال بمكتبة جوجل شيت
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # تحويل البيانات القادمة إلى DataFrame
        new_report_df = pd.DataFrame(data_list)
        
        # قراءة البيانات القديمة لعدم مسحها (Append)
        try:
            existing_data = conn.read(spreadsheet=SHEET_URL, worksheet="Sheet1")
            # تنظيف البيانات القديمة من أي أعمدة فارغة تماماً
            existing_data = existing_data.dropna(how='all', axis=1)
            updated_df = pd.concat([existing_data, new_report_df], ignore_index=True)
        except:
            # إذا كان الشيت فارغاً تماماً
            updated_df = new_report_df

        # رفع الجدول المحدث بالكامل إلى جوجل شيت
        conn.update(spreadsheet=SHEET_URL, worksheet="Sheet1", data=updated_df)
        return True
    except Exception as e:
        st.error(f"خطأ في الاتصال بجوجل شيت: {e}")
        return False