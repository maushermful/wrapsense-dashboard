import streamlit as st
import pandas as pd
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
# Login Function
# -----------------------------
def login_user(email, password):

    try:

        response = supabase.auth.sign_in_with_password(
            {
                "email": email,
                "password": password,
            }
        )

        if response.user:

            st.session_state.authenticated = True
            st.session_state.user_email = email

            return True

    except Exception as e:
        st.error(f"Login failed: {e}")

    return False

# -----------------------------
# Session State
# -----------------------------
if "clients_data" not in st.session_state:
    st.session_state.clients_data = []

if "starter_tasks" not in st.session_state:
    st.session_state.starter_tasks = []

if "current_customer" not in st.session_state:
    st.session_state.current_customer = ""

if "suppliers_data" not in st.session_state:
    st.session_state.suppliers_data = []

if "purchase_orders_data" not in st.session_state:
    st.session_state.purchase_orders_data = []

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "user_email" not in st.session_state:
    st.session_state.user_email = ""


# -----------------------------
# Demo Data
# -----------------------------
def load_data(query):
    po_count = len(load_purchase_orders_from_supabase())

    return pd.DataFrame(
        {
            "Project": ["FJ Pouch Line Project"],
            "Client": ["ForJars Canning Supply Inc."],
            "Status": ["Active"],
            "Tasks": [len(st.session_state.starter_tasks)],
            "Purchase Orders": [po_count],
            "Quotes": [1],
        }
    )


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
# Supabase Client Functions
# -----------------------------
def load_clients_from_supabase():
    response = supabase.table("clients").select("*").execute()
    return response.data


def add_client_to_supabase(client):
    return supabase.table("clients").insert(
        {
            "client_name": client.get("Customer Name", ""),
            "contact": client.get("Contact", ""),
            "email": client.get("Email", ""),
            "phone": client.get("Phone", ""),
            "notes": client.get("Notes", ""),
        }
    ).execute()
    
def delete_client_from_supabase(client_id):
    return supabase.table("clients").delete().eq("id", client_id).execute()

# -----------------------------
# Supabase Projects Functions
# -----------------------------
def load_projects_from_supabase():
    response = supabase.table("projects").select("*").execute()
    return response.data


def add_project_to_supabase(project):
    return supabase.table("projects").insert(
        {
            "project_name": project.get("Project Name", ""),
            "client_name": project.get("Client Name", ""),
            "internal_ref": project.get("Internal Reference", ""),
            "status": project.get("Status", "planning"),
            "description": project.get("Description", ""),
        }
    ).execute()


def delete_project_from_supabase(project_id):
    return supabase.table("projects").delete().eq("id", project_id).execute()

# -----------------------------
# Supabase Purchase Order Functions
# -----------------------------
def load_purchase_orders_from_supabase():
    response = supabase.table("purchase_orders").select("*").execute()

    purchase_orders = []

    for row in response.data:
        purchase_orders.append(
            {
                "id": row.get("id"),
                "PO Number": row.get("po_number", ""),
                "PO Date": row.get("po_date", ""),
                "Supplier": row.get("supplier", ""),
                "Project": row.get("project", ""),
                "Title": row.get("title", ""),
                "Incoterm": row.get("incoterm", ""),
                "Payment Terms": row.get("payment_terms", ""),
                "Lead Time": row.get("lead_time", ""),
                "Notes": row.get("notes", ""),
                "Item": row.get("item", ""),
                "Quantity": row.get("quantity", 0),
                "Unit Price": row.get("unit_price", 0),
                "Line Total": row.get("line_total", 0),
                "Status": row.get("status", "Draft"),
            }
        )

    return purchase_orders


def add_purchase_order_to_supabase(po):
    return supabase.table("purchase_orders").insert(
        {
            "po_number": po.get("PO Number", ""),
            "po_date": po.get("PO Date", None),
            "supplier": po.get("Supplier", ""),
            "project": po.get("Project", ""),
            "title": po.get("Title", ""),
            "incoterm": po.get("Incoterm", ""),
            "payment_terms": po.get("Payment Terms", ""),
            "lead_time": po.get("Lead Time", ""),
            "notes": po.get("Notes", ""),
            "item": po.get("Item", ""),
            "quantity": po.get("Quantity", 0),
            "unit_price": po.get("Unit Price", 0),
            "line_total": po.get("Line Total", 0),
            "status": po.get("Status", "Draft"),
        }
    ).execute()


def update_purchase_order_in_supabase(po):
    po_id = po.get("id")

    if not po_id:
        return None

    quantity = float(po.get("Quantity", 0) or 0)
    unit_price = float(po.get("Unit Price", 0) or 0)
    line_total = quantity * unit_price

    update_data = {
        "po_number": po.get("PO Number", ""),
        "po_date": po.get("PO Date", None),
        "supplier": po.get("Supplier", ""),
        "project": po.get("Project", ""),
        "title": po.get("Title", ""),
        "incoterm": po.get("Incoterm", ""),
        "payment_terms": po.get("Payment Terms", ""),
        "lead_time": po.get("Lead Time", ""),
        "notes": po.get("Notes", ""),
        "item": po.get("Item", ""),
        "quantity": quantity,
        "unit_price": unit_price,
        "line_total": line_total,
        "status": po.get("Status", "Draft"),
    }

    response = (
        supabase.table("purchase_orders")
        .update(update_data)
        .eq("id", po_id)
        .execute()
    )

    return response

