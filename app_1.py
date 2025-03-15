import streamlit as st
from pymongo import MongoClient
from datetime import datetime

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
# 2) LANGUAGE SELECTION (English / Telugu)
# ------------------------------------------------------------------------------
LANGUAGES = {
    "English": {
        "title": "🔒 User Authentication",
        "username_prompt": "Enter your Username to Login:",
        "login_button": "Login",
        "logout_button": "Logout",
        "content_manager": "📖 Q & A Content Manager",
        "search_placeholder": "🔍 Search Content by ID:",
        "search_button": "Search",
        "retrieved_content": "📜 Retrieved Content",
        "total_questions": "📌 Total Questions:",
        "edit_question": "Edit Question",
        "delete": "🗑 Delete",
        "save_changes": "Save Changes",
        "delete_success": "✅ Deleted selected questions!",
        "add_question": "📝 Add a New Question",
        "enter_question": "Enter New Question:",
        "save_question": "Save Question",
        "skip_fetch": "Skip & Fetch Next Content",
        "success_question": "✅ New question added successfully!",
        "empty_warning": "⚠️ Please enter a question before saving!",
        "no_more_content": "✅ No more content available to process!",
        "welcome_message": "✅ Welcome, ",
    },
    "Telugu": {
        "title": "🔒 వినియోగదారుని ప్రామాణీకరణ",
        "username_prompt": "మీ వినియోగదారు పేరు నమోదు చేయండి:",
        "login_button": "ప్రవేశించండి",
        "logout_button": "లాగ్ అవుట్",
        "content_manager": "📖 ప్రశ్నలు & సమాధానాలు కంటెంట్ మేనేజర్",
        "search_placeholder": "🔍 ID ద్వారా కంటెంట్ శోధించండి:",
        "search_button": "శోధించండి",
        "retrieved_content": "📜 లభించిన కంటెంట్",
        "total_questions": "📌 మొత్తం ప్రశ్నలు:",
        "edit_question": "ప్రశ్నను మార్చండి",
        "delete": "🗑 తొలగించండి",
        "save_changes": "మార్పులను భద్రపరచండి",
        "delete_success": "✅ ఎంచుకున్న ప్రశ్నలు తొలగించబడ్డాయి!",
        "add_question": "📝 కొత్త ప్రశ్నను జోడించండి",
        "enter_question": "కొత్త ప్రశ్నను నమోదు చేయండి:",
        "save_question": "ప్రశ్నను భద్రపరచండి",
        "skip_fetch": "దాటవేసి తదుపరి కంటెంట్‌ను పొందండి",
        "success_question": "✅ కొత్త ప్రశ్న విజయవంతంగా జోడించబడింది!",
        "empty_warning": "⚠️ దయచేసి ప్రశ్నను నమోదు చేయండి!",
        "no_more_content": "✅ ప్రాసెస్ చేయడానికి మరో కంటెంట్ లేదు!",
        "welcome_message": "✅ స్వాగతం, ",
    }
}

if "language" not in st.session_state:
    st.session_state["language"] = "English"

def get_text(key):
    return LANGUAGES[st.session_state["language"]][key]

st.sidebar.selectbox("🌍 Select Language", ["English", "Telugu"], key="language")

# ------------------------------------------------------------------------------
# 3) USER AUTHENTICATION (Username-Only Login)
# ------------------------------------------------------------------------------
def is_authenticated():
    return "authenticated_user" in st.session_state

def login_user(username):
    st.session_state["authenticated_user"] = username

def logout_user():
    st.session_state.pop("authenticated_user", None)

def authenticate_or_register_user(username):
    if not users_collection.find_one({"username": username}):
        users_collection.insert_one({"username": username})  
    login_user(username)

# ------------------------------------------------------------------------------
# 4) FETCH NEXT CONTENT (Prioritizing Empty Questions)
# ------------------------------------------------------------------------------
def fetch_next_content():
    if "skipped_ids" not in st.session_state:
        st.session_state["skipped_ids"] = []

    doc = content_collection.find_one({"questions": {"$size": 0}, "content_id": {"$nin": st.session_state["skipped_ids"]}})

    if not doc:
        doc = content_collection.find_one({"$expr": {"$lt": [{"$size": "$questions"}, 6]}, "content_id": {"$nin": st.session_state["skipped_ids"]}})

    if not doc and st.session_state["skipped_ids"]:
        doc = content_collection.find_one({"content_id": st.session_state["skipped_ids"].pop(0)})

    if doc:
        st.session_state["current_content_id"] = doc["content_id"]
        st.session_state["questions"] = doc.get("questions", [])
        st.session_state["new_question"] = ""  # Clear input field when fetching new content
    else:
        st.warning(get_text("no_more_content"))

