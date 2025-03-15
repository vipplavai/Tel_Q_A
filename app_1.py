import streamlit as st
from pymongo import MongoClient
import bcrypt
from datetime import datetime

# ------------------------------------------------------------------------------
# 1) LANGUAGE SUPPORT (English & Telugu)
# ------------------------------------------------------------------------------
LANG_TEXT = {
    "English": {
        "app_title": "📖 Question Inserter Tool @vipplavAI",
        "login_label": "Login",
        "register_label": "Register",
        "new_username": "New Username:",
        "new_password": "New Password:",
        "register_btn": "Register",
        "login_username": "Username:",
        "login_password": "Password:",
        "login_btn": "Login",
        "search_id": "Search content_id:",
        "search_btn": "Search",
        "content_id_retrieved": "📜 Retrieved Content (ID: {content_id})",
        "content_box_label": "Content:",
        "total_questions": "📌 **Total Questions:** {count}",
        "add_new_question_subheader": "📝 Add a New Question",
        "fetch_next_btn": "Fetch Next Content",
        "instructions_btn": "Instructions"
    },
    "Telugu": {
        "app_title": "📖 ప్రశ్న ఇన్సర్టర్ సాధనం @vipplavAI",
        "login_label": "లాగిన్",
        "register_label": "రిజిస్టర్",
        "new_username": "క్రొత్త యూజర్ పేరు:",
        "new_password": "క్రొత్త పాస్వర్డ్:",
        "register_btn": "రిజిస్టర్",
        "login_username": "యూజర్ పేరు:",
        "login_password": "పాస్వర్డ్:",
        "login_btn": "లాగిన్",
        "search_id": "కంటెంట్ ఐడి వెతకండి:",
        "search_btn": "వెతకండి",
        "content_id_retrieved": "📜 తిరిగి పొందిన కంటెంట్ (ID: {content_id})",
        "content_box_label": "కంటెంట్:",
        "total_questions": "📌 **మొత్తం ప్రశ్నలు:** {count}",
        "add_new_question_subheader": "📝 కొత్త ప్రశ్న చేర్చండి",
        "fetch_next_btn": "తదుపరి కంటెంట్ తీసుకురండి",
        "instructions_btn": "నిర్దేశాలు"
    }
}

# ------------------------------------------------------------------------------
# 2) MONGODB CONNECTION
# ------------------------------------------------------------------------------
@st.cache_resource
def init_connection():
    return MongoClient(st.secrets["mongo"]["uri"])

client = init_connection()
db = client["Q_and_A"]
users_collection = db["users"]  
content_collection = db["content_data"]

# ------------------------------------------------------------------------------
# 3) USER AUTHENTICATION FUNCTIONS (USING bcrypt)
# ------------------------------------------------------------------------------
def hash_password(password):
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(password, hashed_password):
    """Verify password against stored bcrypt hash."""
    if isinstance(hashed_password, bytes):
        hashed_password = hashed_password.decode("utf-8")
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))

def register_user(username, password):
    """Registers a new user by hashing the password and storing it in MongoDB."""
    existing_user = users_collection.find_one({"username": username})
    if existing_user:
        return False, "❌ Username already exists."

    hashed_password = hash_password(password)
    users_collection.insert_one({"username": username, "hashed_password": hashed_password})
    return True, "✅ Registration successful! Please log in."

def authenticate_user(username, password):
    """Authenticates a user by verifying bcrypt-hashed passwords."""
    user = users_collection.find_one({"username": username})
    
    if not user:
        return False, "❌ Username does not exist."

    if "hashed_password" not in user:
        return False, "❌ Password field missing in database. Please contact admin."

    hashed_password = user["hashed_password"]
    if not verify_password(password, hashed_password):
        return False, "❌ Incorrect password."

    return True, "✅ Login successful!"

def is_authenticated():
    """Check if a user is logged in by verifying session state."""
    return "authenticated_user" in st.session_state

def login_user(username):
    """Save logged-in user to session state."""
    st.session_state["authenticated_user"] = username

def logout_user():
    """Clear session and log out user."""
    st.session_state.pop("authenticated_user", None)

# ------------------------------------------------------------------------------
# 4) SEARCH FOR CONTENT BY content_id
# ------------------------------------------------------------------------------
def fetch_content_by_id(content_id):
    """Fetches content based on user-input content_id."""
    found = content_collection.find_one({"content_id": content_id})
    if found:
        st.session_state["current_content_id"] = found["content_id"]
        st.session_state["questions"] = found.get("questions", [])
    else:
        st.error(f"❌ No content found for content_id: {content_id}")

# ------------------------------------------------------------------------------
# 5) CONTENT MANAGEMENT FUNCTION
# ------------------------------------------------------------------------------
def content_management(lang):
    """Manages content fetching, editing, adding, and deleting."""
    st.subheader(LANG_TEXT[lang]["app_title"])

    # **Search Box for Content ID**
    search_id = st.text_input(LANG_TEXT[lang]["search_id"])
    if st.button(LANG_TEXT[lang]["search_btn"]):
        fetch_content_by_id(search_id)

    if "current_content_id" in st.session_state:
        content_data = content_collection.find_one({"content_id": st.session_state["current_content_id"]})
        if content_data:
            st.subheader(LANG_TEXT[lang]["content_id_retrieved"].format(content_id=content_data['content_id']))
            st.text_area(LANG_TEXT[lang]["content_box_label"], value=content_data.get("content", ""), height=300, disabled=True)
            
            questions_list = content_data.get("questions", [])
            st.write(LANG_TEXT[lang]["total_questions"].format(count=len(questions_list)))

    if st.button(LANG_TEXT[lang]["fetch_next_btn"]):
        st.session_state.pop("current_content_id")
        st.session_state.pop("questions", None)
        st.rerun()

# ------------------------------------------------------------------------------
# 6) MAIN STREAMLIT APP: LOGIN & AUTHENTICATION
# ------------------------------------------------------------------------------
st.title("🔒 User Authentication")

# Language Selection
lang = st.selectbox("🌍 Choose Language", options=["English", "Telugu"])

if not is_authenticated():
    st.subheader("🔑 Login or Register")
    option = st.radio("Choose an option:", [LANG_TEXT[lang]["login_label"], LANG_TEXT[lang]["register_label"]])

    if option == LANG_TEXT[lang]["login_label"]:
        username = st.text_input(LANG_TEXT[lang]["login_username"])
        password = st.text_input(LANG_TEXT[lang]["login_password"], type="password")
        if st.button(LANG_TEXT[lang]["login_btn"]):
            success, message = authenticate_user(username, password)
            if success:
                login_user(username)
                st.rerun()
            else:
                st.error(message)
    else:
        new_username = st.text_input(LANG_TEXT[lang]["new_username"])
        new_password = st.text_input(LANG_TEXT[lang]["new_password"], type="password")
        if st.button(LANG_TEXT[lang]["register_btn"]):
            success, message = register_user(new_username, new_password)
            st.success(message) if success else st.error(message)

else:
    st.success(f"✅ {LANG_TEXT[lang]['app_title']} - Welcome, {st.session_state['authenticated_user']}!")
    if st.button("Logout"):
        logout_user()
        st.rerun()
    content_management(lang)
