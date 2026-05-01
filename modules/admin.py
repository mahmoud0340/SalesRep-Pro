# modules/admin.py
import streamlit as st
from services import client_service, invoice_service, google_sheets_service
import database.db as db
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px

def show_admin_dashboard():
    st.title("👑 لوحة تحكم المدير - HANZ & TEX")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["👥 المستخدمين", "🏢 العملاء", "📊 أداء المندوبين", "📅 التقارير", "📈 التحليلات", "🗑️ إدارة الفواتير"])

    # ----------------------------- تبويب المستخدمين -----------------------------
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
            st.dataframe(user_data, width='stretch')
        else:
            st.write("لا يوجد مستخدمون بعد.")
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
            if user_options:
                selected_user_label = st.selectbox("اختر مستخدم", list(user_options.keys()))
                if selected_user_label:
                    user_id = user_options[selected_user_label]
                    selected_user = next(u for u in users if u['id'] == user_id)
                    new_pass = st.text_input("كلمة المرور الجديدة (اترك فارغاً إذا لا تريد التغيير)", type="password")
                    is_active = st.checkbox("نشط", value=selected_user['is_active'])
                    if st.button("تحديث البيانات"):
                        if new_pass:
                            success, msg = db.update_user_password(user_id, new_pass)
                            if not success:
                                st.error(msg)
                            else:
                                st.success(msg)
                        db.update_user_activation(user_id, 1 if is_active else 0)
                        st.rerun()
                    if selected_user['role'] == 'Rep':
                        with db.get_db_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("SELECT COUNT(*) FROM Clients WHERE Assigned_Rep = ?", (user_id,))
                            count = cursor.fetchone()[0]
                        if count > 0:
                            st.warning(f"هذا المندوب مسؤول عن {count} عميل. إذا أردت حذفه، يجب نقل العملاء أولاً.")
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
                                st.info("لا يوجد مندوب آخر نشط لنقل العملاء إليه.")
                    if st.button("حذف المستخدم (بدون عملاء)", key="del_user"):
                        success, msg = db.delete_user(user_id, st.session_state['user_id'])
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
            else:
                st.info("لا يوجد مستخدمون لتعديلهم.")

    # ----------------------------- تبويب العملاء -----------------------------
    with tab2:
        st.subheader("جميع العملاء")
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
                    st.write(f"**الموقع التفصيلي:** {cl['location'] or 'غير محدد'}")
                    if st.button(f"تعديل العميل {cl['id']}", key=f"edit_{cl['id']}"):
                        st.session_state['edit_client_id'] = cl['id']
                        st.rerun()
        else:
            st.info("لا يوجد عملاء.")
        if 'edit_client_id' in st.session_state:
            client_id = st.session_state['edit_client_id']
            client = client_service.get_client_by_id(client_id)
            if client:
                st.subheader(f"تعديل بيانات العميل: {client['name']}")
                users = db.get_all_users()
                reps = [u for u in users if u['role'] == 'Rep' and u['is_active']]
                rep_dict = {f"{r['username']} (ID: {r['id']})": r['id'] for r in reps}
                with st.form("edit_client_form"):
                    new_name = st.text_input("الاسم", value=client['name'])
                    new_phone = st.text_input("الهاتف", value=client['phone'] or "")
                    new_address = st.text_area("العنوان", value=client['address'])
                    new_location = st.text_input("الموقع التفصيلي", value=client['location'] or "")
                    current_rep = next((f"{r['username']} (ID: {r['id']})" for r in reps if r['id'] == client['rep_id']), list(rep_dict.keys())[0] if rep_dict else "")
                    new_rep = st.selectbox("المندوب المسؤول", list(rep_dict.keys()), index=list(rep_dict.keys()).index(current_rep) if current_rep in rep_dict else 0)
                    submitted = st.form_submit_button("حفظ التعديلات")
                    if submitted:
                        rep_id = rep_dict[new_rep]
                        client_service.update_client(client_id, new_name, new_phone, new_address, new_location, rep_id)
                        st.success("تم التحديث بنجاح")
                        del st.session_state['edit_client_id']
                        st.rerun()
                if st.button("إلغاء التعديل"):
                    del st.session_state['edit_client_id']
                    st.rerun()

    # ----------------------------- تبويب أداء المندوبين -----------------------------
    with tab3:
        st.subheader("أداء المندوبين")
        performance = invoice_service.get_all_reps_performance()
        if performance:
            for rep in performance:
                with st.container():
                    st.markdown(f"### 👤 {rep['username']}")
                    col1, col2, col3 = st.columns(3)
                    col1.metric("💰 إجمالي المبيعات", f"{rep['total_sales']:,.2f} ج.م")
                    col2.metric("📦 إجمالي الكميات", f"{rep['total_qty']} قطعة")
                    col3.metric("🧾 عدد الفواتير", f"{rep['invoice_count']}")
                    st.divider()
        else:
            st.info("لا توجد بيانات للمندوبين بعد.")

    # ----------------------------- تبويب التقارير -----------------------------
    with tab4:
        st.subheader("📥 تصدير ورفع التقارير")
        rep_options = {"كل المندوبين": None}
        users = db.get_all_users()
        reps = [u for u in users if u['role'] == 'Rep']
        for r in reps:
            rep_options[r['username']] = r['id']
        selected_rep = st.selectbox("اختر المندوب", list(rep_options.keys()))
        rep_id = rep_options[selected_rep]
        report_type = st.radio("الفترة", ["يومي", "أسبوعي (آخر 7 أيام)", "شهري (آخر 30 يوماً)", "فترة مخصصة"])
        today = datetime.now().date()
        if report_type == "يومي":
            start_date = today
            end_date = today
        elif report_type == "أسبوعي (آخر 7 أيام)":
            start_date = today - timedelta(days=7)
            end_date = today
        elif report_type == "شهري (آخر 30 يوماً)":
            start_date = today - timedelta(days=30)
            end_date = today
        else:
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("من تاريخ", value=today - timedelta(days=7))
            with col2:
                end_date = st.date_input("إلى تاريخ", value=today)
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📄 CSV (تقليدي)"):
                csv_data = invoice_service.export_invoices_to_csv(str(start_date), str(end_date), rep_id)
                if csv_data:
                    st.download_button(
                        label="💾 تحميل CSV",
                        data=csv_data,
                        file_name=f"report_{selected_rep}_{start_date}_to_{end_date}.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("لا توجد فواتير.")
        with col2:
            if st.button("📊 Excel (احترافي)"):
                excel_data = invoice_service.export_invoices_to_excel(str(start_date), str(end_date), rep_id)
                if excel_data:
                    st.download_button(
                        label="💾 تحميل Excel",
                        data=excel_data,
                        file_name=f"report_{selected_rep}_{start_date}_to_{end_date}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.warning("لا توجد فواتير.")
        with col3:
            if st.button("☁️ رفع إلى Google Sheets"):
                report_rows = invoice_service.get_report_data_for_google_sheets(str(start_date), str(end_date), rep_id)
                if report_rows:
                    success, msg = google_sheets_service.append_report_to_google_sheets(report_rows, sheet_name=f"تقرير_{selected_rep}")
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
                else:
                    st.warning("لا توجد فواتير لرفعها.")

    # ----------------------------- تبويب التحليلات -----------------------------
    with tab5:
        st.subheader("📈 لوحة التحليلات التفاعلية")
        def get_all_invoices_data():
            with db.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT i.Invoice_ID, i.Amount, i.Quantity, i.Created_At, i.ProductName, 
                           c.Name as ClientName, u.username as RepName
                    FROM Invoices i
                    JOIN Clients c ON i.Client_ID = c.Client_ID
                    JOIN Users u ON c.Assigned_Rep = u.id
                    WHERE i.is_deleted = 0
                    ORDER BY i.Created_At
                """)
                rows = cursor.fetchall()
                return [{"id": r[0], "amount": r[1], "quantity": r[2], "date": r[3],
                         "product": r[4] or "", "client": r[5], "rep": r[6]} for r in rows]
        try:
            invoices_data = get_all_invoices_data()
            if not invoices_data:
                st.info("لا توجد فواتير مسجلة حتى الآن لعرض التحليلات.")
            else:
                df = pd.DataFrame(invoices_data)
                df['date'] = pd.to_datetime(df['date'])
                df['month'] = df['date'].dt.strftime('%Y-%m')
                rep_sales = df.groupby('rep')['amount'].sum().reset_index().sort_values('amount', ascending=False)
                fig1 = px.bar(rep_sales, x='rep', y='amount', title="إجمالي المبيعات لكل مندوب (ج.م)",
                              labels={'rep': 'المندوب', 'amount': 'المبيعات'},
                              color='amount', color_continuous_scale='Blues')
                st.plotly_chart(fig1, width='stretch')
                monthly_sales = df.groupby('month')['amount'].sum().reset_index()
                fig2 = px.line(monthly_sales, x='month', y='amount', title="اتجاه المبيعات الشهرية",
                               labels={'month': 'الشهر', 'amount': 'المبيعات (ج.م)'},
                               markers=True)
                st.plotly_chart(fig2, width='stretch')
                product_qty = df.groupby('product')['quantity'].sum().reset_index().sort_values('quantity', ascending=False).head(10)
                fig3 = px.bar(product_qty, x='quantity', y='product', orientation='h',
                              title="أكثر 10 منتجات مبيعاً (بالقطع)",
                              labels={'quantity': 'الكمية المباعة', 'product': 'المنتج'},
                              color='quantity', color_continuous_scale='viridis')
                st.plotly_chart(fig3, width='stretch')
        except Exception as e:
            st.error(f"حدث خطأ أثناء تحميل التحليلات: {str(e)}")

    # ----------------------------- تبويب إدارة الفواتير -----------------------------
    with tab6:
        st.subheader("🗑️ حذف الفواتير")
        with db.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT i.Invoice_ID, i.Created_At, i.Amount, i.ProductName, 
                       c.Name as ClientName, u.username as RepName
                FROM Invoices i
                JOIN Clients c ON i.Client_ID = c.Client_ID
                JOIN Users u ON c.Assigned_Rep = u.id
                WHERE i.is_deleted = 0
                ORDER BY i.Created_At DESC
            """)
            invoices = cursor.fetchall()

        if not invoices:
            st.info("لا توجد فواتير مسجلة حتى الآن.")
        else:
            for inv in invoices:
                inv_id, inv_date, inv_amount, inv_product, client_name, rep_name = inv
                with st.expander(f"فاتورة رقم {inv_id} - العميل: {client_name} - التاريخ: {inv_date[:10]}"):
                    st.write(f"**المبلغ:** {inv_amount:.2f} ج.م")
                    st.write(f"**المنتج:** {inv_product or 'غير محدد'}")
                    st.write(f"**المندوب:** {rep_name}")
                    if st.button(f"🗑️ حذف هذه الفاتورة", key=f"del_inv_{inv_id}"):
                        st.session_state['invoice_to_delete'] = inv_id
                        st.rerun()
                if 'invoice_to_delete' in st.session_state and st.session_state['invoice_to_delete'] == inv_id:
                    st.warning(f"هل أنت متأكد من حذف الفاتورة رقم {inv_id}؟ هذا الإجراء لا يمكن التراجع عنه.")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ نعم، احذف", key=f"confirm_del_{inv_id}"):
                            success, msg = invoice_service.soft_delete_invoice(inv_id)
                            if success:
                                st.success(msg)
                                del st.session_state['invoice_to_delete']
                                st.rerun()
                            else:
                                st.error(msg)
                    with col2:
                        if st.button("❌ لا، إلغاء", key=f"cancel_del_{inv_id}"):
                            del st.session_state['invoice_to_delete']
                            st.rerun()