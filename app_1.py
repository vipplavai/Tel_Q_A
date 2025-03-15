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
        "save_changes_btn": "Save Changes",
        "delete_question_label": "Delete question {idx}",
        "delete_warning": "Marked question {idx} for deletion.",
        "changes_saved": "✅ Changes saved successfully!",
        "save_question_btn": "Save Question",
        "empty_q_error": "⚠️ Please enter a question before saving!",
        "fetch_next_subheader": "🔄 Fetch Next Content (Skip this one)"
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
        "save_changes_btn": "మార్పులు సేవ్ చేయండి",
        "delete_question_label": "ఈ ప్రశ్నను తొలగించు {idx}",
        "delete_warning": "{idx} ప్రశ్న తొలగించబడింది.",
        "changes_saved": "✅ మార్పులు విజయవంతంగా సేవ్ అయ్యాయి!",
        "save_question_btn": "ప్రశ్నని సేవ్ చేయండి",
        "empty_q_error": "⚠️ సేవ్ చేసే ముందు దయచేసి ఒక ప్రశ్నను నమోదు చేయండి!",
        "fetch_next_subheader": "🔄 మరో కంటెంట్ తీసుకురండి (ఇది స్కిప్ చేయండి)"
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
# 3) USER AUTHENTICATION FUNCTIONS
# ------------------------------------------------------------------------------
def hash_password(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(password, hashed_password):
    if isinstance(hashed_password, bytes):
        hashed_password = hashed_password.decode("utf-8")
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))

def register_user(username, password):
    existing_user = users_collection.find_one({"username": username})
    if existing_user:
        return False, "❌ Username already exists."
    hashed_password = hash_password(password)
    users_collection.insert_one({"username": username, "hashed_password": hashed_password})
    return True, "✅ Registration successful! Please log in."

def authenticate_user(username, password):
    user = users_collection.find_one({"username": username})
    if not user or "hashed_password" not in user:
        return False, "❌ Invalid username or password."
    if not verify_password(password, user["hashed_password"]):
        return False, "❌ Incorrect password."
    return True, "✅ Login successful!"

def is_authenticated():
    return "authenticated_user" in st.session_state

def login_user(username):
    st.session_state["authenticated_user"] = username

def logout_user():
    st.session_state.pop("authenticated_user", None)

# ------------------------------------------------------------------------------
# 4) FETCH NEXT CONTENT (Prioritizing Empty Questions)
# ------------------------------------------------------------------------------
def fetch_next_content():
    if "skipped_ids" not in st.session_state:
        st.session_state["skipped_ids"] = []

    query_empty = {"questions": {"$size": 0}, "content_id": {"$nin": st.session_state["skipped_ids"]}}
    doc = content_collection.find_one(query_empty)

    if not doc:
        query_lt6 = {"$expr": {"$lt": [{"$size": "$questions"}, 6]}, "content_id": {"$nin": st.session_state["skipped_ids"]}}
        doc = content_collection.find_one(query_lt6)

    if not doc and st.session_state["skipped_ids"]:
        skipped_id = st.session_state["skipped_ids"].pop(0)
        doc = content_collection.find_one({"content_id": skipped_id})

    if doc:
        st.session_state["current_content_id"] = doc["content_id"]
        st.session_state["questions"] = doc.get("questions", [])

# ------------------------------------------------------------------------------
# 5) CONTENT MANAGEMENT FUNCTION
# ------------------------------------------------------------------------------
def content_management(lang):
    st.subheader(LANG_TEXT[lang]["app_title"])
    search_id = st.text_input(LANG_TEXT[lang]["search_id"])
    if st.button(LANG_TEXT[lang]["search_btn"]):
        fetch_content_by_id(search_id)

    if "current_content_id" not in st.session_state:
        fetch_next_content()

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
        fetch_next_content()
        st.rerun()

# ------------------------------------------------------------------------------
# 6) MAIN APP: LOGIN & AUTHENTICATION
# ------------------------------------------------------------------------------
st.title("🔒 User Authentication")
lang = st.selectbox("🌍 Choose Language", options=["English", "Telugu"])

if not is_authenticated():
    option = st.radio("Choose an option:", [LANG_TEXT[lang]["login_label"], LANG_TEXT[lang]["register_label"]])
    if option == LANG_TEXT[lang]["login_label"]:
        username = st.text_input(LANG_TEXT[lang]["login_username"])
        password = st.text_input(LANG_TEXT[lang]["login_password"], type="password")
        if st.button(LANG_TEXT[lang]["login_btn"]):
            success, message = authenticate_user(username, password)
            if success:
                login_user(username)
                fetch_next_content()  # 🔥 Automatically fetches next available content
                st.rerun()
            else:
                st.error(message)
else:
    st.success(f"✅ {LANG_TEXT[lang]['app_title']} - Welcome, {st.session_state['authenticated_user']}!")
    if st.button("Logout"):
        logout_user()
        st.rerun()
    content_management(lang)
