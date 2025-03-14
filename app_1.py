import streamlit as st
from pymongo import MongoClient
from datetime import datetime

# For debugging, see actual Streamlit version
st.write("Running Streamlit version:", st.__version__)

# ------------------------------------------------------------------------------
# 0) USERNAME PROMPT (MUST ENTER BEFORE PROCEEDING)
# ------------------------------------------------------------------------------
username = st.text_input("Enter your username to proceed:")
if not username.strip():
    st.warning("Please enter a username to continue.")
    st.stop()  # Prevent further interaction if no username provided

# ------------------------------------------------------------------------------
# 1) Initialize connection to MongoDB
# ------------------------------------------------------------------------------
@st.cache_resource
def init_connection():
    return MongoClient(st.secrets["mongo"]["uri"])

client = init_connection()
db = client["Q_and_A"]         # Database Name
collection = db["content_data"]  # Collection Name

# ------------------------------------------------------------------------------
# 2) Helper: Log user actions (skip, add, edit) to the "users" array
# ------------------------------------------------------------------------------
def log_user_action(content_id, action):
    """Append a record with username, action, and timestamp to the 'users' array."""
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    collection.update_one(
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

# ------------------------------------------------------------------------------
# 3) Session init: track "skipped_ids"
# ------------------------------------------------------------------------------
if "skipped_ids" not in st.session_state:
    st.session_state["skipped_ids"] = []

# ------------------------------------------------------------------------------
# 4) SEARCH BOX
# ------------------------------------------------------------------------------
st.title("📖 Fetch & Edit Content from MongoDB")

st.write("Use the box below to fetch a specific content_id directly.")
search_id = st.text_input("Search content_id:")
search_button = st.button("Search")

if search_button:
    found = collection.find_one({"content_id": search_id})
    if found:
        st.session_state["current_content_id"] = found["content_id"]
        st.session_state["questions"] = found.get("questions", [])
    else:
        st.error(f"No content found for content_id: {search_id}")

# ------------------------------------------------------------------------------
# 5) AUTO-FETCH LOGIC
#
# First: content where questions array is empty
# If none found: content with questions < 6
# If none found: use st.session_state["skipped_ids"] (FIFO)
# ------------------------------------------------------------------------------
def fetch_next_content():
    """Sets st.session_state["current_content_id"] to the next appropriate item
       (empty questions, else < 6 questions, else from skip list)."""
    # 5a) Attempt to get doc with empty questions, excluding anything we've skipped
    query_empty = {
        "questions": {"$size": 0},
        "content_id": {"$nin": st.session_state["skipped_ids"]},
    }
    doc = collection.find_one(query_empty)
    if not doc:
        # 5b) If none found, try doc with questions < 6
        query_lt6 = {
            "$expr": {"$lt": [{"$size": "$questions"}, 6]},
            "content_id": {"$nin": st.session_state["skipped_ids"]},
        }
        doc = collection.find_one(query_lt6)
    
    # 5c) If still none found, pull from skip list if available
    if not doc:
        if st.session_state["skipped_ids"]:
            # Take the earliest item we skipped
            skipped_id = st.session_state["skipped_ids"].pop(0)
            doc = collection.find_one({"content_id": skipped_id})
    
    # 5d) If we finally have doc, set it up. Otherwise none is found
    if doc:
        st.session_state["current_content_id"] = doc["content_id"]
        st.session_state["questions"] = doc.get("questions", [])
    else:
        st.warning("No more items. Nothing with empty or < 6 questions, and no skipped items remain.")
        st.stop()

# If no "current_content_id" in session, attempt to fetch next
if "current_content_id" not in st.session_state:
    fetch_next_content()

# ------------------------------------------------------------------------------
# 6) SHOW & EDIT THE CURRENT CONTENT
# ------------------------------------------------------------------------------
if "current_content_id" in st.session_state:
    content_data = collection.find_one({"content_id": st.session_state["current_content_id"]})
    if content_data:
        st.subheader(f"📜 Retrieved Content (ID: {content_data['content_id']})")
        st.text_area("Content:", value=content_data.get("content", ""), height=300, disabled=True)

        questions_list = content_data.get("questions", [])
        st.write(f"📌 **Total Questions:** {len(questions_list)}")

        # 6a) EDIT EXISTING QUESTIONS
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
                updated_questions.append({
                    "question": question_text,
                    "difficulty": difficulty,
                    "answer": answer_text
                })
            
            if st.button("Save Changes"):
                collection.update_one(
                    {"content_id": content_data["content_id"]},
                    {"$set": {"questions": updated_questions}}
                )
                log_user_action(content_data["content_id"], "edited questions")
                st.success("✅ Changes saved successfully!")
                st.rerun()

        # 6b) ADD NEW QUESTION
        st.subheader("📝 Add a New Question")
        new_question = st.text_area("Enter New Question:", height=100)
        new_difficulty = st.selectbox("Select Difficulty Level:", ["easy", "medium", "hard"])

        if st.button("Save Question"):
            if new_question.strip():
                collection.update_one(
                    {"content_id": content_data["content_id"]},
                    {
                        "$push": {
                            "questions": {
                                "question": new_question,
                                "difficulty": new_difficulty,
                                "answer": ""
                            }
                        },
                        "$set": {"ques_not_avail": False}  # optional, if you still track this
                    },
                    upsert=True
                )
                log_user_action(content_data["content_id"], "added question")
                st.success("✅ New question added successfully!")
                st.rerun()
            else:
                st.error("⚠️ Please enter a question before saving!")

# ------------------------------------------------------------------------------
# 7) FETCH NEXT CONTENT (SKIP) BUTTON
#
# If user wants to skip the item entirely (even with zero changes),
# we store the content_id in "skipped_ids" and fetch the next.
# ------------------------------------------------------------------------------
st.subheader("🔄 Fetch Next Content (Skip this one)")
if st.button("Fetch Next Content"):
    current_id = st.session_state.get("current_content_id")
    if current_id:
        # Mark that we "skipped" it
        st.session_state["skipped_ids"].append(current_id)
        log_user_action(current_id, "skipped")
        st.session_state.pop("current_content_id")
        st.session_state.pop("questions", None)
    st.rerun()