# -----------------------------
# Supabase Tasks Functions
# -----------------------------
def load_tasks_from_supabase():
    response = supabase.table("tasks").select("*").execute()
    return response.data


def add_task_to_supabase(task):
    return supabase.table("tasks").insert(
        {
            "task": task.get("Task", ""),
            "priority": task.get("Priority", ""),
            "status": task.get("Status", "Open"),
            "customer": task.get("Customer", ""),
            "project": task.get("Project", ""),
        }
    ).execute()


def delete_task_from_supabase(task_id):
    return supabase.table("tasks").delete().eq("id", task_id).execute()

# -----------------------------
# Supabase Quote Functions
# -----------------------------

def load_quotes_from_supabase():
    response = supabase.table("quotes").select("*").execute()
    return response.data


def add_quote_to_supabase(quote):
    return supabase.table("quotes").insert(
        {
            "quote_number": quote.get("Quote Number", ""),
            "quote_date": quote.get("Quote Date", None),
            "client_name": quote.get("Client Name", ""),
            "project_name": quote.get("Project Name", ""),
            "title": quote.get("Title", ""),
            "description": quote.get("Description", ""),
            "item": quote.get("Item", ""),
            "quantity": quote.get("Quantity", 0),
            "unit_price": quote.get("Unit Price", 0),
            "line_total": quote.get("Line Total", 0),
            "status": quote.get("Status", "Draft"),
            "notes": quote.get("Notes", ""),
        }
    ).execute()


def update_quote_in_supabase(quote):
    quote_id = quote.get("id")

    if not quote_id:
        return None

    quantity = float(
        quote.get("Quantity", quote.get("quantity", 0)) or 0
    )

    unit_price = float(
        quote.get("Unit Price", quote.get("unit_price", 0)) or 0
    )

    line_total = quantity * unit_price

    update_data = {
        "quote_number": quote.get("Quote Number", quote.get("quote_number", "")),
        "quote_date": quote.get("Quote Date", quote.get("quote_date", None)),
        "client_name": quote.get("Client Name", quote.get("client_name", "")),
        "project_name": quote.get("Project Name", quote.get("project_name", "")),
        "title": quote.get("Title", quote.get("title", "")),
        "description": quote.get("Description", quote.get("description", "")),
        "item": quote.get("Item", quote.get("item", "")),
        "quantity": quantity,
        "unit_price": unit_price,
        "line_total": line_total,
        "status": quote.get("Status", quote.get("status", "Draft")),
        "notes": quote.get("Notes", quote.get("notes", "")),
    }

    return (
        supabase.table("quotes")
        .update(update_data)
        .eq("id", quote_id)
        .execute()
    )


def delete_quote_from_supabase(quote_id):
    return (
        supabase.table("quotes")
        .delete()
        .eq("id", quote_id)
        .execute()
    )

def update_quote_in_supabase(quote):
    quote_id = quote.get("id")

    if not quote_id:
        return None

    quantity = float(quote.get("quantity", 0) or 0)
    unit_price = float(quote.get("unit_price", 0) or 0)
    line_total = quantity * unit_price

    update_data = {
        "quote_number": quote.get("quote_number", ""),
        "quote_date": str(quote.get("quote_date", "")) if quote.get("quote_date") else None,
        "client_name": quote.get("client_name", ""),
        "project_name": quote.get("project_name", ""),
        "title": quote.get("title", ""),
        "description": quote.get("description", ""),
        "item": quote.get("item", ""),
        "quantity": quantity,
        "unit_price": unit_price,
        "line_total": line_total,
        "status": quote.get("status", "Draft"),
        "notes": quote.get("notes", ""),
    }

    return (
        supabase.table("quotes")
        .update(update_data)
        .eq("id", quote_id)
        .execute()
    )

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

