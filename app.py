import streamlit as st
import pandas as pd
import os
import re
from datetime import date
from io import BytesIO
from pypdf import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from supabase import create_client, Client

st.set_page_config(page_title="Wrapsense Dashboard", layout="wide")

# -----------------------------
# Supabase Connection
# -----------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# -----------------------------
# File Storage
# -----------------------------
PO_FILE = "purchase_orders.csv"

# -----------------------------
# Session State
# -----------------------------
if "clients_data" not in st.session_state:
    st.session_state.clients_data = []

if "starter_tasks" not in st.session_state:
    st.session_state.starter_tasks = []

if "current_customer" not in st.session_state:
    st.session_state.current_customer = ""

try:
    if "purchase_orders_data" not in st.session_state:
        if os.path.exists(PO_FILE) and os.path.getsize(PO_FILE) > 0:
            st.session_state.purchase_orders_data = pd.read_csv(PO_FILE).to_dict("records")
        else:
            st.session_state.purchase_orders_data = []
except pd.errors.EmptyDataError:
    st.session_state.purchase_orders_data = []

if "suppliers_data" not in st.session_state:
    st.session_state.suppliers_data = []

# -----------------------------
# Demo Data
# -----------------------------
def load_data(query):
    return pd.DataFrame(
        {
            "Project": ["FJ Pouch Line Project"],
            "Client": ["ForJars Canning Supply Inc."],
            "Status": ["Active"],
            "Tasks": [len(st.session_state.starter_tasks)],
            "Purchase Orders": [len(st.session_state.purchase_orders_data)],
            "Quotes": [1],
        }
    )

# -----------------------------
# Save Purchase Orders Locally
# -----------------------------
def save_purchase_orders():
    df = pd.DataFrame(st.session_state.purchase_orders_data)
    df.to_csv(PO_FILE, index=False)

# -----------------------------
# Supabase Supplier Functions
# -----------------------------
def load_suppliers_from_supabase():
    response = supabase.table("suppliers").select("*").execute()
    return response.data

def add_supplier_to_supabase(supplier):
    return supabase.table("suppliers").insert(
        {
            "supplier": supplier.get("Supplier", ""),
            "country": supplier.get("Country", ""),
            "specialty": supplier.get("Specialty", ""),
            "contact": supplier.get("Contact", ""),
            "email": supplier.get("Email", ""),
            "notes": supplier.get("Notes", ""),
        }
    ).execute()

def delete_supplier_from_supabase(supplier_id):
    return supabase.table("suppliers").delete().eq("id", supplier_id).execute()

# -----------------------------
# PDF Upload + Extraction
# -----------------------------
def extract_text_from_pdf(uploaded_file):
    reader = PdfReader(uploaded_file)
    text = ""

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"

    return text

def extract_po_fields(text):
    po_number = re.search(r"(PO\s*(Number|#)?[:\s]+)([A-Z0-9\-]+)", text, re.I)
    supplier = re.search(r"(Supplier|Vendor)[:\s]+(.+)", text, re.I)
    incoterm = re.search(r"\b(FOB|EXW|CIF|DDP)\b", text, re.I)
    lead_time = re.search(r"(Lead\s*Time)[:\s]+(.+)", text, re.I)
    payment_terms = re.search(r"(Payment\s*Terms)[:\s]+(.+)", text, re.I)

    return {
        "po_number": po_number.group(3).strip() if po_number else "",
        "supplier": supplier.group(2).strip() if supplier else "",
        "incoterm": incoterm.group(1).upper() if incoterm else "FOB",
        "lead_time": lead_time.group(2).strip() if lead_time else "",
        "payment_terms": payment_terms.group(2).strip() if payment_terms else "",
        "raw_text": text,
    }

