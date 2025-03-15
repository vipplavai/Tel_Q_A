import streamlit as st
from users import register_user, authenticate_user, login_user, logout_user, is_authenticated
from content_manager import content_management

st.title("🔒 User Authentication")

if not is_authenticated():
    option = st.radio("Choose an option:", ["Login", "Register"])
    if option == "Login":
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            success, message = authenticate_user(username, password)
            if success:
                login_user(username)
                st.experimental_rerun()
            else:
                st.error(message)
    else:
        new_username = st.text_input("New Username")
        new_password = st.text_input("New Password", type="password")
        if st.button("Register"):
            success, message = register_user(new_username, new_password)
            st.success(message) if success else st.error(message)
else:
    content_management()