def generate_quote_pdf(quote):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)

    width, height = letter
    y = height - 50

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, y, "Wrapsense Quote")

    y -= 35
    pdf.setFont("Helvetica", 10)
    pdf.drawString(50, y, f"Quote Number: {quote.get('quote_number', '')}")
    y -= 18
    pdf.drawString(50, y, f"Quote Date: {quote.get('quote_date', '')}")
    y -= 18
    pdf.drawString(50, y, f"Client: {quote.get('client_name', '')}")
    y -= 18
    pdf.drawString(50, y, f"Project: {quote.get('project_name', '')}")
    y -= 18
    pdf.drawString(50, y, f"Title: {quote.get('title', '')}")
    y -= 18
    pdf.drawString(50, y, f"Status: {quote.get('status', '')}")

    y -= 35
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Description")

    y -= 18
    pdf.setFont("Helvetica", 10)
    description = str(quote.get("description", ""))
    pdf.drawString(50, y, description[:90])

    y -= 35
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Line Item")

    y -= 22
    pdf.setFont("Helvetica", 10)
    pdf.drawString(50, y, f"Item: {quote.get('item', '')}")
    y -= 18
    pdf.drawString(50, y, f"Quantity: {quote.get('quantity', '')}")
    y -= 18
    pdf.drawString(50, y, f"Unit Price: ${quote.get('unit_price', '')}")
    y -= 18
    pdf.drawString(50, y, f"Line Total: ${quote.get('line_total', '')}")

    y -= 35
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Notes")

    y -= 18
    pdf.setFont("Helvetica", 10)
    notes = str(quote.get("notes", ""))
    pdf.drawString(50, y, notes[:90])

    pdf.save()
    buffer.seek(0)
    return buffer
    
# -----------------------------
# Authentication Gate
# -----------------------------
if not st.session_state.authenticated:

    st.title("Wrapsense Login")

    with st.form("login_form"):

        login_email = st.text_input("Email")

        login_password = st.text_input(
            "Password",
            type="password"
        )

        login_submitted = st.form_submit_button("Login")

        if login_submitted:

            success = login_user(
                login_email,
                login_password
            )

            if success:
                st.success("Login successful!")
                st.rerun()

            else:
                st.error("Invalid email or password.")

    st.stop()
    
# -----------------------------
# User Roles
# -----------------------------
ADMIN_EMAILS = [
    "mausherm@gmail.com",
]

MANAGER_EMAILS = [
    "chris@wrapsensepackaging.com",
]


def get_user_role():

    email = st.session_state.get(
        "user_email",
        ""
    ).lower()

    if email in [
        admin.lower() for admin in ADMIN_EMAILS
    ]:
        return "admin"

    if email in [
        manager.lower() for manager in MANAGER_EMAILS
    ]:
        return "manager"

    return "viewer"


user_role = get_user_role()

# -----------------------------
# Header + Sidebar
# -----------------------------

st.title("Wrapsense Operations Dashboard")

st.sidebar.title("Navigation")

st.sidebar.markdown(
    f"Logged in as: {st.session_state.get('user_email', '')}"
)

st.sidebar.markdown(
    f"Role: {user_role.title()}"
)

if st.sidebar.button("Logout"):

    st.session_state.authenticated = False
    st.session_state.user_email = ""

    st.rerun()

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
            "New Task",
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

                add_client_to_supabase(new_customer)

                st.session_state.clients_data = load_clients_from_supabase()
                st.session_state.current_customer = customer_name

                st.success("Customer saved to Supabase!")

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

                add_purchase_order_to_supabase(new_po)
                st.session_state.purchase_orders_data = (
                    load_purchase_orders_from_supabase()
                )

                st.success("PO draft saved to Supabase!")
    elif workflow_type == "New Project":
        st.subheader("New Project Wizard")

        with st.form("new_project_form"):

            project_name = st.text_input("Project Name")

            client_name = st.text_input("Client Name")

            internal_ref = st.text_input(
                "Internal Reference",
                placeholder="Example: CL-FJ4",
            )

            status = st.selectbox(
                "Status",
                ["planning", "active", "on-hold", "completed"],
            )

            description = st.text_area(
                "Project Description"
            )

            submitted = st.form_submit_button(
                "Save Project"
            )

            if submitted:

                new_project = {
                    "Project Name": project_name,
                    "Client Name": client_name,
                    "Internal Reference": internal_ref,
                    "Status": status,
                    "Description": description,
                }

                add_project_to_supabase(
                    new_project
                )

                st.success(
                    "Project saved to Supabase!"
                )
    elif workflow_type == "New Task":
        st.subheader("New Task Wizard")

        with st.form("new_task_form"):
            task = st.text_input("Task")
            priority = st.selectbox(
                "Priority",
                ["Low", "Medium", "High"],
            )
            status = st.selectbox(
                "Status",
                ["Open", "In Progress", "Completed"],
            )
            customer = st.text_input("Customer / Client")
            project = st.text_input("Project")

            submitted = st.form_submit_button("Save Task")

            if submitted:
                new_task = {
                    "Task": task,
                    "Priority": priority,
                    "Status": status,
                    "Customer": customer,
                    "Project": project,
                }

                add_task_to_supabase(new_task)

                st.success("Task saved to Supabase!")
                
    elif workflow_type == "New Quote":
        st.subheader("New Quote Wizard")

        with st.form("new_quote_form"):

            quote_number = st.text_input(
                "Quote Number"
            )

            quote_date = st.date_input(
                "Quote Date"
            )

            client_name = st.text_input(
                "Client Name"
            )

            project_name = st.text_input(
                "Project Name"
            )

            title = st.text_input(
                "Quote Title"
            )

            description = st.text_area(
                "Description"
            )

            item = st.text_input(
                "Item"
            )

            quantity = st.number_input(
                "Quantity",
                min_value=0.0,
                step=1.0,
            )

            unit_price = st.number_input(
                "Unit Price",
                min_value=0.0,
                step=1.0,
            )

            line_total = quantity * unit_price

            st.metric(
                "Line Total",
                f"${line_total:,.2f}"
            )

            status = st.selectbox(
                "Status",
                [
                    "Draft",
                    "Sent",
                    "Approved",
                    "Rejected",
                ],
            )

            notes = st.text_area(
                "Notes"
            )

            submitted = st.form_submit_button(
                "Save Quote"
            )

            if submitted:

                new_quote = {
                    "Quote Number": quote_number,
                    "Quote Date": str(quote_date),
                    "Client Name": client_name,
                    "Project Name": project_name,
                    "Title": title,
                    "Description": description,
                    "Item": item,
                    "Quantity": quantity,
                    "Unit Price": unit_price,
                    "Line Total": line_total,
                    "Status": status,
                    "Notes": notes,
                }

                add_quote_to_supabase(
                    new_quote
                )

                st.success(
                    "Quote saved to Supabase!"
                )
                