# -----------------------------
# PDF Generator
# -----------------------------
def generate_po_pdf(po):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)

    width, height = letter
    y = height - 50

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, y, "Wrapsense Purchase Order")

    y -= 35
    pdf.setFont("Helvetica", 10)
    pdf.drawString(50, y, f"PO Number: {po.get('PO Number', '')}")
    y -= 18
    pdf.drawString(50, y, f"PO Date: {po.get('PO Date', '')}")
    y -= 18
    pdf.drawString(50, y, f"Supplier: {po.get('Supplier', '')}")
    y -= 18
    pdf.drawString(50, y, f"Title: {po.get('Title', '')}")
    y -= 18
    pdf.drawString(50, y, f"Incoterm: {po.get('Incoterm', '')}")
    y -= 18
    pdf.drawString(50, y, f"Lead Time: {po.get('Lead Time', '')}")

    y -= 35
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Line Item")

    y -= 22
    pdf.setFont("Helvetica", 10)
    pdf.drawString(50, y, f"Description: {po.get('Item', '')}")
    y -= 18
    pdf.drawString(50, y, f"Quantity: {po.get('Quantity', '')}")
    y -= 18
    pdf.drawString(50, y, f"Unit Price: ${po.get('Unit Price', '')}")
    y -= 18
    pdf.drawString(50, y, f"Line Total: ${po.get('Line Total', '')}")

    y -= 35
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Payment Terms")

    y -= 18
    pdf.setFont("Helvetica", 10)
    payment_terms = str(po.get("Payment Terms", ""))
    pdf.drawString(50, y, payment_terms[:90])

    y -= 35
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Supplier-Facing Notes")

    y -= 18
    pdf.setFont("Helvetica", 10)
    notes = str(po.get("Notes", ""))
    pdf.drawString(50, y, notes[:90])

    y -= 50
    pdf.setFont("Helvetica-Oblique", 9)
    pdf.drawString(
        50,
        y,
        "Customer/client names are intentionally omitted from supplier-facing PO documents.",
    )

    pdf.save()
    buffer.seek(0)
    return buffer

# -----------------------------
# Header + Sidebar
# -----------------------------
st.title("Wrapsense Operations Dashboard")

st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to",
    [
        "Dashboard",
        "Guided Workflow",
        "Clients",
        "Projects",
        "Tasks",
        "Quotes",
        "Purchase Orders",
        "Suppliers",
    ],
)

