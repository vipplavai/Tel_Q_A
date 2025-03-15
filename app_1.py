import streamlit as st
from pymongo import MongoClient
from datetime import datetime
from lang_text import LANG_TEXT
from instructions import INSTRUCTIONS

# ------------------------------------------------------------------------------
# 1) CONFIGURATIONS: LANGUAGE & DB CONNECTION
# ------------------------------------------------------------------------------
st.set_page_config(page_title="Question Inserter Tool @vipplavAI", layout="wide")

# Set default language
if "language" not in st.session_state:
    st.session_state["language"] = "English"

# Load text based on language
TEXT = LANG_TEXT[st.session_state["language"]]
GUIDE = INSTRUCTIONS[st.session_state["language"]]

@st.cache_resource
def init_connection():
    return MongoClient(st.secrets["mongo"]["uri"])

client = init_connection()
db = client["Q_and_A"]
users_collection = db["users"]
content_collection = db["content_data"]

# ------------------------------------------------------------------------------
# 2) USER AUTHENTICATION (Username-Only Login)
# ------------------------------------------------------------------------------
def is_authenticated():
    return "authenticated_user" in st.session_state

def login_user(username):
    st.session_state["authenticated_user"] = username

def logout_user():
    st.session_state.pop("authenticated_user", None)

def authenticate_or_register_user(username):
    """Logs in an existing user or registers a new one automatically."""
    if not users_collection.find_one({"username": username}):
        users_collection.insert_one({"username": username})  # Auto-register if new user
    login_user(username)

# ------------------------------------------------------------------------------
# 3) FETCH NEXT CONTENT (Prioritizing Empty Questions)
# ------------------------------------------------------------------------------
def fetch_next_content():
    if "skipped_ids" not in st.session_state:
        st.session_state["skipped_ids"] = []

    # Reset new question box
    st.session_state["new_question"] = ""

    # Priority 1: Fetch content with empty questions
    doc = content_collection.find_one({"questions": {"$size": 0}, "content_id": {"$nin": st.session_state["skipped_ids"]}})

    # Priority 2: Fetch content with <6 questions
    if not doc:
        doc = content_collection.find_one({"$expr": {"$lt": [{"$size": "$questions"}, 6]}, "content_id": {"$nin": st.session_state["skipped_ids"]}})

    # Priority 3: Fetch skipped content
    if not doc and st.session_state["skipped_ids"]:
        doc = content_collection.find_one({"content_id": st.session_state["skipped_ids"].pop(0)})

    if doc:
        st.session_state["current_content_id"] = doc["content_id"]
        st.session_state["questions"] = doc.get("questions", [])
    else:
        st.warning(TEXT["no_more_items"])

# ------------------------------------------------------------------------------
# 4) LOG USER ACTIONS
# ------------------------------------------------------------------------------
def log_user_action(content_id, action):
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content_collection.update_one(
        {"content_id": content_id},
        {
            "$push": {
                "users": {
                    "username": st.session_state["authenticated_user"],
                    "action": action,
                    "datetime": timestamp_str
                }
            }
        },
        upsert=True
    )

# ------------------------------------------------------------------------------
# 5) CONTENT MANAGEMENT FUNCTION
# ------------------------------------------------------------------------------
def content_management():
    st.subheader(TEXT["app_title"])

    search_id = st.text_input(TEXT["search_id"])
    if st.button(TEXT["search_btn"]):
        fetch_content_by_id(search_id)

    if "current_content_id" not in st.session_state:
        fetch_next_content()

    if "current_content_id" in st.session_state:
        content_data = content_collection.find_one({"content_id": st.session_state["current_content_id"]})
        st.subheader(TEXT["content_id_retrieved"].format(content_id=content_data["content_id"]))
        st.text_area(TEXT["content_box_label"], value=content_data.get("content", ""), height=300, disabled=True)

        questions = content_data.get("questions", [])
        st.write(TEXT["total_questions"].format(count=len(questions)))

        updated_questions = []
        delete_indices = []
        for idx, q in enumerate(questions, start=1):
            question_text = st.text_area(f"{TEXT['edit_question_label'].format(idx=idx)}", value=q["question"], key=f"edit_q_{idx}")
            delete_flag = st.checkbox(f"{TEXT['delete_question_label'].format(idx=idx)}", key=f"delete_{idx}")
            if delete_flag:
                delete_indices.append(idx - 1)
            updated_questions.append({"question": question_text})

        if st.button(TEXT["save_changes_btn"]):
            content_collection.update_one({"content_id": content_data["content_id"]}, {"$set": {"questions": updated_questions}})
            log_user_action(content_data["content_id"], "edited questions")
            st.success(TEXT["changes_saved"])
            st.rerun()

        if delete_indices:
            new_questions = [q for i, q in enumerate(questions) if i not in delete_indices]
            content_collection.update_one({"content_id": content_data["content_id"]}, {"$set": {"questions": new_questions}})
            log_user_action(content_data["content_id"], "deleted questions")
            st.success(TEXT["delete_warning"])
            st.rerun()

        st.subheader(TEXT["add_new_question_subheader"])
        st.session_state["new_question"] = st.text_area(TEXT["enter_new_q_label"], value=st.session_state.get("new_question", ""))

        if st.button(TEXT["save_question_btn"]):
            if st.session_state["new_question"].strip():
                content_collection.update_one(
                    {"content_id": content_data["content_id"]},
                    {"$push": {"questions": {"question": st.session_state["new_question"]}}},
                    upsert=True
                )
                log_user_action(content_data["content_id"], "added question")
                st.success("✅ New question added successfully!")
                st.session_state["new_question"] = ""  # Reset after adding
                st.rerun()
            else:
                st.error(TEXT["empty_q_error"])

    if st.button(TEXT["fetch_next_btn"]):
        log_user_action(st.session_state["current_content_id"], "skipped")
        st.session_state["skipped_ids"].append(st.session_state["current_content_id"])
        st.session_state.pop("current_content_id")
        st.session_state.pop("questions", None)
        fetch_next_content()
        st.rerun()

# ------------------------------------------------------------------------------
# 6) MAIN APP: LOGIN & AUTHENTICATION
# ------------------------------------------------------------------------------
st.title(TEXT["app_title"])

# Language Selection
language_option = st.radio("🌎 Choose Language:", ["English", "Telugu"], index=0 if st.session_state["language"] == "English" else 1)
if language_option != st.session_state["language"]:
    st.session_state["language"] = language_option
    st.rerun()

if not is_authenticated():
    username = st.text_input(TEXT["login_username"])
    if st.button(TEXT["login_btn"]):
        if username.strip():
            authenticate_or_register_user(username)  # Auto-login or register new user
            fetch_next_content()  # Fetch next available content after login
            st.rerun()
        else:
            st.error(TEXT["login_fill_error"])
else:
    st.success(TEXT["welcome_user"].format(username=st.session_state['authenticated_user']))
    if st.button("Logout"):
        logout_user()
        st.rerun()
    content_management()

# ------------------------------------------------------------------------------
# 7) INSTRUCTIONS SECTION
# ------------------------------------------------------------------------------
if st.button(TEXT["instructions_btn"]):
    st.markdown(GUIDE, unsafe_allow_html=True)
