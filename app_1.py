import streamlit as st
from pymongo import MongoClient
from datetime import datetime
from instructions import INSTRUCTIONS  # Import instructions from separate file
from lang_text import LANG_TEXT  # Import language text mappings from separate file

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
        st.session_state["new_question"] = ""  # Reset new question field
    else:
        st.warning("✅ No more content available to process!")

# ------------------------------------------------------------------------------
# 4) CONTENT MANAGEMENT FUNCTION
# ------------------------------------------------------------------------------
def content_management():
    st.subheader("📖 Q & A Content Manager")
    
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
            st.success("✅ Changes saved successfully!")
            st.rerun()

        if delete_indices:
            new_questions = [q for i, q in enumerate(questions) if i not in delete_indices]
            content_collection.update_one({"content_id": content_data["content_id"]}, {"$set": {"questions": new_questions}})
            st.success("✅ Deleted selected questions!")
            st.rerun()

        st.subheader("📝 Add a New Question")
        st.session_state["new_question"] = st.text_area("Enter New Question:", value=st.session_state.get("new_question", ""))
        
        if st.button("Save Question"):
            if st.session_state["new_question"].strip():
                content_collection.update_one(
                    {"content_id": content_data["content_id"]},
                    {"$push": {"questions": {"question": st.session_state["new_question"]}}},
                    upsert=True
                )
                st.session_state["new_question"] = ""  # Reset input field
                st.success("✅ New question added successfully!")
                st.rerun()
            else:
                st.error("⚠️ Please enter a question before saving!")

    if st.button("Skip & Fetch Next Content"):
        st.session_state["skipped_ids"].append(st.session_state["current_content_id"])
        st.session_state.pop("current_content_id")
        st.session_state.pop("questions", None)
        fetch_next_content()
        st.rerun()

# ------------------------------------------------------------------------------
# 5) MAIN APP: LOGIN & AUTHENTICATION (USERNAME ONLY)
# ------------------------------------------------------------------------------
st.title("🔒 User Authentication")

if not is_authenticated():
    username = st.text_input("Enter your Username to Login:")
    if st.button("Login"):
        if username.strip():
            authenticate_or_register_user(username)
            fetch_next_content()
            st.rerun()
        else:
            st.error("⚠️ Please enter a username to continue.")
else:
    st.success(f"✅ Welcome, {st.session_state['authenticated_user']}!")
    if st.button("Logout"):
        logout_user()
        st.rerun()
    content_management()

st.sidebar.header("ℹ️ Instructions")
st.sidebar.text_area("Instructions", INSTRUCTIONS["English"], height=300, disabled=True)
