import streamlit as st
from pymongo import MongoClient
from datetime import datetime

# ------------------------------------------------------------------------------
# 1) CONFIGURATIONS: LANGUAGE & DB CONNECTION
# ------------------------------------------------------------------------------
st.set_page_config(page_title="📖 Question Inserter Tool @vipplavAI", layout="wide")

# Default Language
if "language" not in st.session_state:
    st.session_state["language"] = "English"

LANG_TEXT = {
    "English": {
        "app_title": "📖 Question Inserter Tool @vipplavAI",
        "choose_language": "🌎 Choose Language:",
        "login_label": "Login",
        "login_username": "Enter your Username:",
        "login_btn": "Login",
        "logout_btn": "Logout",
        "welcome_user": "✅ Welcome, {username}!",
        "search_id": "🔍 Search Content by ID:",
        "search_btn": "Search",
        "search_err": "❌ No content found for content_id: {search_id}",
        "content_id_retrieved": "📜 Retrieved Content (ID: {content_id})",
        "content_box_label": "📄 Content:",
        "total_questions": "📌 **Total Questions:** {count}",
        "add_new_question_subheader": "📝 Add a New Question",
        "enter_new_q_label": "Enter New Question:",
        "save_question_btn": "Save Question",
        "empty_q_error": "⚠️ Please enter a question before saving!",
        "fetch_next_btn": "⏭ Skip & Fetch Next Content",
        "instructions_btn": "📖 Show Instructions",
        "save_changes_btn": "💾 Save Changes",
        "changes_saved": "✅ Changes saved successfully!",
        "delete_question_label": "🗑 Delete Question {idx}",
        "delete_warning": "✅ Selected question(s) deleted successfully!"
    }
}

# Instructions
INSTRUCTIONS = {
    "English": """\
### 📝 How to Use the Tool
1. **Login** with a username.
2. **Fetch Content Automatically** or **Search by ID**.
3. **Add, Edit, or Delete Questions**:
   - Add at least **6 questions per content**.
   - Use Easy (single-word), Medium (2-3 lines), and Hard (4-6 lines) difficulty levels.
4. **Submit & Fetch Next Content**:
   - Save changes before skipping.
   - Your edits are logged.

---
"""
}

@st.cache_resource
def init_connection():
    return MongoClient(st.secrets["mongo"]["uri"])

client = init_connection()
db = client["Q_and_A"]
users_collection = db["users"]
content_collection = db["content_data"]

def is_authenticated():
    return "authenticated_user" in st.session_state

def login_user(username):
    st.session_state["authenticated_user"] = username

def logout_user():
    st.session_state.pop("authenticated_user", None)

def log_user_action(content_id, action):
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content_collection.update_one(
        {"content_id": content_id},
        {"$push": {"users": {"username": st.session_state["authenticated_user"], "action": action, "datetime": timestamp_str}}},
        upsert=True
    )

def fetch_next_content():
    st.session_state["new_question"] = ""
    doc = content_collection.find_one({"questions": {"$size": 0}})
    if not doc:
        doc = content_collection.find_one({"$expr": {"$lt": [{"$size": "$questions"}, 6]}})
    if doc:
        st.session_state["current_content_id"] = doc["content_id"]
        st.session_state["questions"] = doc.get("questions", [])
    else:
        st.warning("✅ No more content available to process!")

def fetch_content_by_id(content_id):
    found = content_collection.find_one({"content_id": content_id})
    if found:
        st.session_state["current_content_id"] = found["content_id"]
        st.session_state["questions"] = found.get("questions", [])
    else:
        st.error(TEXT["search_err"].format(search_id=content_id))

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
            question_text = st.text_area(f"Edit Question {idx}", value=q["question"], key=f"edit_q_{idx}")
            delete_flag = st.checkbox(TEXT["delete_question_label"].format(idx=idx), key=f"delete_{idx}")
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
                st.session_state["new_question"] = ""
                st.rerun()
            else:
                st.error(TEXT["empty_q_error"])

    if st.button(TEXT["fetch_next_btn"]):
        log_user_action(st.session_state["current_content_id"], "skipped")
        fetch_next_content()
        st.rerun()

st.title(TEXT["app_title"])

language_option = st.radio(TEXT["choose_language"], ["English"])
if language_option != st.session_state["language"]:
    st.session_state["language"] = language_option
    st.rerun()

TEXT = LANG_TEXT[st.session_state["language"]]

if not is_authenticated():
    username = st.text_input(TEXT["login_username"])
    if st.button(TEXT["login_btn"]):
        if username.strip():
            login_user(username)
            fetch_next_content()
            st.rerun()
else:
    st.success(TEXT["welcome_user"].format(username=st.session_state['authenticated_user']))
    if st.button(TEXT["logout_btn"]):
        logout_user()
        st.rerun()
    content_management()

if st.button(TEXT["instructions_btn"]):
    st.markdown(INSTRUCTIONS[st.session_state["language"]], unsafe_allow_html=True)