elif page == "Clients":
    st.header("Clients")

    st.session_state.clients_data = load_clients_from_supabase()

    if st.session_state.clients_data:
        df = pd.DataFrame(st.session_state.clients_data)

        st.markdown("### Clients Overview")

        st.caption(
            "This table is view-only. "
            "To make changes, use the "
            "Edit Client form below."
        )

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )

        csv = df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Download Clients CSV",
            data=csv,
            file_name="clients.csv",
            mime="text/csv",
        )

        st.markdown("---")
        st.markdown("### Edit Client")

        st.info(
            "Select a client below, make changes in this form, "
            "then click 'Save Client Changes'. "
            "Edits made directly in the overview table will not save."
        )

        client_options = [
            f"{client.get('client_name', 'No Client')} — "
            f"{client.get('email', 'No Email')}"
            for client in st.session_state.clients_data
        ]

        selected_client_label = st.selectbox(
            "Select Client",
            client_options,
            key="edit_client_select",
        )

        selected_client_index = client_options.index(selected_client_label)
        selected_client = st.session_state.clients_data[selected_client_index]

        with st.form("edit_client_form"):
            client_name = st.text_input(
                "Client Name",
                value=selected_client.get("client_name", ""),
            )

            contact = st.text_input(
                "Contact",
                value=selected_client.get("contact", ""),
            )

            email = st.text_input(
                "Email",
                value=selected_client.get("email", ""),
            )

            phone = st.text_input(
                "Phone",
                value=selected_client.get("phone", ""),
            )

            notes = st.text_area(
                "Notes",
                value=selected_client.get("notes", ""),
            )

            save_client = st.form_submit_button("Save Client Changes")

        if save_client:
            supabase.table("clients").update(
                {
                    "client_name": client_name,
                    "contact": contact,
                    "email": email,
                    "phone": phone,
                    "notes": notes,
                }
            ).eq(
                "id",
                selected_client["id"],
            ).execute()

            st.success("Client updated successfully!")
            st.rerun()

        if user_role in ["admin", "manager"]:
            st.markdown("---")
            st.markdown("## Delete Client")

            delete_client_label = st.selectbox(
                "Select Client to Delete",
                client_options,
                key="delete_client_select",
            )

            delete_client_index = client_options.index(delete_client_label)
            selected_delete_client = st.session_state.clients_data[
                delete_client_index
            ]

            confirm_delete_client = st.checkbox(
                "I understand this client will be permanently deleted."
            )

            if st.button("Delete Selected Client"):
                if confirm_delete_client:
                    delete_client_from_supabase(selected_delete_client["id"])

                    st.success(
                        f"Client {selected_delete_client.get('client_name')} deleted successfully."
                    )

                    st.rerun()
                else:
                    st.warning("Please confirm deletion before removing the client.")

        else:
            st.info("You do not have permission to delete clients.")

    else:
        st.info("No clients added yet.")

