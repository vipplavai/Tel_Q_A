import pymongo
import streamlit as st
from pymongo.server_api import ServerApi

# Secure MongoDB connection using Streamlit Secrets
@st.cache_resource
def init_connection():
    return pymongo.MongoClient(st.secrets["mongo"]["uri"], server_api=ServerApi('1'))

# Initialize DB connection
client = init_connection()
db = client["Q_and_A"]  # Your database name
collection = db["content_data"]  # Your collection name
