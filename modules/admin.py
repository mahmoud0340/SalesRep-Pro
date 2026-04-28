# modules/admin.py
import streamlit as st
from services import client_service, invoice_service
import database.db as db
from datetime import datetime, timedelta

def show_admin_dashboard():
    st.title("لوحة تحكم المدير")
    
    tab1, tab2, tab3, tab4 = st.tabs(["المستخدمين", "العملاء", "تقارير الأداء", "تصدير التقارير (CSV)"])
    
    with tab1:
        st.subheader("إدارة المستخدمين")
        users = db.get_all_users()
        if users:
            user_data = []
            for u in users:
                user_data.append({
                    "ID": u['id'],
                    "اسم المستخدم": u['username'],
                    "الدور": u['role'],
                    "نشط": "نعم" if u['is_active'] else "لا"
                })
            st.dataframe(user_data, use_container_width=True)
        else:
            st.write("لا يوجد مستخدمون.")
        
        st.divider()
        
        with st.expander("➕ إضافة مستخدم جديد"):
            with st.form("new_user_form"):
                new_user = st.text_input("اسم المستخدم")
                new_pass = st.text_input("كلمة المرور", type="password")
                new_role = st.selectbox("الدور", ["Rep", "Admin"])
                submit_user = st.form_submit_button("إضافة")
                if submit_user:
                    if new_user and new_pass:
                        success, msg = db.create_user(new_user, new_pass, new_role)
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.error("يرجى ملء جميع الحقول")
        
        with st.expander("✏️ تعديل مستخدم"):
            user_options = {f"{u['username']} (ID: {u['id']})": u['id'] for u in users}
            selected_user_label = st.selectbox("اختر مستخدم", list(user_options.keys()))
            if selected_user_label:
                user_id = user_options[selected_user_label]
                selected_user = next(u for u in users if u['id'] == user_id)
                new_pass = st.text_input("كلمة المرور الجديدة (اترك فارغاً إذا لا تريد التغيير)", type="password")
                is_active = st.checkbox("نشط", value=selected_user['is_active'])
                if st.button("تحديث"):
                    if new_pass:
                        success, msg = db.update_user_password(user_id, new_pass)
                        if not success:
                            st.error(msg)
                        else:
                            st.success(msg)
                    db.update_user_activation(user_id, 1 if is_active else 0)
                    st.rerun()
                
                # نقل العملاء قبل الحذف (إذا كان المستخدم مندوباً وله عملاء)
                if selected_user['role'] == 'Rep':
                    with db.get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT COUNT(*) FROM Clients WHERE Assigned_Rep = ?", (user_id,))
                        count = cursor.fetchone()[0]
                    if count > 0:
                        st.warning(f"هذا المندوب مسؤول عن {count} عميل/عملاء. إذا أردت حذفه، يجب نقل العملاء أولاً.")
                        # قائمة المندوبين الآخرين
                        reps = [r for r in users if r['role'] == 'Rep' and r['id'] != user_id and r['is_active']]
                        if reps:
                            new_rep_options = {f"{r['username']} (ID: {r['id']})": r['id'] for r in reps}
                            selected_new_rep = st.selectbox("نقل العملاء إلى مندوب آخر", list(new_rep_options.keys()))
                            if st.button("نقل العملاء ثم حذف هذا المندوب"):
                                new_rep_id = new_rep_options[selected_new_rep]
                                client_service.transfer_clients(user_id, new_rep_id)
                                success, msg = db.delete_user(user_id, st.session_state['user_id'])
                                if success:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)
                        else:
                            st.info("لا يوجد مندوب آخر نشط لنقل العملاء إليه. قم بتفعيل مندوب آخر أولاً.")
                
                if st.button("حذف المستخدم (بدون عملاء)", key="del_user"):
                    success, msg = db.delete_user(user_id, st.session_state['user_id'])
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
    
    with tab2:
        st.subheader("جميع العملاء")
        # Pagination
        page_size = 20
        total_clients = client_service.get_total_clients_count()
        total_pages = (total_clients + page_size - 1) // page_size if total_clients > 0 else 1
        if 'clients_page' not in st.session_state:
            st.session_state.clients_page = 1
        
        col1, col2 = st.columns([1, 3])
        with col1:
            page = st.number_input("الصفحة", min_value=1, max_value=total_pages, value=st.session_state.clients_page, step=1)
            if page != st.session_state.clients_page:
                st.session_state.clients_page = page
                st.rerun()
        with col2:
            st.write(f"إجمالي العملاء: {total_clients} | الصفحة {page} من {total_pages}")
        
        offset = (page - 1) * page_size
        clients = client_service.get_all_clients(limit=page_size, offset=offset)
        if clients:
            for cl in clients:
                with st.expander(f"{cl['name']} (كود: {cl['code']}) - المندوب: {cl['rep_name']}"):
                    st.write(f"**الهاتف:** {cl['phone'] or 'لا يوجد'}")
                    st.write(f"**العنوان:** {cl['address']}")
                    if st.button(f"تعديل العميل {cl['id']}", key=f"edit_{cl['id']}"):
                        st.session_state['edit_client_id'] = cl['id']
                        st.rerun()
        else:
            st.info("لا يوجد عملاء.")
        
        if 'edit_client_id' in st.session_state:
            client_id = st.session_state['edit_client_id']
            client = client_service.get_client_by_id(client_id)
            if client:
                st.subheader(f"تعديل بيانات العميل {client['name']}")
                users = db.get_all_users()
                reps = [u for u in users if u['role'] == 'Rep' and u['is_active']]
                rep_dict = {f"{r['username']} (ID: {r['id']})": r['id'] for r in reps}
                with st.form("edit_client_form"):
                    new_name = st.text_input("الاسم", value=client['name'])
                    new_phone = st.text_input("الهاتف", value=client['phone'] or "")
                    new_address = st.text_area("العنوان", value=client['address'])
                    current_rep = next((f"{r['username']} (ID: {r['id']})" for r in reps if r['id'] == client['rep_id']), list(rep_dict.keys())[0] if rep_dict else "")
                    new_rep = st.selectbox("المندوب", list(rep_dict.keys()), index=list(rep_dict.keys()).index(current_rep) if current_rep in rep_dict else 0)
                    submitted = st.form_submit_button("حفظ التعديلات")
                    if submitted:
                        rep_id = rep_dict[new_rep]
                        client_service.update_client(client_id, new_name, new_phone, new_address, rep_id)
                        st.success("تم التحديث")
                        del st.session_state['edit_client_id']
                        st.rerun()
                if st.button("إلغاء التعديل"):
                    del st.session_state['edit_client_id']
                    st.rerun()
    
    with tab3:
        st.subheader("أداء المندوبين")
        performance = invoice_service.get_all_reps_performance()
        if performance:
            for rep in performance:
                with st.container():
                    st.markdown(f"### {rep['username']}")
                    col1, col2 = st.columns(2)
                    col1.metric("إجمالي المبيعات", f"{rep['total_sales']:.2f} ج.م")
                    col2.metric("إجمالي الكميات المباعة", f"{rep['total_qty']} قطعة")
                    st.divider()
        else:
            st.info("لا توجد بيانات للمندوبين بعد.")
    
    with tab4:
        st.subheader("تصدير التقارير (CSV)")
        rep_options = {"كل المندوبين": None}
        users = db.get_all_users()
        reps = [u for u in users if u['role'] == 'Rep']
        for r in reps:
            rep_options[r['username']] = r['id']
        selected_rep = st.selectbox("اختر المندوب", list(rep_options.keys()))
        rep_id = rep_options[selected_rep]
        
        report_type = st.radio("نوع التقرير", ["أسبوعي (آخر 7 أيام)", "شهري (آخر 30 يوماً)", "فترة مخصصة"])
        if report_type == "أسبوعي (آخر 7 أيام)":
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
        elif report_type == "شهري (آخر 30 يوماً)":
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
        else:
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("من تاريخ", value=datetime.now() - timedelta(days=7))
            with col2:
                end_date = st.date_input("إلى تاريخ", value=datetime.now())
        
        if st.button("تحميل التقرير (CSV)"):
            csv_data = invoice_service.export_invoices_to_csv(str(start_date), str(end_date), rep_id)
            if csv_data:
                st.download_button(
                    label="📥 تحميل الملف",
                    data=csv_data,
                    file_name=f"report_{selected_rep}_{start_date}_to_{end_date}.csv",
                    mime="text/csv"
                )
            else:
                st.warning("لا توجد فواتير في هذه الفترة")