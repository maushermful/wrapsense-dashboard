import streamlit as st
import pandas as pd
import os
from datetime import date
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


st.set_page_config(page_title="Wrapsense Dashboard", layout="wide")

# -----------------------------
# File Storage
# -----------------------------
PO_FILE = "purchase_orders.csv"

# -----------------------------
# Session State
# -----------------------------
if "clients_data" not in st.session_state:
    st.session_state.clients_data = []

if "suppliers_data" not in st.session_state:
    st.session_state.suppliers_data = []

if "starter_tasks" not in st.session_state:
    st.session_state.starter_tasks = []

if "purchase_orders_data" not in st.session_state:
    if os.path.exists(PO_FILE):
        st.session_state.purchase_orders_data = pd.read_csv(PO_FILE).to_dict("records")
    else:
        st.session_state.purchase_orders_data = []

if "current_customer" not in st.session_state:
    st.session_state.current_customer = ""

# -----------------------------
# Demo Data
# -----------------------------
def load_data(query):
    return pd.DataFrame({
        "Project": ["FJ Pouch Line Project"],
        "Client": ["ForJars Canning Supply Inc."],
        "Status": ["Active"],
        "Tasks": [1],
        "Purchase Orders": [len(st.session_state.purchase_orders_data)],
        "Quotes": [1]
    })

# -----------------------------
# Save Functions
# -----------------------------
def save_purchase_orders():
    df = pd.DataFrame(st.session_state.purchase_orders_data)
    df.to_csv(PO_FILE, index=False)

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
        "Customer/client names are intentionally omitted from supplier-facing PO documents."
    )

    pdf.save()
    buffer.seek(0)
    return buffer

# -----------------------------
# Header
# -----------------------------
st.title("Wrapsense Operations Dashboard")

# -----------------------------
# Sidebar
# -----------------------------
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
        "Suppliers"
    ]
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
            "New Purchase Order"
        ]
    )

    if workflow_type == "New Customer":
        st.subheader("New Customer Wizard")

        st.markdown("### Step 1: Add Customer")

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
                    "Notes": notes
                }

                st.session_state.clients_data.append(new_customer)
                st.session_state.current_customer = customer_name

                st.success("Customer saved! Next step: create a project.")

        st.markdown("### Step 2: Create First Project")

        with st.form("new_project_form"):
            project_name = st.text_input("Project Name")
            internal_ref = st.text_input("Internal Reference", placeholder="Example: CL-FJ4")
            project_status = st.selectbox("Status", ["active", "planning", "on-hold", "completed"])
            description = st.text_area("Project Description")

            project_submitted = st.form_submit_button("Save Project + Create Starter Tasks")

            if project_submitted:
                starter_tasks = [
                    {"Task": "Create customer quote", "Priority": "High", "Status": "Open", "Customer": st.session_state.current_customer, "Project": project_name},
                    {"Task": "Begin supplier sourcing", "Priority": "High", "Status": "Open", "Customer": st.session_state.current_customer, "Project": project_name},
                    {"Task": "Upload supplier PI", "Priority": "Medium", "Status": "Open", "Customer": st.session_state.current_customer, "Project": project_name},
                    {"Task": "Create engineering checklist", "Priority": "Medium", "Status": "Open", "Customer": st.session_state.current_customer, "Project": project_name},
                    {"Task": "Follow up with customer", "Priority": "Medium", "Status": "Open", "Customer": st.session_state.current_customer, "Project": project_name}
                ]

                st.session_state.starter_tasks.extend(starter_tasks)
                st.success("Project saved and starter tasks created!")

        st.markdown("### Step 3: Recommended Next Actions")

        if st.session_state.starter_tasks:
            st.dataframe(pd.DataFrame(st.session_state.starter_tasks), use_container_width=True)
        else:
            st.info("Starter tasks will appear here after you save a project.")

    elif workflow_type == "New Supplier":
        st.subheader("New Supplier Wizard")

        st.markdown("### Step 1: Add Supplier")

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
                    "Notes": notes
                }

                st.session_state.suppliers_data.append(new_supplier)
                st.success("Supplier saved! Next step: upload PI or link to project.")

        st.markdown("### Step 2: Recommended Next Actions")

        st.checkbox("Upload Supplier PI")
        st.checkbox("Link supplier to project")
        st.checkbox("Create purchase order")
        st.checkbox("Add sourcing task")

        if st.session_state.suppliers_data:
            st.markdown("### Saved Suppliers This Session")
            st.dataframe(pd.DataFrame(st.session_state.suppliers_data), use_container_width=True)

    elif workflow_type == "New Purchase Order":
        st.subheader("New Purchase Order Wizard")

        st.warning(
            "Privacy rule: customer/client names should NOT appear on supplier-facing PO documents."
        )

        st.markdown("### Step 1: PO Details")

        with st.form("new_po_form"):
            po_number = st.text_input("PO Number", placeholder="Example: WS-PO-2026-001")
            po_date = st.date_input("PO Date", value=date.today())
            supplier = st.text_input("Supplier Name")
            project = st.text_input("Project / Internal Reference", placeholder="Example: CL-FJ4")
            po_title = st.text_input("PO Title")
            incoterm = st.selectbox("Incoterm", ["FOB", "EXW", "CIF", "DDP", "Other"])
            payment_terms = st.text_area("Payment Terms")
            lead_time = st.text_input("Lead Time")
            notes = st.text_area(
                "Supplier-Facing Notes",
                placeholder="Do NOT include customer/client name here."
            )

            st.markdown("### Step 2: Line Item")
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
                    "Status": "Draft"
                }

                st.session_state.purchase_orders_data.append(new_po)
                save_purchase_orders()

                st.success("PO draft saved and stored!")

        st.markdown("### Saved PO Drafts")

        if st.session_state.purchase_orders_data:
            st.dataframe(pd.DataFrame(st.session_state.purchase_orders_data), use_container_width=True)
        else:
            st.info("No PO drafts created yet.")

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
        st.info("No clients added in this session yet.")

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
        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Download Purchase Orders CSV",
            data=csv,
            file_name="purchase_orders.csv",
            mime="text/csv"
        )

        st.markdown("### Generate PO PDF")

        po_options = [
            f"{po.get('PO Number', 'No PO Number')} — {po.get('Supplier', 'No Supplier')}"
            for po in st.session_state.purchase_orders_data
        ]

        selected_po_label = st.selectbox("Select PO", po_options)
        selected_index = po_options.index(selected_po_label)
        selected_po = st.session_state.purchase_orders_data[selected_index]

        pdf_file = generate_po_pdf(selected_po)

        st.download_button(
            label="Download Selected PO as PDF",
            data=pdf_file,
            file_name=f"{selected_po.get('PO Number', 'purchase_order')}.pdf",
            mime="application/pdf"
        )

    else:
        st.info("No purchase orders created yet.")

elif page == "Suppliers":
    st.header("Suppliers")

    if st.session_state.suppliers_data:
        st.dataframe(pd.DataFrame(st.session_state.suppliers_data), use_container_width=True)
    else:
        st.info("No suppliers added in this session yet.")