elif page == "Projects":
    st.header("Projects")

    projects_data = load_projects_from_supabase()

    if projects_data:
        df = pd.DataFrame(projects_data)

        st.markdown("### Projects Overview")

        st.caption(
            "This table is view-only. "
            "To make changes, use the Edit Project form below."
        )

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )

        csv = df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Download Projects CSV",
            data=csv,
            file_name="projects.csv",
            mime="text/csv",
        )

        st.markdown("---")
        st.markdown("### Edit Project")

        st.info(
            "Select a project below, make changes in this form, "
            "then click 'Save Project Changes'. "
            "Edits made directly in the overview table will not save."
        )

        project_options = [
            f"{project.get('project_name', 'No Project')} — "
            f"{project.get('client_name', 'No Client')}"
            for project in projects_data
        ]

        selected_project_label = st.selectbox(
            "Select Project",
            project_options,
            key="edit_project_select",
        )

        selected_project_index = project_options.index(selected_project_label)
        selected_project = projects_data[selected_project_index]

        with st.form("edit_project_form"):
            project_name = st.text_input(
                "Project Name",
                value=selected_project.get("project_name", ""),
            )

            client_name = st.text_input(
                "Client Name",
                value=selected_project.get("client_name", ""),
            )

            internal_ref = st.text_input(
                "Internal Reference",
                value=selected_project.get("internal_ref", ""),
            )

            status_options = [
                "planning",
                "active",
                "on-hold",
                "completed",
            ]

            current_status = selected_project.get("status", "planning")

            status = st.selectbox(
                "Status",
                status_options,
                index=status_options.index(current_status)
                if current_status in status_options
                else 0,
            )

            description = st.text_area(
                "Description",
                value=selected_project.get("description", ""),
            )

            save_project = st.form_submit_button("Save Project Changes")

        if save_project:
            supabase.table("projects").update(
                {
                    "project_name": project_name,
                    "client_name": client_name,
                    "internal_ref": internal_ref,
                    "status": status,
                    "description": description,
                }
            ).eq(
                "id",
                selected_project["id"],
            ).execute()

            st.success("Project updated successfully!")
            st.rerun()

        if user_role in ["admin", "manager"]:
            st.markdown("---")
            st.markdown("## Delete Project")

            delete_project_label = st.selectbox(
                "Select Project to Delete",
                project_options,
                key="delete_project_select",
            )

            delete_project_index = project_options.index(delete_project_label)
            selected_delete_project = projects_data[delete_project_index]

            confirm_delete_project = st.checkbox(
                "I understand this project will be permanently deleted."
            )

            if st.button("Delete Selected Project"):
                if confirm_delete_project:
                    delete_project_from_supabase(selected_delete_project["id"])

                    st.success(
                        f"Project {selected_delete_project.get('project_name')} deleted successfully."
                    )

                    st.rerun()
                else:
                    st.warning("Please confirm deletion before removing the project.")

        else:
            st.info("You do not have permission to delete projects.")

    else:
        st.info("No projects added yet.")

elif page == "Tasks":
    st.header("Tasks")

    tasks_data = load_tasks_from_supabase()

    if tasks_data:
        df = pd.DataFrame(tasks_data)

        st.markdown("### Tasks Overview")

        st.caption(
            "This table is view-only. "
            "To make changes, use the Edit Task form below."
        )

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )

        csv = df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Download Tasks CSV",
            data=csv,
            file_name="tasks.csv",
            mime="text/csv",
        )

        st.markdown("---")
        st.markdown("### Edit Task")

        st.info(
            "Select a task below, make changes in this form, "
            "then click 'Save Task Changes'. "
            "Edits made directly in the overview table will not save."
        )

        task_options = [
            f"{task.get('task', 'No Task')} — "
            f"{task.get('project', 'No Project')}"
            for task in tasks_data
        ]

        selected_task_label = st.selectbox(
            "Select Task",
            task_options,
            key="edit_task_select",
        )

        selected_task_index = task_options.index(selected_task_label)
        selected_task = tasks_data[selected_task_index]

        with st.form("edit_task_form"):
            task_name = st.text_input(
                "Task",
                value=selected_task.get("task", ""),
            )

            priority_options = ["Low", "Medium", "High"]
            current_priority = selected_task.get("priority", "Medium")

            priority = st.selectbox(
                "Priority",
                priority_options,
                index=priority_options.index(current_priority)
                if current_priority in priority_options
                else 1,
            )

            status_options = ["Open", "In Progress", "Completed"]
            current_status = selected_task.get("status", "Open")

            status = st.selectbox(
                "Status",
                status_options,
                index=status_options.index(current_status)
                if current_status in status_options
                else 0,
            )

            customer = st.text_input(
                "Customer / Client",
                value=selected_task.get("customer", ""),
            )

            project = st.text_input(
                "Project",
                value=selected_task.get("project", ""),
            )

            save_task = st.form_submit_button("Save Task Changes")

        if save_task:
            supabase.table("tasks").update(
                {
                    "task": task_name,
                    "priority": priority,
                    "status": status,
                    "customer": customer,
                    "project": project,
                }
            ).eq(
                "id",
                selected_task["id"],
            ).execute()

            st.success("Task updated successfully!")
            st.rerun()

        if user_role in ["admin", "manager"]:
            st.markdown("---")
            st.markdown("## Delete Task")

            delete_task_label = st.selectbox(
                "Select Task to Delete",
                task_options,
                key="delete_task_select",
            )

            delete_task_index = task_options.index(delete_task_label)
            selected_delete_task = tasks_data[delete_task_index]

            confirm_delete_task = st.checkbox(
                "I understand this task will be permanently deleted."
            )

            if st.button("Delete Selected Task"):
                if confirm_delete_task:
                    delete_task_from_supabase(selected_delete_task["id"])

                    st.success(
                        f"Task {selected_delete_task.get('task')} deleted successfully."
                    )

                    st.rerun()
                else:
                    st.warning("Please confirm deletion before removing the task.")

        else:
            st.info("You do not have permission to delete tasks.")

    else:
        st.info("No tasks added yet.")


