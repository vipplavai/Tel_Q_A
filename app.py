import streamlit as st
from pymongo import MongoClient

# Initialize connection to MongoDB
@st.cache_resource
def init_connection():
    return MongoClient(st.secrets["mongo"]["uri"])

client = init_connection()
db = client["Q_and_A"]  # Database Name
collection = db["content_data"]  # Collection Name

# Streamlit UI
st.title("📖 Fetch Content from MongoDB")

st.subheader("🔍 Enter Content ID to Fetch Content")
content_id_input = st.text_input("Enter Content ID (e.g., 000001):")

if st.button("Fetch Content"):
    content_data = collection.find_one({"content_id": content_id_input})

    if content_data:
        st.subheader("📜 Retrieved Content")
        st.text_area("Content:", value=content_data["content"], height=300, disabled=True)
    else:
        st.error("❌ No content found for this ID!")
