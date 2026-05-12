import streamlit as st
import mysql.connector
import pandas as pd

st.set_page_config(page_title="Wrapsense Dashboard", layout="wide")

st.title("Wrapsense Operations Dashboard")

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Phish92?",
    database="client_dashboard"
)

def load_data(query):
    df = pd.read_sql(query, conn)
    df.columns = [col.replace("_", " ").title() for col in df.columns]
    return df

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to",
    ["Dashboard", "Clients", "Projects", "Tasks", "Quotes", "Purchase Orders", "Suppliers"]
)

# Pages
if page == "Dashboard":
    st.header("Project Dashboard")
    df = load_data("SELECT * FROM project_dashboard;")
    st.dataframe(df, use_container_width=True)

elif page == "Clients":
    st.header("Clients")
    df = load_data("SELECT * FROM clients;")
    st.dataframe(df, use_container_width=True)

elif page == "Projects":
    st.header("Projects")
    df = load_data("SELECT * FROM projects;")
    st.dataframe(df, use_container_width=True)

elif page == "Tasks":
    st.header("Open Tasks")
    df = load_data("SELECT * FROM open_tasks_dashboard;")
    st.dataframe(df, use_container_width=True)

elif page == "Quotes":
    st.header("Quotes")
    df = load_data("SELECT * FROM quote_dashboard;")
    st.dataframe(df, use_container_width=True)

elif page == "Purchase Orders":
    st.header("Purchase Orders")
    df = load_data("SELECT * FROM po_dashboard;")
    st.dataframe(df, use_container_width=True)

elif page == "Suppliers":
    st.header("Suppliers")
    df = load_data("SELECT * FROM suppliers;")
    st.dataframe(df, use_container_width=True)