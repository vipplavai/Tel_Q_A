import streamlit as st
from pymongo import MongoClient
from datetime import datetime

# ------------------------------------------------------------------------------
# 0) LANGUAGE DICTIONARY
# ------------------------------------------------------------------------------
LANG_DICT = {
    "en": {
        "select_language": "Select Language",
        "app_title": "🔒 User Authentication",
        "login_input": "Enter your Username to Login:",
        "login_button": "Login",
        "logout_button": "Logout",
        "user_welcome": "✅ Welcome,",
        "no_username_warning": "⚠️ Please enter a username to continue.",
        "no_content_available": "✅ No more content available to process!",
        "no_content_found": "❌ No content found for content_id:",
        "qna_manager_title": "📖 Q & A Content Manager",
        "search_content_id": "🔍 Search Content by ID:",
        "search_button": "Search",
        "retrieved_content_id": "📜 Retrieved Content (ID:",
        "content_label": "Content:",
        "total_questions": "📌 **Total Questions:**",
        "edit_question": "Edit Question",
        "delete_question": "🗑 Delete",
        "save_changes": "Save Changes",
        "changes_saved": "✅ Changes saved successfully!",
        "deleted_questions": "✅ Deleted selected questions!",
        "add_new_question": "📝 Add a New Question",
        "enter_new_question": "Enter New Question:",
        "save_question": "Save Question",
        "question_added": "✅ New question added successfully!",
        "enter_question_warning": "⚠️ Please enter a question before saving!",
        "skip_and_next": "Skip & Fetch Next Content",
        "skipped": "skipped",
    },
    "te": {
        "select_language": "భాషను ఎంచుకోండి",
        "app_title": "🔒 వాడుకరి ధృవీకరణ",
        "login_input": "లాగిన్ కోసం మీ వాడుకరి పేరును నమోదు చేయండి:",
        "login_button": "లాగిన్",
        "logout_button": "లాగ్ అవుట్",
        "user_welcome": "✅ స్వాగతం,",
        "no_username_warning": "⚠️ కొనసాగడానికి దయచేసి వాడుకరి పేరును నమోదు చేయండి.",
        "no_content_available": "✅ ప్రాసెస్ చేయడానికి ఇంక ఏ కంటెంట్ లేదు!",
        "no_content_found": "❌ ఈ content_id కోసం కంటెంట్ లభించలేదు:",
        "qna_manager_title": "📖 Q & A కంటెంట్ మేనేజర్",
        "search_content_id": "🔍 ID ద్వారా కంటెంట్ వెతకండి:",
        "search_button": "వెతకండి",
        "retrieved_content_id": "📜 పొందిన కంటెంట్ (ID:",
        "content_label": "కంటెంట్:",
        "total_questions": "📌 **మొత్తం ప్రశ్నలు:**",
        "edit_question": "ప్రశ్నను మార్చండి",
        "delete_question": "🗑 తొలగించండి",
        "save_changes": "మార్పులను సేవ్ చేయండి",
        "changes_saved": "✅ మార్పులు విజయవంతంగా సేవ్ అయ్యాయి!",
        "deleted_questions": "✅ ఎంపిక చేసిన ప్రశ్నలు తొలగించబడ్డాయి!",
        "add_new_question": "📝 కొత్త ప్రశ్నను జోడించండి",
        "enter_new_question": "కొత్త ప్రశ్నను నమోదు చేయండి:",
        "save_question": "ప్రశ్నను సేవ్ చేయండి",
        "question_added": "✅ కొత్త ప్రశ్న విజయవంతంగా జోడించబడింది!",
        "enter_question_warning": "⚠️ దయచేసి ప్రశ్నను నమోదు చేసిన తర్వాత సేవ్ చేయండి!",
        "skip_and_next": "దాటవేసి తదుపరి కంటెంట్ చూడండి",
        "skipped": "దాటవేసారు",
    }
}

# ------------------------------------------------------------------------------
# 1) MONGODB CONNECTION
# ------------------------------------------------------------------------------
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
        st.warning(LANG_DICT[st.session_state["lang"]]["no_content_available"])

# ------------------------------------------------------------------------------
# 4) SEARCH FOR CONTENT BY `content_id`
# ------------------------------------------------------------------------------
def fetch_content_by_id(content_id):
    found = content_collection.find_one({"content_id": content_id})
    if found:
        st.session_state["current_content_id"] = found["content_id"]
        st.session_state["questions"] = found.get("questions", [])
    else:
        st.error(f"{LANG_DICT[st.session_state['lang']]['no_content_found']} {content_id}")

