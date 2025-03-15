import streamlit as st
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash

# ------------------------------------------------------------------------------
# 1) MongoDB CONNECTION INITIALIZATION
# ------------------------------------------------------------------------------
@st.cache_resource
def init_connection():
    return MongoClient(st.secrets["mongo"]["uri"])

client = init_connection()
db = client["Q_and_A"]
users_collection = db["users"]  # Collection for user accounts

# ------------------------------------------------------------------------------
# 2) REGISTER A NEW USER
# ------------------------------------------------------------------------------
def register_user(username, password):
    """Registers a new user by hashing the password and storing it in MongoDB."""
    existing_user = users_collection.find_one({"username": username})
    if existing_user:
        return False, "❌ Username already exists."

    hashed_password = generate_password_hash(password)  # Hash password
    users_collection.insert_one({"username": username, "password": hashed_password})
    return True, "✅ Registration successful! Please log in."

# ------------------------------------------------------------------------------
# 3) USER LOGIN VERIFICATION
# ------------------------------------------------------------------------------
def authenticate_user(username, password):
    """Authenticates a user by checking hashed passwords."""
    user = users_collection.find_one({"username": username})
    if not user or not check_password_hash(user["password"], password):
        return False, "❌ Invalid username or password."

    return True, "✅ Login successful!"

# ------------------------------------------------------------------------------
# 4) SESSION MANAGEMENT
# ------------------------------------------------------------------------------
def is_authenticated():
    """Check if a user is logged in by verifying session state."""
    return "authenticated_user" in st.session_state

def login_user(username):
    """Save logged-in user to session state."""
    st.session_state["authenticated_user"] = username

def logout_user():
    """Clear session and log out user."""
    st.session_state.pop("authenticated_user", None)