elif page == "Quotes":
    st.header("Quotes")

    quotes_data = load_quotes_from_supabase()

    if quotes_data:
        df = pd.DataFrame(quotes_data)

        st.markdown("### Quotes Overview")

        st.caption(
            "This table is view-only. "
            "To make changes, use the "
            "Edit Quote form below."
        )

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )

        csv = df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Download Quotes CSV",
            data=csv,
            file_name="quotes.csv",
            mime="text/csv",
        )

        st.markdown("---")
        st.markdown("### Edit Quote")

        st.info(
            "Select a quote below, make changes in this form, "
            "then click 'Save Quote Changes'. "
            "Edits made directly in the overview table will not save."
        )

        quote_options = [
            f"{quote.get('quote_number', 'No Quote')} — "
            f"{quote.get('client_name', 'No Client')}"
            for quote in quotes_data
        ]

        selected_quote_label = st.selectbox(
            "Select Quote",
            quote_options,
            key="edit_quote_select",
        )

        selected_quote_index = quote_options.index(selected_quote_label)
        selected_quote = quotes_data[selected_quote_index]

        with st.form("edit_quote_form"):
            quote_number = st.text_input(
                "Quote Number",
                value=selected_quote.get("quote_number", ""),
            )

            quote_date = st.text_input(
                "Quote Date",
                value=str(selected_quote.get("quote_date", "")),
            )

            client_name = st.text_input(
                "Client Name",
                value=selected_quote.get("client_name", ""),
            )

            project_name = st.text_input(
                "Project Name",
                value=selected_quote.get("project_name", ""),
            )

            title = st.text_input(
                "Title",
                value=selected_quote.get("title", ""),
            )

            description = st.text_area(
                "Description",
                value=selected_quote.get("description", ""),
            )

            item = st.text_input(
                "Item",
                value=selected_quote.get("item", ""),
            )

            quantity = st.number_input(
                "Quantity",
                min_value=0.0,
                value=float(selected_quote.get("quantity", 0) or 0),
            )

            unit_price = st.number_input(
                "Unit Price",
                min_value=0.0,
                value=float(selected_quote.get("unit_price", 0) or 0),
            )

            line_total = quantity * unit_price

            st.metric(
                "Line Total",
                f"${line_total:,.2f}",
            )

            status_options = [
                "Draft",
                "Sent",
                "Approved",
                "Rejected",
            ]

            current_status = selected_quote.get("status", "Draft")

            status = st.selectbox(
                "Status",
                status_options,
                index=status_options.index(current_status)
                if current_status in status_options
                else 0,
            )

            notes = st.text_area(
                "Notes",
                value=selected_quote.get("notes", ""),
            )

            save_quote = st.form_submit_button("Save Quote Changes")

        if save_quote:
            supabase.table("quotes").update(
                {
                    "quote_number": quote_number,
                    "quote_date": quote_date if quote_date else None,
                    "client_name": client_name,
                    "project_name": project_name,
                    "title": title,
                    "description": description,
                    "item": item,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "line_total": line_total,
                    "status": status,
                    "notes": notes,
                }
            ).eq(
                "id",
                selected_quote["id"],
            ).execute()

            st.success("Quote updated successfully!")
            st.rerun()

        st.markdown("---")
        st.markdown("### Generate Quote PDF")

        quote_pdf = generate_quote_pdf(
            {
                "quote_number": selected_quote.get("quote_number", ""),
                "quote_date": selected_quote.get("quote_date", ""),
                "client_name": selected_quote.get("client_name", ""),
                "project_name": selected_quote.get("project_name", ""),
                "title": selected_quote.get("title", ""),
                "description": selected_quote.get("description", ""),
                "item": selected_quote.get("item", ""),
                "quantity": selected_quote.get("quantity", ""),
                "unit_price": selected_quote.get("unit_price", ""),
                "line_total": selected_quote.get("line_total", ""),
                "status": selected_quote.get("status", ""),
                "notes": selected_quote.get("notes", ""),
            }
        )

        st.download_button(
            label="Download Selected Quote as PDF",
            data=quote_pdf,
            file_name=f"{selected_quote.get('quote_number', 'quote')}.pdf",
            mime="application/pdf",
        )

        if user_role in ["admin", "manager"]:
            st.markdown("---")
            st.markdown("## Delete Quote")

            delete_quote_label = st.selectbox(
                "Select Quote to Delete",
                quote_options,
                key="delete_quote_select",
            )

            delete_quote_index = quote_options.index(delete_quote_label)
            selected_delete_quote = quotes_data[delete_quote_index]

            confirm_delete_quote = st.checkbox(
                "I understand this quote will be permanently deleted."
            )

            if st.button("Delete Selected Quote"):
                if confirm_delete_quote:
                    delete_quote_from_supabase(selected_delete_quote["id"])

                    st.success(
                        f"Quote {selected_delete_quote.get('quote_number')} deleted successfully."
                    )

                    st.rerun()
                else:
                    st.warning("Please confirm deletion before removing the quote.")

        else:
            st.info("You do not have permission to delete quotes.")

    else:
        st.info("No quotes added yet.")

