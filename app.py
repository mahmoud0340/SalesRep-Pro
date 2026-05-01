# app.py
import streamlit as st
from database.db import init_db, get_user_by_username, hash_password
from modules import rep, admin

init_db()

st.set_page_config(page_title="SalesRep Pro", page_icon="🛢️", layout="wide", initial_sidebar_state="auto")

# ========== الهيدر باسم الشركة ==========
st.markdown("""
    <div style="text-align: center; padding: 1rem; background: linear-gradient(90deg, #E65100, #BF360C); border-radius: 10px; margin-bottom: 1rem;">
        <h1 style="color: white; margin: 0; font-family: 'Arial Black', sans-serif;">🛢️ HANZ & TEX LUBRICANTS 🛢️</h1>
        <p style="color: #FFCC80; margin: 0;">نظام إدارة المبيعات - بجودة عالية</p>
    </div>
""", unsafe_allow_html=True)

# ========== تحسينات PWA ==========
pwa_html = """
<link rel="manifest" href="manifest.json">
<meta name="theme-color" content="#E65100">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="SalesRep Pro">
<link rel="apple-touch-icon" href="icon-192.png">
"""
st.markdown(pwa_html, unsafe_allow_html=True)

# ========== CSS ==========
st.markdown("""
<style>
    :root {
        --primary-color: #E65100;
        --primary-dark: #BF360C;
        --bg-color: #F5F5F5;
        --card-bg: #FFFFFF;
        --text-color: #212121;
        --border-color: #E0E0E0;
        --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        --radius: 0.75rem;
    }
    .stApp {
        background-color: var(--bg-color);
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(135deg, #212121 0%, #424242 100%);
        border-radius: 0 2rem 2rem 0;
    }
    [data-testid="stSidebar"] .stMarkdown, 
    [data-testid="stSidebar"] .stText {
        color: white !important;
    }
    [data-testid="stSidebar"] .stButton button {
        background-color: #E65100;
        color: white;
        border: none;
    }
    [data-testid="stSidebar"] .stButton button:hover {
        background-color: #BF360C;
        transform: scale(1.02);
    }
    .stButton > button {
        background: linear-gradient(90deg, var(--primary-color) 0%, var(--primary-dark) 100%);
        color: white;
        border: none;
        border-radius: var(--radius);
        padding: 0.6rem 1.2rem;
        font-weight: 600;
        transition: all 0.1s ease;
        box-shadow: var(--shadow-md);
    }
    .stButton > button:active {
        transform: scale(0.97);
        box-shadow: 0 1px 2px rgba(0,0,0,0.2);
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }
    .stTextInput > div > input, .stTextArea > div > textarea, .stSelectbox > div {
        border-radius: var(--radius);
        border: 1px solid var(--border-color);
    }
    .stMetric {
        background: var(--card-bg);
        border-radius: var(--radius);
        padding: 1rem;
        box-shadow: var(--shadow-md);
        text-align: center;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
    }
    .stTabs [aria-selected="true"] {
        background-color: var(--primary-color);
        color: white;
        border-radius: var(--radius);
    }
    h1, h2, h3 {
        font-family: 'Arial', sans-serif;
        color: var(--text-color);
    }
    .custom-footer {
        text-align: center;
        margin-top: 2rem;
        padding: 1rem;
        border-top: 1px solid var(--border-color);
        color: #757575;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# ========== جلسة المستخدم ==========
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.role = None

# ========== شاشة تسجيل الدخول ==========
if not st.session_state.logged_in:
    st.title("🔐 تسجيل الدخول - SalesRep Pro")
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
else:
    with st.sidebar:
        st.header(f"👋 مرحباً، {st.session_state.username}")
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
    
    # تذييل
    st.markdown('<div class="custom-footer">🔧 نظام إدارة مبيعات HANZ & TEX | شركة مابكو للزيوت المعدنيه | جميع الحقوق محفوظة © 2026</div>', unsafe_allow_html=True)