import pymongo
import streamlit as st

# Secure MongoDB connection using Streamlit Secrets
@st.cache_resource
def init_connection():
    return pymongo.MongoClient(st.secrets["mongo"]["uri"])

# Initialize DB connection
client = init_connection()
db = client["Q_and_A"]  # Database name
collection = db["content_data"]  # Collection name