elif page == "Purchase Orders":
    st.header("Purchase Orders")

    st.session_state.purchase_orders_data = (
        load_purchase_orders_from_supabase()
    )

    if st.session_state.purchase_orders_data:

        df = pd.DataFrame(
            st.session_state.purchase_orders_data
        )

        st.markdown(
            "### Purchase Orders Overview"
        )

        st.caption(
            "This table is view-only. "
            "To make changes, use the "
            "Edit Purchase Order form below."
        )

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )

        csv = (
            df.to_csv(index=False)
            .encode("utf-8")
        )
        st.download_button(
            label="Download Purchase Orders CSV",
            data=csv,
            file_name="purchase_orders.csv",
            mime="text/csv",
        )

        st.markdown("---")

        st.markdown(
            "### Edit Purchase Order"
        )

        st.info(
            "Select a purchase order below, "
            "make changes in this form, then click "
            "'Save Purchase Order Changes'. "
            "Edits made directly in the overview table "
            "will not save."
        )

        po_options = [
            f"{po.get('PO Number', 'No PO')} — "
            f"{po.get('Supplier', 'No Supplier')}"
            for po in (
                st.session_state.purchase_orders_data
            )
        ]

        selected_po_label = st.selectbox(
            "Select Purchase Order",
            po_options,
            key="edit_po_select",
        )

        selected_po_index = po_options.index(selected_po_label)
        selected_po = st.session_state.purchase_orders_data[selected_po_index]

        with st.form("edit_po_form"):
            po_number = st.text_input(
                "PO Number",
                value=selected_po.get("PO Number", ""),
            )

            supplier = st.text_input(
                "Supplier",
                value=selected_po.get("Supplier", ""),
            )

            project = st.text_input(
                "Project",
                value=selected_po.get("Project", ""),
            )

            title = st.text_input(
                "Title",
                value=selected_po.get("Title", ""),
            )

            incoterm = st.text_input(
                "Incoterm",
                value=selected_po.get("Incoterm", ""),
            )

            payment_terms = st.text_area(
                "Payment Terms",
                value=selected_po.get("Payment Terms", ""),
            )

            lead_time = st.text_input(
                "Lead Time",
                value=selected_po.get("Lead Time", ""),
            )

            notes = st.text_area(
                "Notes",
                value=selected_po.get("Notes", ""),
            )

            item = st.text_input(
                "Item",
                value=selected_po.get("Item", ""),
            )

            quantity = st.number_input(
                "Quantity",
                min_value=0.0,
                value=float(selected_po.get("Quantity", 0) or 0),
            )

            unit_price = st.number_input(
                "Unit Price",
                min_value=0.0,
                value=float(selected_po.get("Unit Price", 0) or 0),
            )

            line_total = quantity * unit_price

            st.metric(
                "Line Total",
                f"${line_total:,.2f}",
            )

            status_options = [
                "Draft",
                "Sent",
                "Approved",
                "Completed",
            ]

            current_status = selected_po.get("Status", "Draft")

            status = st.selectbox(
                "Status",
                status_options,
                index=status_options.index(current_status)
                if current_status in status_options
                else 0,
            )

            save_po = st.form_submit_button(
                "Save Purchase Order Changes"
            )

        if save_po:
            supabase.table("purchase_orders").update(
                {
                    "po_number": po_number,
                    "supplier": supplier,
                    "project": project,
                    "title": title,
                    "incoterm": incoterm,
                    "payment_terms": payment_terms,
                    "lead_time": lead_time,
                    "notes": notes,
                    "item": item,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "line_total": line_total,
                    "status": status,
                }
            ).eq(
                "id",
                selected_po["id"],
            ).execute()

            st.success("Purchase order updated successfully!")
            st.rerun()

        st.markdown("---")
        st.markdown("### Generate PO PDF")

        pdf_file = generate_po_pdf(
            {
                "PO Number": selected_po.get("PO Number", ""),
                "PO Date": selected_po.get("PO Date", ""),
                "Supplier": selected_po.get("Supplier", ""),
                "Project": selected_po.get("Project", ""),
                "Title": selected_po.get("Title", ""),
                "Incoterm": selected_po.get("Incoterm", ""),
                "Payment Terms": selected_po.get("Payment Terms", ""),
                "Lead Time": selected_po.get("Lead Time", ""),
                "Notes": selected_po.get("Notes", ""),
                "Item": selected_po.get("Item", ""),
                "Quantity": selected_po.get("Quantity", ""),
                "Unit Price": selected_po.get("Unit Price", ""),
                "Line Total": selected_po.get("Line Total", ""),
                "Status": selected_po.get("Status", ""),
            }
        )

        st.download_button(
            label="Download Selected PO as PDF",
            data=pdf_file,
            file_name=f"{selected_po.get('PO Number', 'purchase_order')}.pdf",
            mime="application/pdf",
        )

        if user_role in ["admin", "manager"]:
            st.markdown("---")
            st.markdown("## Delete Purchase Order")

            delete_po_label = st.selectbox(
                "Select PO to Delete",
                po_options,
                key="delete_po_select",
            )

            delete_index = po_options.index(delete_po_label)
            selected_delete_po = st.session_state.purchase_orders_data[
                delete_index
            ]

            confirm_delete = st.checkbox(
                "I understand this action cannot be undone."
            )

            if st.button("Delete Selected Purchase Order"):
                if confirm_delete:
                    delete_purchase_order_from_supabase(
                        selected_delete_po["id"]
                    )

                    st.success(
                        f"Purchase Order "
                        f"{selected_delete_po.get('PO Number')} "
                        f"deleted successfully."
                    )

                    st.rerun()
                else:
                    st.warning(
                        "Please confirm deletion before removing "
                        "the purchase order."
                    )

        else:
            st.info(
                "You do not have permission to delete purchase orders."
            )

    else:
        st.info("No purchase orders created yet.")