# ------------------------------------------------------------------------------
# 5) LOG USER ACTIONS
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
# 6) CONTENT MANAGEMENT FUNCTION
# ------------------------------------------------------------------------------
def content_management():
    lang = st.session_state["lang"]
    st.subheader(LANG_DICT[lang]["qna_manager_title"])

    search_id = st.text_input(LANG_DICT[lang]["search_content_id"])
    if st.button(LANG_DICT[lang]["search_button"]):
        fetch_content_by_id(search_id)

    if "current_content_id" not in st.session_state:
        fetch_next_content()

    if "current_content_id" in st.session_state:
        content_data = content_collection.find_one({"content_id": st.session_state["current_content_id"]})
        st.subheader(f"{LANG_DICT[lang]['retrieved_content_id']} {content_data['content_id']})")
        st.text_area(LANG_DICT[lang]["content_label"], value=content_data.get("content", ""), height=300, disabled=True)

        questions = content_data.get("questions", [])
        st.write(f"{LANG_DICT[lang]['total_questions']} {len(questions)}")

        updated_questions = []
        delete_indices = []
        for idx, q in enumerate(questions, start=1):
            question_text = st.text_area(f"{LANG_DICT[lang]['edit_question']} {idx}", value=q["question"], key=f"edit_q_{idx}")
            delete_flag = st.checkbox(f"{LANG_DICT[lang]['delete_question']} {idx}", key=f"delete_{idx}")
            if delete_flag:
                delete_indices.append(idx - 1)
            updated_questions.append({"question": question_text})

        if st.button(LANG_DICT[lang]["save_changes"]):
            content_collection.update_one(
                {"content_id": content_data["content_id"]},
                {"$set": {"questions": updated_questions}}
            )
            log_user_action(content_data["content_id"], "edited questions")
            st.success(LANG_DICT[lang]["changes_saved"])
            st.rerun()

        if delete_indices:
            new_questions = [q for i, q in enumerate(questions) if i not in delete_indices]
            content_collection.update_one({"content_id": content_data["content_id"]}, {"$set": {"questions": new_questions}})
            log_user_action(content_data["content_id"], "deleted questions")
            st.success(LANG_DICT[lang]["deleted_questions"])
            st.rerun()

        st.subheader(LANG_DICT[lang]["add_new_question"])
        new_question = st.text_area(LANG_DICT[lang]["enter_new_question"])
        if st.button(LANG_DICT[lang]["save_question"]):
            if new_question.strip():
                content_collection.update_one(
                    {"content_id": content_data["content_id"]},
                    {"$push": {"questions": {"question": new_question}}},
                    upsert=True
                )
                log_user_action(content_data["content_id"], "added question")
                st.success(LANG_DICT[lang]["question_added"])
                st.rerun()
            else:
                st.error(LANG_DICT[lang]["enter_question_warning"])

    if st.button(LANG_DICT[lang]["skip_and_next"]):
        log_user_action(st.session_state["current_content_id"], LANG_DICT[lang]["skipped"])
        st.session_state["skipped_ids"].append(st.session_state["current_content_id"])
        st.session_state.pop("current_content_id")
        st.session_state.pop("questions", None)
        fetch_next_content()
        st.rerun()

# ------------------------------------------------------------------------------
# 7) MAIN APP: LOGIN & AUTHENTICATION (USERNAME ONLY)
# ------------------------------------------------------------------------------
def main():
    # Language selection (store in session_state)
    if "lang" not in st.session_state:
        st.session_state["lang"] = "en"  # default language

    # Language selector at the top (or in a sidebar)
    language_choice = st.selectbox(
        LANG_DICT[st.session_state["lang"]]["select_language"],
        ["English", "Telugu"]
    )
    # Map choice to language code
    st.session_state["lang"] = "en" if language_choice == "English" else "te"
    lang = st.session_state["lang"]

    st.title(LANG_DICT[lang]["app_title"])

    if not is_authenticated():
        username = st.text_input(LANG_DICT[lang]["login_input"])
        if st.button(LANG_DICT[lang]["login_button"]):
            if username.strip():
                authenticate_or_register_user(username)
                fetch_next_content()  # load initial content after login
                st.rerun()
            else:
                st.error(LANG_DICT[lang]["no_username_warning"])
    else:
        st.success(f"{LANG_DICT[lang]['user_welcome']} {st.session_state['authenticated_user']}!")
        if st.button(LANG_DICT[lang]["logout_button"]):
            logout_user()
            st.rerun()
        content_management()

if __name__ == "__main__":
    main()
