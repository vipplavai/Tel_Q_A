import streamlit as st
from pymongo import MongoClient
from datetime import datetime

# ------------------------------------------------------------------------------
# 1) MongoDB CONNECTION INITIALIZATION
# ------------------------------------------------------------------------------
@st.cache_resource
def init_connection():
    return MongoClient(st.secrets["mongo"]["uri"])

client = init_connection()
db = client["Q_and_A"]
collection = db["content_data"]

# ------------------------------------------------------------------------------
# 2) FUNCTION: LOG USER ACTIONS
# ------------------------------------------------------------------------------
def log_user_action(username, content_id, action):
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
# 3) FUNCTION: FETCH NEXT CONTENT
# ------------------------------------------------------------------------------
def fetch_next_content():
    """Fetches next content based on priority: empty questions → less than 6 questions → skipped."""
    if "skipped_ids" not in st.session_state:
        st.session_state["skipped_ids"] = []

    query_empty = {"questions": {"$size": 0}, "content_id": {"$nin": st.session_state["skipped_ids"]}}
    doc = collection.find_one(query_empty)

    if not doc:
        query_lt6 = {"$expr": {"$lt": [{"$size": "$questions"}, 6]}, "content_id": {"$nin": st.session_state["skipped_ids"]}}
        doc = collection.find_one(query_lt6)

    if not doc and st.session_state["skipped_ids"]:
        skipped_id = st.session_state["skipped_ids"].pop(0)
        doc = collection.find_one({"content_id": skipped_id})

    if doc:
        st.session_state["current_content_id"] = doc["content_id"]
        st.session_state["questions"] = doc.get("questions", [])
    else:
        st.warning("✅ No more content available to process!")
        st.stop()

# ------------------------------------------------------------------------------
# 4) CONTENT MANAGEMENT FUNCTION
# ------------------------------------------------------------------------------
def content_management():
    """Manages content fetching, editing, adding, and deleting."""
    st.subheader("📖 Q & A Content Manager")

    if "current_content_id" not in st.session_state:
        fetch_next_content()

    if "current_content_id" in st.session_state:
        content_data = collection.find_one({"content_id": st.session_state["current_content_id"]})
        if content_data:
            st.subheader(f"📜 Content (ID: {content_data['content_id']})")
            st.text_area("Content:", value=content_data.get("content", ""), height=300, disabled=True)

            questions_list = content_data.get("questions", [])
            st.write(f"📌 **Total Questions:** {len(questions_list)}")

            # 4a) EDIT & DELETE QUESTIONS
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
                collection.update_one({"content_id": content_data["content_id"]}, {"$set": {"questions": updated_questions}})
                log_user_action(st.session_state["authenticated_user"], content_data["content_id"], "edited questions")
                st.success("✅ Changes saved successfully!")
                st.rerun()

            if delete_indices:
                if st.button("Delete Selected Questions"):
                    new_questions = [q for i, q in enumerate(questions_list) if i not in delete_indices]
                    collection.update_one({"content_id": content_data["content_id"]}, {"$set": {"questions": new_questions}})
                    log_user_action(st.session_state["authenticated_user"], content_data["content_id"], "deleted questions")
                    st.success("✅ Selected questions deleted successfully!")
                    st.rerun()

            # 4b) ADD NEW QUESTION
            new_question = st.text_area("Enter New Question:", height=100)
            new_difficulty = st.selectbox("Select Difficulty Level:", ["easy", "medium", "hard"])
            if st.button("Save Question"):
                if new_question.strip():
                    collection.update_one(
                        {"content_id": content_data["content_id"]},
                        {"$push": {"questions": {"question": new_question, "difficulty": new_difficulty, "answer": ""}}},
                        upsert=True
                    )
                    log_user_action(st.session_state["authenticated_user"], content_data["content_id"], "added question")
                    st.success("✅ New question added successfully!")
                    st.rerun()
                else:
                    st.error("⚠ Please enter a question before saving!")

    # Skip content
    if st.button("Fetch Next Content"):
        st.session_state["skipped_ids"].append(st.session_state["current_content_id"])
        log_user_action(st.session_state["authenticated_user"], st.session_state["current_content_id"], "skipped")
        st.session_state.pop("current_content_id")
        st.session_state.pop("questions", None)
        st.rerun()