elif page == "Suppliers":
    st.header("Suppliers")

    st.session_state.suppliers_data = load_suppliers_from_supabase()

    if st.session_state.suppliers_data:
        df = pd.DataFrame(st.session_state.suppliers_data)

        st.markdown("### Suppliers Overview")

        st.caption(
            "This table is view-only. "
            "To make changes, use the Edit Supplier form below."
        )

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )

        csv = df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Download Suppliers CSV",
            data=csv,
            file_name="suppliers.csv",
            mime="text/csv",
        )

        st.markdown("---")
        st.markdown("### Edit Supplier")

        st.info(
            "Select a supplier below, make changes in this form, "
            "then click 'Save Supplier Changes'. "
            "Edits made directly in the overview table will not save."
        )

        supplier_options = [
            f"{supplier.get('supplier', 'No Supplier')} — "
            f"{supplier.get('country', 'No Country')}"
            for supplier in st.session_state.suppliers_data
        ]

        selected_supplier_label = st.selectbox(
            "Select Supplier",
            supplier_options,
            key="edit_supplier_select",
        )

        selected_supplier_index = supplier_options.index(selected_supplier_label)
        selected_supplier = st.session_state.suppliers_data[selected_supplier_index]

        with st.form("edit_supplier_form"):
            supplier_name = st.text_input(
                "Supplier Name",
                value=selected_supplier.get("supplier", ""),
            )

            country = st.text_input(
                "Country",
                value=selected_supplier.get("country", ""),
            )

            specialty = st.text_input(
                "Specialty",
                value=selected_supplier.get("specialty", ""),
            )

            contact = st.text_input(
                "Contact",
                value=selected_supplier.get("contact", ""),
            )

            email = st.text_input(
                "Email",
                value=selected_supplier.get("email", ""),
            )

            notes = st.text_area(
                "Notes",
                value=selected_supplier.get("notes", ""),
            )

            save_supplier = st.form_submit_button("Save Supplier Changes")

        if save_supplier:
            supabase.table("suppliers").update(
                {
                    "supplier": supplier_name,
                    "country": country,
                    "specialty": specialty,
                    "contact": contact,
                    "email": email,
                    "notes": notes,
                }
            ).eq(
                "id",
                selected_supplier["id"],
            ).execute()

            st.success("Supplier updated successfully!")
            st.rerun()

        if user_role in ["admin", "manager"]:
            st.markdown("---")
            st.markdown("## Delete Supplier")

            delete_supplier_label = st.selectbox(
                "Select Supplier to Delete",
                supplier_options,
                key="delete_supplier_select",
            )

            delete_supplier_index = supplier_options.index(delete_supplier_label)
            selected_delete_supplier = st.session_state.suppliers_data[
                delete_supplier_index
            ]

            confirm_delete_supplier = st.checkbox(
                "I understand this supplier will be permanently deleted."
            )

            if st.button("Delete Selected Supplier"):
                if confirm_delete_supplier:
                    delete_supplier_from_supabase(selected_delete_supplier["id"])

                    st.success(
                        f"Supplier {selected_delete_supplier.get('supplier')} deleted successfully."
                    )

                    st.rerun()
                else:
                    st.warning("Please confirm deletion before removing the supplier.")

        else:
            st.info("You do not have permission to delete suppliers.")

    else:
        st.info("No suppliers added yet.")