# -----------------------------
# Pages
# -----------------------------
if page == "Guided Workflow":
    st.header("Guided Workflow")

    workflow_type = st.selectbox(
        "What are you starting?",
        [
            "New Customer",
            "New Supplier",
            "New Project",
            "New Quote",
            "New Purchase Order",
        ],
    )

    if workflow_type == "New Customer":
        st.subheader("New Customer Wizard")

        with st.form("new_customer_form"):
            customer_name = st.text_input("Customer Name")
            contact = st.text_input("Main Contact")
            email = st.text_input("Email")
            phone = st.text_input("Phone")
            notes = st.text_area("Internal Notes")

            submitted = st.form_submit_button("Save Customer")

            if submitted:
                new_customer = {
                    "Customer Name": customer_name,
                    "Contact": contact,
                    "Email": email,
                    "Phone": phone,
                    "Notes": notes,
                }

                st.session_state.clients_data.append(new_customer)
                st.session_state.current_customer = customer_name
                st.success("Customer saved!")

    elif workflow_type == "New Supplier":
        st.subheader("New Supplier Wizard")

        with st.form("new_supplier_form"):
            supplier_name = st.text_input("Supplier Name")
            country = st.text_input("Country")
            specialty = st.text_input("Specialty")
            contact = st.text_input("Contact Person")
            email = st.text_input("Email")
            notes = st.text_area("Notes")

            submitted = st.form_submit_button("Save Supplier")

            if submitted:
                new_supplier = {
                    "Supplier": supplier_name,
                    "Country": country,
                    "Specialty": specialty,
                    "Contact": contact,
                    "Email": email,
                    "Notes": notes,
                }

                add_supplier_to_supabase(new_supplier)
                st.session_state.suppliers_data = load_suppliers_from_supabase()
                st.success("Supplier saved to Supabase!")

        st.markdown("### Recommended Next Actions")
        st.checkbox("Upload Supplier PI")
        st.checkbox("Link supplier to project")
        st.checkbox("Create purchase order")
        st.checkbox("Add sourcing task")

    elif workflow_type == "New Purchase Order":
        st.subheader("New Purchase Order Wizard")

        st.warning(
            "Privacy rule: customer/client names should NOT appear on supplier-facing PO documents."
        )

        uploaded_po = st.file_uploader("Upload Purchase Order PDF", type=["pdf"])

        extracted = {
            "po_number": "",
            "supplier": "",
            "incoterm": "FOB",
            "lead_time": "",
            "payment_terms": "",
            "raw_text": "",
        }

        if uploaded_po is not None:
            pdf_text = extract_text_from_pdf(uploaded_po)
            extracted = extract_po_fields(pdf_text)
            st.success("PDF uploaded and text extracted.")

            with st.expander("View extracted text"):
                st.text_area("Extracted PDF Text", extracted["raw_text"], height=300)

        with st.form("new_po_form"):
            po_number = st.text_input(
                "PO Number",
                value=extracted["po_number"],
                placeholder="Example: WS-PO-2026-001",
            )

            po_date = st.date_input("PO Date", value=date.today())

            supplier = st.text_input(
                "Supplier Name",
                value=extracted["supplier"],
            )

            project = st.text_input(
                "Project / Internal Reference",
                placeholder="Example: CL-FJ4",
            )

            po_title = st.text_input("PO Title")

            incoterm_options = ["FOB", "EXW", "CIF", "DDP", "Other"]
            incoterm_index = (
                incoterm_options.index(extracted["incoterm"])
                if extracted["incoterm"] in incoterm_options
                else 0
            )

            incoterm = st.selectbox(
                "Incoterm",
                incoterm_options,
                index=incoterm_index,
            )

            payment_terms = st.text_area(
                "Payment Terms",
                value=extracted["payment_terms"],
            )

            lead_time = st.text_input(
                "Lead Time",
                value=extracted["lead_time"],
            )

            notes = st.text_area(
                "Supplier-Facing Notes",
                placeholder="Do NOT include customer/client name here.",
            )

            st.markdown("### Line Item")
            item_description = st.text_input("Item Description")
            quantity = st.number_input("Quantity", min_value=1, value=1)
            unit_price = st.number_input("Unit Price", min_value=0.0, value=0.0)

            submitted = st.form_submit_button("Save PO Draft")

            if submitted:
                line_total = quantity * unit_price

                new_po = {
                    "PO Number": po_number,
                    "PO Date": str(po_date),
                    "Supplier": supplier,
                    "Project": project,
                    "Title": po_title,
                    "Incoterm": incoterm,
                    "Payment Terms": payment_terms,
                    "Lead Time": lead_time,
                    "Notes": notes,
                    "Item": item_description,
                    "Quantity": quantity,
                    "Unit Price": unit_price,
                    "Line Total": line_total,
                    "Status": "Draft",
                }

                st.session_state.purchase_orders_data.append(new_po)
                save_purchase_orders()
                st.success("PO draft saved!")

    elif workflow_type == "New Project":
        st.subheader("New Project Wizard")
        st.info("This workflow is coming next.")

    elif workflow_type == "New Quote":
        st.subheader("New Quote Wizard")
        st.info("This workflow is coming next.")

elif page == "Dashboard":
    st.header("Project Dashboard")
    df = load_data("SELECT * FROM project_dashboard;")
    st.dataframe(df, use_container_width=True)

elif page == "Clients":
    st.header("Clients")

    if st.session_state.clients_data:
        st.dataframe(pd.DataFrame(st.session_state.clients_data), use_container_width=True)
    else:
        st.info("No clients added yet.")

elif page == "Projects":
    st.header("Projects")
    df = load_data("SELECT * FROM projects;")
    st.dataframe(df, use_container_width=True)

