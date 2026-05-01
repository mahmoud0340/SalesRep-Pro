# services/google_sheets_service.py
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

def upload_report_to_google_sheets(report_data, sheet_name="التقارير"):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = pd.DataFrame(report_data)
        df['تاريخ_الرفع'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.update(data=df, worksheet=sheet_name)
        return True, "تم رفع التقرير بنجاح إلى Google Sheets (استبدال البيانات القديمة)"
    except Exception as e:
        return False, f"خطأ في الرفع: {str(e)}"

def append_report_to_google_sheets(report_data, sheet_name="التقارير"):
    """
    رفع التقرير إلى Google Sheets مع استبدال البيانات القديمة بالكامل (بدون تكرار)
    """
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = pd.DataFrame(report_data)
        df['تاريخ_الرفع'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # كتابة البيانات مباشرة (استبدال الورقة القديمة بالكامل)
        conn.update(data=df, worksheet=sheet_name)
        return True, "تم رفع التقرير بنجاح إلى Google Sheets (تم استبدال البيانات القديمة)"
    except Exception as e:
        return False, f"خطأ في الرفع: {str(e)}"

def get_google_sheet_data(sheet_name="التقارير"):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet=sheet_name)
        return df
    except Exception as e:
        st.error(f"خطأ في القراءة: {e}")
        return None