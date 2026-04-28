# app.py - نسخة عمل سابقة (بدون HANZ)
import streamlit as st
from database.db import init_db, get_user_by_username, hash_password
from modules import rep, admin

init_db()

st.set_page_config(page_title="SalesRep Pro", page_icon="📱", layout="wide", initial_sidebar_state="auto")

pwa_html = """
<link rel="manifest" href="manifest.json">
<meta name="theme-color" content="#1E88E5">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="SalesRep Pro">
<link rel="apple-touch-icon" href="icon-192.png">
"""
st.markdown(pwa_html, unsafe_allow_html=True)

# CSS الجذاب (بدون خلفية HANZ)
st.markdown("""
<style>
    :root {
        --primary-color: #4F46E5;
        --primary-dark: #4338CA;
        --bg-color: #F9FAFB;
        --card-bg: #FFFFFF;
        --text-color: #1F2937;
        --border-color: #E5E7EB;
        --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        --radius: 0.75rem;
    }
    .stApp { background-color: var(--bg-color); }
    [data-testid="stSidebar"] { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 0 2rem 2rem 0; }
    .stButton > button { background: linear-gradient(90deg, var(--primary-color) 0%, var(--primary-dark) 100%); color: white; border-radius: var(--radius); }
    .stButton > button:hover { transform: translateY(-2px); }
    .stMetric { background: var(--card-bg); border-radius: var(--radius); padding: 1rem; box-shadow: var(--shadow-md); }
    .dataframe th { background-color: var(--primary-color) !important; color: white !important; }
    .stTabs [aria-selected="true"] { background-color: var(--primary-color); color: white; }
                h1 { background: linear-gradient(120deg, var(--primary-color), var(--primary-dark)); background-clip: text; -webkit-background-clip: text; color: transparent; }
/* خلفية HANZ المائية */
.stApp::before {
    content: "HANZ";
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    font-size: 8rem;
    font-weight: bold;
    color: rgba(0, 0, 0, 0.03);
    display: flex;
    align-items: center;
    justify-content: center;
    pointer-events: none;
    z-index: 0;
    font-family: Arial, sans-serif;
    transform: rotate(-15deg);
}           
            </style>
""", unsafe_allow_html=True)

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.role = None

if not st.session_state.logged_in:
    st.title("📱 تسجيل الدخول - SalesRep Pro")
    with st.form("login_form"):
        username = st.text_input("اسم المستخدم")
        password = st.text_input("كلمة المرور", type="password")
        submit = st.form_submit_button("دخول")
        if submit:
            user = get_user_by_username(username)
            if user and user['password'] == hash_password(password) and user['is_active']:
                st.session_state.logged_in = True
                st.session_state.user_id = user['id']
                st.session_state.username = user['username']
                st.session_state.role = user['role']
                st.rerun()
            else:
                st.error("اسم المستخدم أو كلمة المرور غير صحيحة أو الحساب غير نشط")
    st.info("المدير الافتراضي: username = admin, password = admin123")
else:
    with st.sidebar:
        st.header(f"👋 مرحباً أحمد راشد، {st.session_state.username}")
        st.write(f"🔑 الدور: {st.session_state.role}")
        if st.button("🚪 تسجيل الخروج"):
            for key in ['logged_in', 'user_id', 'username', 'role', 'selected_client_for_invoice', 'edit_client_id', 'clients_page']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    
    if st.session_state.role == "Rep":
        rep.show_rep_dashboard(st.session_state.user_id)
    elif st.session_state.role == "Admin":
        admin.show_admin_dashboard()