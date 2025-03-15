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

    # Ensure new_question is initialized before setting
    if "new_question" not in st.session_state:
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

# ------------------------------------------------------------------------------
# 4) SEARCH FOR CONTENT BY `content_id`
# ------------------------------------------------------------------------------
def fetch_content_by_id(content_id):
    found = content_collection.find_one({"content_id": content_id})
    if found:
        st.session_state["current_content_id"] = found["content_id"]
        st.session_state["questions"] = found.get("questions", [])

        # Ensure new_question is initialized before setting
        st.session_state["new_question"] = ""
    else:
        st.error(f"❌ No content found for content_id: {content_id}")

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
    st.subheader("📖 Q & A Content Manager")

    search_id = st.text_input("🔍 Search Content by ID:")
    if st.button("Search"):
        fetch_content_by_id(search_id)

    if "current_content_id" not in st.session_state:
        fetch_next_content()

    if "current_content_id" in st.session_state:
        content_data = content_collection.find_one({"content_id": st.session_state["current_content_id"]})
        st.subheader(f"📜 Retrieved Content (ID: {content_data['content_id']})")
        st.text_area("Content:", value=content_data.get("content", ""), height=300, disabled=True)

        questions = content_data.get("questions", [])
        st.write(f"📌 **Total Questions:** {len(questions)}")

        updated_questions = []
        delete_indices = []
        for idx, q in enumerate(questions, start=1):
            question_text = st.text_area(f"Edit Question {idx}", value=q["question"], key=f"edit_q_{idx}")
            delete_flag = st.checkbox(f"🗑 Delete {idx}", key=f"delete_{idx}")
            if delete_flag:
                delete_indices.append(idx - 1)
            updated_questions.append({"question": question_text})

        if st.button("Save Changes"):
            content_collection.update_one({"content_id": content_data["content_id"]}, {"$set": {"questions": updated_questions}})
            log_user_action(content_data["content_id"], "edited questions")
            st.success("✅ Changes saved successfully!")
            st.rerun()

        if delete_indices:
            new_questions = [q for i, q in enumerate(questions) if i not in delete_indices]
            content_collection.update_one({"content_id": content_data["content_id"]}, {"$set": {"questions": new_questions}})
            log_user_action(content_data["content_id"], "deleted questions")
            st.success("✅ Deleted selected questions!")
            st.rerun()

        st.subheader("📝 Add a New Question")
        new_question = st.text_area("Enter New Question:", value=st.session_state.get("new_question", ""), key="new_question")
        if st.button("Save Question"):
            if new_question.strip():
                content_collection.update_one(
                    {"content_id": content_data["content_id"]},
                    {"$push": {"questions": {"question": new_question}}},
                    upsert=True
                )
                log_user_action(content_data["content_id"], "added question")
                st.success("✅ New question added successfully!")
                st.session_state["new_question"] = ""  # Reset input after adding
                st.rerun()
            else:
                st.error("⚠️ Please enter a question before saving!")

    if st.button("Skip & Fetch Next Content"):
        log_user_action(st.session_state["current_content_id"], "skipped")
        st.session_state["skipped_ids"].append(st.session_state["current_content_id"])
        st.session_state.pop("current_content_id")
        st.session_state.pop("questions", None)
        fetch_next_content()
        st.rerun()

# ------------------------------------------------------------------------------
# 7) MAIN APP: LOGIN & AUTHENTICATION (USERNAME ONLY)
# ------------------------------------------------------------------------------
st.title("🔒 User Authentication")

if not is_authenticated():
    username = st.text_input("Enter your Username to Login:")
    if st.button("Login"):
        if username.strip():
            authenticate_or_register_user(username)  # Auto-login or register new user
            fetch_next_content()  # Fetch next available content after login
            st.rerun()
        else:
            st.error("⚠️ Please enter a username to continue.")
else:
    st.success(f"✅ Welcome, {st.session_state['authenticated_user']}!")
    if st.button("Logout"):
        logout_user()
        st.rerun()
    content_management()
