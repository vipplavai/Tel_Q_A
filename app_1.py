import streamlit as st
from pymongo import MongoClient
from datetime import datetime
import bcrypt  # Requires "pip install bcrypt"

# ------------------------------------------------------------------------------
# 1) Initialize connection to MongoDB
# ------------------------------------------------------------------------------
@st.cache_resource
def init_connection():
    return MongoClient(st.secrets["mongo"]["uri"])

client = init_connection()
db = client["Q_and_A"]  # Database Name

# Collections
content_collection = db["content_data"]  # content Q&A
users_collection = db["users"]           # for storing user accounts

# ------------------------------------------------------------------------------
# 2) Authentication Helpers
# ------------------------------------------------------------------------------
def hash_password(password: str) -> bytes:
    """Generate salted hash for the given password."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(password: str, hashed: bytes) -> bool:
    """Compare a plain password with the hashed password."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

def register_user(username: str, password: str) -> bool:
    """
    Attempt to register a new user. 
    Returns True if registration is successful, False if username already exists.
    """
    existing_user = users_collection.find_one({"username": username})
    if existing_user:
        return False  # username already taken

    hashed_pw = hash_password(password)
    new_user = {
        "username": username,
        "hashed_password": hashed_pw,
        "activity_logs": []  # store user logs here
    }
    users_collection.insert_one(new_user)
    return True

def login_user(username: str, password: str) -> bool:
    """
    Attempt to log in user. 
    Returns True if credentials match, else False.
    """
    user_doc = users_collection.find_one({"username": username})
    if not user_doc:
        return False

    hashed_pw = user_doc["hashed_password"]
    if check_password(password, hashed_pw):
        return True
    return False

# ------------------------------------------------------------------------------
# 3) Log user actions (skip, add, edit, delete) 
#    to BOTH the content item and the user's record
# ------------------------------------------------------------------------------
def log_user_action(content_id, action, username):
    """Append a record with username, action, and timestamp 
       to both the content document and the user's activity_logs."""
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 3a) Log to the content_data 'users' array
    content_collection.update_one(
        {"content_id": content_id},
        {
            "$push": {
                "users": {
                    "username": username,
                    "action": action,
                    "datetime": timestamp_str
                }
            }
        },
        upsert=True
    )

    # 3b) Also log in the user's own doc:
    users_collection.update_one(
        {"username": username},
        {
            "$push": {
                "activity_logs": {
                    "content_id": content_id,
                    "action": action,
                    "datetime": timestamp_str
                }
            }
        }
    )

# ------------------------------------------------------------------------------
# 4) App Title
# ------------------------------------------------------------------------------
st.write("Running Streamlit version:", st.__version__)
st.title("📖 Fetch & Edit Content from MongoDB (with Registration/Login)")

# ------------------------------------------------------------------------------
# 5) Check if user is authenticated in session
# ------------------------------------------------------------------------------
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = None

# ------------------------------------------------------------------------------
# 6) If user is not logged in, show register/login
# ------------------------------------------------------------------------------
if not st.session_state["logged_in"]:
    auth_choice = st.radio("Choose an action:", ["Login", "Register"])

    if auth_choice == "Register":
        reg_username = st.text_input("New Username:", key="reg_user")
        reg_password = st.text_input("New Password:", type="password", key="reg_pass")
        if st.button("Register"):
            if reg_username.strip() and reg_password.strip():
                success = register_user(reg_username, reg_password)
                if success:
                    st.success("User registered successfully! Please login now.")
                else:
                    st.error("Username already exists. Please choose a different name.")
            else:
                st.error("Please enter both username and password.")

    elif auth_choice == "Login":
        log_username = st.text_input("Username:", key="log_user")
        log_password = st.text_input("Password:", type="password", key="log_pass")
        if st.button("Login"):
            if log_username.strip() and log_password.strip():
                success = login_user(log_username, log_password)
                if success:
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = log_username
                    # Without st.experimental_rerun(), the page won't auto-refresh. 
                    # You can do st.stop() after setting session states if you wish:
                    st.stop()
                else:
                    st.error("Invalid username or password.")
            else:
                st.error("Please enter both username and password.")

    st.stop()  # if not logged in, stop here to avoid showing the rest of the app
else:
    st.markdown(f"**Welcome, {st.session_state['username']}!**")

# ------------------------------------------------------------------------------
# 7) Once logged in, the rest of the app is accessible
# ------------------------------------------------------------------------------
username = st.session_state["username"]

# Create or get the "skipped_ids" in session
if "skipped_ids" not in st.session_state:
    st.session_state["skipped_ids"] = []

# ------------------------------------------------------------------------------
# 8) SEARCH BOX
# ------------------------------------------------------------------------------
search_id = st.text_input("Search content_id:")
search_button = st.button("Search")

if search_button:
    found = content_collection.find_one({"content_id": search_id})
    if found:
        st.session_state["current_content_id"] = found["content_id"]
        st.session_state["questions"] = found.get("questions", [])
    else:
        st.error(f"No content found for content_id: {search_id}")