# ------------------------------------------------------------------------------
# 5) SEARCH FOR CONTENT BY `content_id`
# ------------------------------------------------------------------------------
def fetch_content_by_id(content_id):
    found = content_collection.find_one({"content_id": content_id})
    if found:
        st.session_state["current_content_id"] = found["content_id"]
        st.session_state["questions"] = found.get("questions", [])
    else:
        st.error(f"❌ {get_text('no_more_content')} {content_id}")

# ------------------------------------------------------------------------------
# 6) LOG USER ACTIONS
# ------------------------------------------------------------------------------
def log_user_action(content_id, action):
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content_collection.update_one(
        {"content_id": content_id},
        {"$push": {"users": {"username": st.session_state["authenticated_user"], "action": action, "datetime": timestamp_str}}},
        upsert=True
    )

# ------------------------------------------------------------------------------
# 7) CONTENT MANAGEMENT FUNCTION
# ------------------------------------------------------------------------------
def content_management():
    st.subheader(get_text("content_manager"))

    search_id = st.text_input(get_text("search_placeholder"))
    if st.button(get_text("search_button")):
        fetch_content_by_id(search_id)

    if "current_content_id" not in st.session_state:
        fetch_next_content()

    if "current_content_id" in st.session_state:
        content_data = content_collection.find_one({"content_id": st.session_state["current_content_id"]})
        st.subheader(f"{get_text('retrieved_content')} (ID: {content_data['content_id']})")
        st.text_area("Content:", value=content_data.get("content", ""), height=300, disabled=True)

        questions = content_data.get("questions", [])
        st.write(f"{get_text('total_questions')} {len(questions)}")

        updated_questions = []
        delete_indices = []
        for idx, q in enumerate(questions, start=1):
            question_text = st.text_area(f"{get_text('edit_question')} {idx}", value=q["question"], key=f"edit_q_{idx}")
            delete_flag = st.checkbox(f"{get_text('delete')} {idx}", key=f"delete_{idx}")
            if delete_flag:
                delete_indices.append(idx - 1)
            updated_questions.append({"question": question_text})

        if st.button(get_text("save_changes")):
            content_collection.update_one({"content_id": content_data["content_id"]}, {"$set": {"questions": updated_questions}})
            log_user_action(content_data["content_id"], "edited questions")
            st.success("✅ Changes saved successfully!")
            st.rerun()

        st.subheader(get_text("add_question"))
        new_question = st.text_area(get_text("enter_question"), key="new_question")
        if st.button(get_text("save_question")):
            if new_question.strip():
                content_collection.update_one({"content_id": content_data["content_id"]}, {"$push": {"questions": {"question": new_question}}}, upsert=True)
                log_user_action(content_data["content_id"], "added question")
                st.success(get_text("success_question"))
                st.session_state["new_question"] = ""
                st.rerun()

    if st.button(get_text("skip_fetch")):
        log_user_action(st.session_state["current_content_id"], "skipped")
        st.session_state["skipped_ids"].append(st.session_state["current_content_id"])
        st.session_state.pop("current_content_id")
        st.session_state.pop("questions", None)
        fetch_next_content()
        st.rerun()

# ------------------------------------------------------------------------------
# 8) MAIN APP: LOGIN
# ------------------------------------------------------------------------------
st.title(get_text("title"))

if not is_authenticated():
    username = st.text_input(get_text("username_prompt"))
    if st.button(get_text("login_button")) and username.strip():
        authenticate_or_register_user(username)
        fetch_next_content()
        st.rerun()
else:
    st.success(f"{get_text('welcome_message')} {st.session_state['authenticated_user']}!")
    if st.button(get_text("logout_button")):
        logout_user()
        st.rerun()
    content_management()