elif page == "Tasks":
    st.header("Tasks")

    if st.session_state.starter_tasks:
        st.dataframe(pd.DataFrame(st.session_state.starter_tasks), use_container_width=True)
    else:
        st.info("No starter tasks created yet.")

elif page == "Quotes":
    st.header("Quotes")
    df = load_data("SELECT * FROM quote_dashboard;")
    st.dataframe(df, use_container_width=True)

elif page == "Purchase Orders":
    st.header("Purchase Orders")

    if st.session_state.purchase_orders_data:
        df = pd.DataFrame(st.session_state.purchase_orders_data)

        st.markdown("### Edit Purchase Orders")

        edited_df = st.data_editor(
            df,
            use_container_width=True,
            num_rows="dynamic",
            key="po_editor",
        )

        if st.button("Save Purchase Order Changes"):
            st.session_state.purchase_orders_data = edited_df.to_dict("records")
            save_purchase_orders()
            st.success("Purchase order changes saved!")
            st.rerun()

        current_po_data = edited_df.to_dict("records")

        st.markdown("---")

        csv = edited_df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Download Purchase Orders CSV",
            data=csv,
            file_name="purchase_orders.csv",
            mime="text/csv",
        )

        st.markdown("### Generate PO PDF")

        po_options = [
            f"{po.get('PO Number', 'No PO Number')} — {po.get('Supplier', 'No Supplier')}"
            for po in current_po_data
        ]

        selected_po_label = st.selectbox(
            "Select PO",
            po_options,
            key="pdf_po_select",
        )

        selected_index = po_options.index(selected_po_label)
        selected_po = current_po_data[selected_index]

        pdf_file = generate_po_pdf(selected_po)

        st.download_button(
            label="Download Selected PO as PDF",
            data=pdf_file,
            file_name=f"{selected_po.get('PO Number', 'purchase_order')}.pdf",
            mime="application/pdf",
        )

        st.markdown("---")
        st.markdown("## Delete Purchase Order")

        delete_po_label = st.selectbox(
            "Select PO to Delete",
            po_options,
            key="delete_po_select",
        )

        delete_index = po_options.index(delete_po_label)
        confirm_delete = st.checkbox("I understand this action cannot be undone.")

        if st.button("Delete Selected Purchase Order"):
            if confirm_delete:
                st.session_state.purchase_orders_data = current_po_data
                deleted_po = st.session_state.purchase_orders_data.pop(delete_index)
                save_purchase_orders()

                st.success(
                    f"Purchase Order {deleted_po.get('PO Number')} deleted successfully."
                )

                st.rerun()
            else:
                st.warning("Please confirm deletion before removing the purchase order.")

    else:
        st.info("No purchase orders created yet.")

elif page == "Suppliers":
    st.header("Suppliers")

    st.session_state.suppliers_data = load_suppliers_from_supabase()

    if st.session_state.suppliers_data:
        df = pd.DataFrame(st.session_state.suppliers_data)
        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Download Suppliers CSV",
            data=csv,
            file_name="suppliers.csv",
            mime="text/csv",
        )

        st.markdown("---")
        st.markdown("## Delete Supplier")

        supplier_options = [
            f"{supplier.get('supplier', 'No Supplier')} — {supplier.get('country', 'No Country')}"
            for supplier in st.session_state.suppliers_data
        ]

        selected_supplier_label = st.selectbox(
            "Select Supplier to Delete",
            supplier_options,
            key="delete_supplier_select",
        )

        selected_supplier_index = supplier_options.index(selected_supplier_label)
        selected_supplier = st.session_state.suppliers_data[selected_supplier_index]

        confirm_delete_supplier = st.checkbox(
            "I understand this supplier will be permanently deleted."
        )

        if st.button("Delete Selected Supplier"):
            if confirm_delete_supplier:
                delete_supplier_from_supabase(selected_supplier["id"])

                st.success(
                    f"Supplier {selected_supplier.get('supplier')} deleted successfully."
                )

                st.rerun()
            else:
                st.warning("Please confirm deletion before removing the supplier.")

    else:
        st.info("No suppliers added yet.")