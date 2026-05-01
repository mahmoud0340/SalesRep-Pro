# modules/rep.py
import streamlit as st
from services import client_service, invoice_service
from datetime import datetime

PRODUCTS = [
    "HANZ (ATF)",
    "TEX 400 g.w ( BREAK FLUID ) DOT 3",
    "TEX 355 g.w ( BREAK FLUID ) DOT 3",
    "HANZ HYDRAULIC ( CH 68 )",
    "GEAR OIL ( 140 )"
]

def show_rep_dashboard(rep_id):
    st.title("🛢️ لوحة تحكم المندوب - HANZ & TEX")

    total_clients = client_service.get_clients_count_by_rep(rep_id)
    total_sales_amount, _, _ = invoice_service.get_rep_sales_summary(rep_id)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("📋 عدد العملاء", total_clients)
    with col2:
        st.metric("💰 إجمالي المبيعات", f"{total_sales_amount:,.2f} ج.م")

    st.divider()

    tab1, tab2, tab3 = st.tabs(["👥 العملاء", "➕ إضافة عميل", "🧾 الفواتير"])

    with tab1:
        st.subheader("قائمة عملائي")
        clients = client_service.get_clients_by_rep(rep_id)
        if not clients:
            st.info("لا يوجد عملاء مسجلين حتى الآن.")
        else:
            for client in clients:
                with st.expander(f"{client['name']} - كود: {client['code']}"):
                    st.write(f"📞 **الهاتف:** {client['phone'] or 'غير مسجل'}")
                    st.write(f"🏠 **العنوان:** {client['address']}")
                    st.write(f"📍 **الموقع التفصيلي:** {client['location'] or 'غير محدد'}")

                    last_inv = invoice_service.get_last_invoice_by_client(client['id'])
                    if last_inv:
                        st.markdown("---")
                        st.markdown("**📄 آخر فاتورة:**")
                        st.write(f"🗓️ **التاريخ:** {last_inv['date']}")
                        st.write(f"🛒 **المنتج:** {last_inv['product']}")
                        st.write(f"📦 **العدد:** {last_inv['quantity']}")
                        st.write(f"💰 **المبلغ:** {last_inv['amount']:,.2f} ج.م")
                        if last_inv['notes']:
                            st.write(f"📝 **ملاحظات:** {last_inv['notes']}")
                    else:
                        st.markdown("---")
                        st.info("لا توجد فواتير سابقة لهذا العميل.")

                    if st.button(f"📝 إنشاء فاتورة جديدة لـ {client['name']}", key=f"new_inv_{client['id']}"):
                        st.session_state['selected_client_for_invoice'] = client
                        st.session_state['focus_on_invoice_form'] = True
                        st.rerun()

    with tab2:
        st.subheader("إضافة عميل جديد")
        with st.form("add_client_form", clear_on_submit=True):
            name = st.text_input("الاسم الكامل *")
            phone = st.text_input("رقم الهاتف")
            address = st.text_area("العنوان الأساسي *")
            location = st.text_input("الموقع التفصيلي (مثل: الحي، الشارع، الفرع)")
            submitted = st.form_submit_button("✅ إضافة العميل")
            if submitted:
                if not name or not address:
                    st.error("❌ الاسم والعنوان الأساسي مطلوبان.")
                else:
                    success, code = client_service.add_client(name, phone, address, rep_id, location)
                    if success:
                        st.success(f"✅ تم إضافة العميل بنجاح. كود العميل: `{code}`")
                        st.rerun()
                    else:
                        st.error(f"❌ حدث خطأ: {code}")

    with tab3:
        st.subheader("إنشاء فاتورة جديدة")

        if 'selected_client_for_invoice' in st.session_state:
            client = st.session_state['selected_client_for_invoice']
            st.info(f"📄 إنشاء فاتورة للعميل: **{client['name']}** ({client['code']}) - الموقع: {client['location'] or 'غير محدد'}")

            with st.form("invoice_form", clear_on_submit=True):
                qty = st.number_input("🔢 العدد (قطع)", min_value=1, step=1, value=None, placeholder="أدخل العدد")
                price = st.number_input("💰 سعر الوحدة (ج.م)", min_value=0.0, step=0.5, format="%.2f", value=None, placeholder="أدخل السعر")
                product = st.selectbox("🛒 المنتج", PRODUCTS + ["(منتج غير مدرج)"])
                custom_product = ""
                if product == "(منتج غير مدرج)":
                    custom_product = st.text_input("✏️ أدخل اسم المنتج الجديد")
                notes = st.text_area("📝 ملاحظات (اختياري)")

                submitted_inv = st.form_submit_button("💾 إنشاء الفاتورة")

                if submitted_inv:
                    error = False
                    if qty is None or qty <= 0:
                        st.error("❌ يرجى إدخال عدد صحيح أكبر من صفر.")
                        error = True
                    elif price is None or price < 0:
                        st.error("❌ يرجى إدخال سعر غير سالب.")
                        error = True
                    else:
                        final_product = custom_product if (product == "(منتج غير مدرج)" and custom_product) else product
                        if not final_product:
                            st.error("❌ يرجى إدخال اسم المنتج الجديد أو اختيار منتج من القائمة.")
                            error = True

                    if not error:
                        try:
                            inv_id, total = invoice_service.create_invoice(
                                client['id'], qty, price, final_product, notes
                            )
                            st.success(f"✅ تم إنشاء الفاتورة رقم `{inv_id}` بنجاح")
                            st.markdown("### 🧾 تفاصيل الفاتورة")
                            st.write(f"- **العميل:** {client['name']}")
                            st.write(f"- **التاريخ:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                            st.write(f"- **المنتج:** {final_product}")
                            st.write(f"- **العدد:** {qty}")
                            st.write(f"- **سعر الوحدة:** {price:.2f} ج.م")
                            st.write(f"- **الإجمالي:** {total:,.2f} ج.م")
                            if notes:
                                st.write(f"- **ملاحظات:** {notes}")

                            del st.session_state['selected_client_for_invoice']
                            if 'focus_on_invoice_form' in st.session_state:
                                del st.session_state['focus_on_invoice_form']
                            st.rerun()
                        except ValueError as e:
                            st.error(f"❌ خطأ: {e}")

            if st.button("❌ إلغاء إنشاء الفاتورة"):
                del st.session_state['selected_client_for_invoice']
                if 'focus_on_invoice_form' in st.session_state:
                    del st.session_state['focus_on_invoice_form']
                st.rerun()

        else:
            st.subheader("سجل الفواتير السابقة")
            invoices = invoice_service.get_invoices_by_rep(rep_id)
            if not invoices:
                st.info("لا توجد فواتير مسجلة حتى الآن.")
            else:
                for inv in invoices:
                    with st.expander(f"🧾 فاتورة رقم {inv['id']} - العميل: {inv['client_name']} - {inv['date'][:10]}"):
                        st.write(f"💰 **المبلغ الإجمالي:** {inv['amount']:,.2f} ج.م")
                        st.write(f"📦 **العدد:** {inv['quantity']}")
                        st.write(f"🛒 **المنتج:** {inv['product'] or 'غير محدد'}")
                        st.write(f"📝 **الملاحظات:** {inv['notes'] or 'لا توجد'}")