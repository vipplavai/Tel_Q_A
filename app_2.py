import streamlit as st
from pymongo import MongoClient
import bcrypt
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
# 2) USER AUTHENTICATION FUNCTIONS (USING bcrypt)
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
# 3) LOG USER ACTIONS
# ------------------------------------------------------------------------------
def log_user_action(content_id, action):
    """Logs user actions such as skipping, editing, and adding questions."""
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
# 4) FETCH NEXT CONTENT
# ------------------------------------------------------------------------------
def fetch_next_content():
    """Fetches the next content based on priority: empty questions → less than 6 questions → skipped items."""
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
    else:
        st.warning("✅ No more content available to process!")
        st.stop()

# ------------------------------------------------------------------------------
# 5) SEARCH FOR CONTENT BY content_id
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
# 6) CONTENT MANAGEMENT FUNCTION
# ------------------------------------------------------------------------------
def content_management():
    """Manages content fetching, editing, adding, and deleting."""
    st.subheader("📖 Q & A Content Manager")

    # **NEW: Search Box for Content ID**
    search_id = st.text_input("🔍 Search Content by ID:")
    if st.button("Search"):
        fetch_content_by_id(search_id)

    if "current_content_id" not in st.session_state:
        fetch_next_content()

    if "current_content_id" in st.session_state:
        content_data = content_collection.find_one({"content_id": st.session_state["current_content_id"]})
        if content_data:
            st.subheader(f"📜 Content (ID: {content_data['content_id']})")
            st.text_area("Content:", value=content_data.get("content", ""), height=300, disabled=True)

            questions_list = content_data.get("questions", [])
            st.write(f"📌 **Total Questions:** {len(questions_list)}")

            # Editing & Deleting Questions
            updated_questions = []
            delete_indices = []
            for idx, q in enumerate(questions_list, start=1):
                col1, col2 = st.columns([8, 1])
                with col1:
                    question_text = st.text_area(f"Edit Question {idx}", value=q["question"], key=f"edit_q_{idx}")
                    difficulty = st.selectbox(f"Difficulty {idx}", ["easy", "medium", "hard"], 
                                              index=["easy", "medium", "hard"].index(q["difficulty"]), key=f"edit_d_{idx}")
                with col2:
                    delete_flag = st.checkbox(f"🗑️", key=f"delete_{idx}")
                    if delete_flag:
                        delete_indices.append(idx - 1)

                answer_text = q.get("answer", "")
                updated_questions.append({"question": question_text, "difficulty": difficulty, "answer": answer_text})

            if st.button("Save Changes"):
                content_collection.update_one({"content_id": content_data["content_id"]}, {"$set": {"questions": updated_questions}})
                log_user_action(content_data["content_id"], "edited questions")
                st.success("✅ Changes saved successfully!")
                st.rerun()

            if delete_indices:
                if st.button("Delete Selected Questions"):
                    new_questions = [q for i, q in enumerate(questions_list) if i not in delete_indices]
                    content_collection.update_one({"content_id": content_data["content_id"]}, {"$set": {"questions": new_questions}})
                    log_user_action(content_data["content_id"], "deleted questions")
                    st.success("✅ Selected questions deleted successfully!")
                    st.rerun()

    if st.button("Fetch Next Content"):
        st.session_state["skipped_ids"].append(st.session_state["current_content_id"])
        log_user_action(st.session_state["current_content_id"], "skipped")
        st.session_state.pop("current_content_id")
        st.session_state.pop("questions", None)
        st.rerun()

# ------------------------------------------------------------------------------
# 7) MAIN STREAMLIT APP: LOGIN & AUTHENTICATION
# ------------------------------------------------------------------------------
st.title("🔒 User Authentication")

if not is_authenticated():
    st.subheader("🔑 Login or Register")
    option = st.radio("Choose an option:", ["Login", "Register"])

    if option == "Login":
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            success, message = authenticate_user(username, password)
            if success:
                login_user(username)
                st.rerun()
            else:
                st.error(message)
else:
    st.success(f"✅ Welcome, {st.session_state['authenticated_user']}!")
    if st.button("Logout"):
        logout_user()
        st.rerun()
    content_management()
