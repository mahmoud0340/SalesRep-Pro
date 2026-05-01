# services/google_sheets_service.py
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

def upload_report_to_google_sheets(report_data, sheet_name="التقارير"):
    """
    رفع التقرير إلى Google Sheets (استبدال البيانات القديمة)
    """
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = pd.DataFrame(report_data)
        df['تاريخ_الرفع'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.write(dataframe=df, sheet_name=sheet_name)
        return True, "تم رفع التقرير بنجاح إلى Google Sheets"
    except Exception as e:
        return False, f"خطأ في الرفع: {str(e)}"

def append_report_to_google_sheets(report_data, sheet_name="التقارير"):
    """
    إضافة التقرير إلى Google Sheets (إلحاق بأسفل البيانات الموجودة)
    """
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = pd.DataFrame(report_data)
        df['تاريخ_الرفع'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        existing_df = conn.read(sheet_name=sheet_name)
        if existing_df is not None and not existing_df.empty:
            updated_df = pd.concat([existing_df, df], ignore_index=True)
        else:
            updated_df = df
            
        conn.write(dataframe=updated_df, sheet_name=sheet_name)
        return True, "تم إضافة التقرير بنجاح إلى Google Sheets"
    except Exception as e:
        return False, f"خطأ في الإلحاق: {str(e)}"

def get_google_sheet_data(sheet_name="التقارير"):
    """قراءة البيانات من Google Sheets"""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(sheet_name=sheet_name)
        return df
    except Exception as e:
        st.error(f"خطأ في القراءة: {e}")
        return None

def test_connection():
    """دالة اختبار للتحقق من صحة الاتصال بـ Google Sheets"""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        test_df = pd.DataFrame({'نتيجة_الاختبار': ['اتصال ناجح']})
        conn.write(dataframe=test_df, sheet_name="اختبار_الاتصال")
        return True, "تم الاتصال بنجاح وتم إنشاء ورقة 'اختبار_الاتصال' في Google Sheet الخاص بك"
    except Exception as e:
        return False, f"فشل الاتصال: {str(e)}"