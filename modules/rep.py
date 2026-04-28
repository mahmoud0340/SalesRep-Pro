# modules/rep.py
import streamlit as st
from services import client_service, invoice_service

def show_rep_dashboard(rep_id):
    st.title("لوحة تحكم المندوب")
    
    total_clients = client_service.get_clients_count_by_rep(rep_id)
    total_sales_amount, _ = invoice_service.get_rep_sales_summary(rep_id)
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("عدد العملاء", total_clients)
    with col2:
        st.metric("إجمالي المبيعات", f"{total_sales_amount:.2f} ج.م")
    
    st.divider()
    
    tab1, tab2, tab3 = st.tabs(["العملاء", "إضافة عميل", "الفواتير"])
    
    with tab1:
        st.subheader("قائمة عملائي")
        clients = client_service.get_clients_by_rep(rep_id)
        if not clients:
            st.info("لا يوجد عملاء بعد.")
        else:
            for c in clients:
                with st.expander(f"{c['name']} - كود: {c['code']}"):
                    st.write(f"**الهاتف:** {c['phone'] or 'لا يوجد'}")
                    st.write(f"**العنوان:** {c['address']}")
                    if st.button(f"إنشاء فاتورة للعميل {c['name']}", key=f"inv_{c['id']}"):
                        st.session_state['selected_client_for_invoice'] = c
                        st.rerun()
    
    with tab2:
        st.subheader("إضافة عميل جديد")
        with st.form("add_client_form"):
            name = st.text_input("الاسم *")
            phone = st.text_input("رقم الهاتف")
            address = st.text_area("العنوان *")
            submitted = st.form_submit_button("إضافة العميل")
            if submitted:
                if not name or not address:
                    st.error("الاسم والعنوان مطلوبان")
                else:
                    success, code = client_service.add_client(name, phone, address, rep_id)
                    if success:
                        st.success(f"تم إضافة العميل بنجاح. كود العميل: {code}")
                        st.rerun()
                    else:
                        st.error(f"خطأ: {code}")
    
    with tab3:
        st.subheader("الفواتير")
        if 'selected_client_for_invoice' in st.session_state:
            client = st.session_state.selected_client_for_invoice
            st.info(f"إنشاء فاتورة للعميل: {client['name']}")
            with st.form("invoice_form"):
                qty = st.number_input("العدد (قطع)", min_value=1, step=1)
                price = st.number_input("سعر الوحدة", min_value=0.0, step=0.5, format="%.2f")
                notes = st.text_area("ملاحظات (اختياري)")
                submit_inv = st.form_submit_button("إنشاء الفاتورة")
                if submit_inv:
                    try:
                        inv_id, total = invoice_service.create_invoice(client['id'], qty, price, notes)
                        st.success(f"تم إنشاء الفاتورة رقم {inv_id} بقيمة {total:.2f} ج.م")
                        del st.session_state['selected_client_for_invoice']
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
            if st.button("إلغاء"):
                del st.session_state['selected_client_for_invoice']
                st.rerun()
        else:
            invoices = invoice_service.get_invoices_by_rep(rep_id)
            if invoices:
                for inv in invoices:
                    with st.expander(f"فاتورة #{inv['id']} - {inv['client_name']} - {inv['date'][:10]}"):
                        st.write(f"**المبلغ:** {inv['amount']:.2f} ج.م")
                        st.write(f"**العدد:** {inv['quantity']}")
                        st.write(f"**الملاحظات:** {inv['notes'] or 'لا توجد'}")
            else:
                st.write("لا توجد فواتير بعد.")