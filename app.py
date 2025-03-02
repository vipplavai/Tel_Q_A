import streamlit as st
from db import collection

st.title("✅ MongoDB Connection Test")

# Test connection
try:
    # Fetch some data from the collection
    sample_data = collection.find_one()

    if sample_data:
        st.success("🎉 Successfully connected to MongoDB!")
        st.write("🔹 **Sample Data from MongoDB:**")
        st.json(sample_data)  # Display first document
    else:
        st.warning("⚠️ Connected, but no data found in the collection.")

except Exception as e:
    st.error(f"❌ Connection failed: {e}")