# ------------------------------------------------------------------------------
# 9) AUTO-FETCH LOGIC
# ------------------------------------------------------------------------------
def fetch_next_content():
    """Sets st.session_state["current_content_id"] to the next appropriate item
       (empty questions, else < 6 questions, else from skip list)."""
    query_empty = {
        "questions": {"$size": 0},
        "content_id": {"$nin": st.session_state["skipped_ids"]},
    }
    doc = content_collection.find_one(query_empty)
    if not doc:
        # Next, try doc with questions < 6
        query_lt6 = {
            "$expr": {"$lt": [{"$size": "$questions"}, 6]},
            "content_id": {"$nin": st.session_state["skipped_ids"]},
        }
        doc = content_collection.find_one(query_lt6)
    
    if not doc:
        # Then from skip list if available
        if st.session_state["skipped_ids"]:
            skipped_id = st.session_state["skipped_ids"].pop(0)
            doc = content_collection.find_one({"content_id": skipped_id})
    
    if doc:
        st.session_state["current_content_id"] = doc["content_id"]
        st.session_state["questions"] = doc.get("questions", [])
    else:
        st.warning("No more items. Nothing with empty or < 6 questions, and no skipped items remain.")
        st.stop()

if "current_content_id" not in st.session_state:
    fetch_next_content()

# ------------------------------------------------------------------------------
# 10) SHOW & EDIT THE CURRENT CONTENT
# ------------------------------------------------------------------------------
if "current_content_id" in st.session_state:
    content_data = content_collection.find_one({"content_id": st.session_state["current_content_id"]})
    if content_data:
        st.subheader(f"📜 Retrieved Content (ID: {content_data['content_id']})")

        st.text_area("Content:", value=content_data.get("content", ""), height=300, disabled=True)

        questions_list = content_data.get("questions", [])
        st.write(f"📌 **Total Questions:** {len(questions_list)}")

        # 10a) EDIT/DELETE EXISTING QUESTIONS
        if questions_list:
            st.write("📋 **Existing Questions (Editable):**")
            updated_questions = []
            for idx, q in enumerate(questions_list, start=1):
                st.write(f"**Question {idx}:**")
                
                question_text = st.text_area(
                    f"Edit Question {idx}",
                    value=q["question"],
                    key=f"edit_q_{idx}"
                )
                difficulty = st.selectbox(
                    f"Difficulty Level {idx}",
                    ["easy", "medium", "hard"],
                    index=["easy", "medium", "hard"].index(q["difficulty"]),
                    key=f"edit_d_{idx}"
                )
                answer_text = q.get("answer", "")

                # "Delete this question" checkbox
                delete_flag = st.checkbox(f"Delete question {idx}", key=f"delete_{idx}")

                # Only append to updated list if user does not want to delete
                if not delete_flag:
                    updated_questions.append({
                        "question": question_text,
                        "difficulty": difficulty,
                        "answer": answer_text
                    })
                else:
                    st.warning(f"Marked question {idx} for deletion.")

            if st.button("Save Changes"):
                # Update DB with whatever remains in updated_questions
                content_collection.update_one(
                    {"content_id": content_data["content_id"]},
                    {"$set": {"questions": updated_questions}}
                )

                # If any were deleted, log that
                if len(updated_questions) < len(questions_list):
                    log_user_action(content_data["content_id"], "deleted question(s)", username)

                # If any were edited (text changed, etc.), we also consider that an edit
                if updated_questions != questions_list:
                    log_user_action(content_data["content_id"], "edited questions", username)

                st.success("✅ Changes saved successfully!")
                # Without st.experimental_rerun(), the UI won't auto-refresh.
                # If you'd like to end and let user refresh:
                st.stop()

        # 10b) ADD NEW QUESTION
        st.subheader("📝 Add a New Question")
        new_question = st.text_area("Enter New Question:", height=100)
        new_difficulty = st.selectbox("Select Difficulty Level:", ["easy", "medium", "hard"])

        if st.button("Save Question"):
            if new_question.strip():
                content_collection.update_one(
                    {"content_id": content_data["content_id"]},
                    {
                        "$push": {
                            "questions": {
                                "question": new_question,
                                "difficulty": new_difficulty,
                                "answer": ""
                            }
                        }
                    },
                    upsert=True
                )
                log_user_action(content_data["content_id"], "added question", username)
                st.success("✅ New question added successfully!")
                st.stop()  # end script; user can refresh for updated view
            else:
                st.error("⚠️ Please enter a question before saving!")

# ------------------------------------------------------------------------------
# 11) FETCH NEXT CONTENT (SKIP) BUTTON
# ------------------------------------------------------------------------------
st.subheader("🔄 Fetch Next Content (Skip this one)")
if st.button("Fetch Next Content"):
    current_id = st.session_state.get("current_content_id")
    if current_id:
        st.session_state["skipped_ids"].append(current_id)
        log_user_action(current_id, "skipped", username)
        st.session_state.pop("current_content_id", None)
        st.session_state.pop("questions", None)
    st.stop()  # user can refresh to load next
