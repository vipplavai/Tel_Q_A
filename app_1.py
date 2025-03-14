import streamlit as st
from pymongo import MongoClient

# 1) Import these internal objects for the manual rerun hack
from streamlit.runtime.scriptrunner import script_run_context as src
from streamlit.runtime.scriptrunner.script_run_context import RerunException

st.write("Running Streamlit version:", st.__version__)

# 2) Define our custom rerun function
def rerun():
    """Force a Streamlit script rerun by raising an internal RerunException."""
    raise RerunException(src.get_script_run_ctx())

# Initialize connection to MongoDB
@st.cache_resource
def init_connection():
    return MongoClient(st.secrets["mongo"]["uri"])

client = init_connection()
db = client["Q_and_A"]  # Database Name
collection = db["content_data"]  # Collection Name

st.title("📖 Fetch & Edit Content from MongoDB")

# ------------------------------------------------------------------------------
# 1) SEARCH BOX & LOGIC
# ------------------------------------------------------------------------------
st.write("Use the box below to fetch a specific content_id, or leave it blank to auto-fetch the next content with < 6 questions.")
search_id = st.text_input("Enter content_id:")
search_button = st.button("Search")

if search_button:
    # Attempt to find a record matching the user-input content_id
    result = collection.find_one({"content_id": search_id})
    if result:
        st.session_state["current_content_id"] = result["content_id"]
        st.session_state["questions"] = result.get("questions", [])
    else:
        st.error("No content found for the given content_id.")

# ------------------------------------------------------------------------------
# 2) AUTO-FETCH CONTENT WITH questions < 6 (if none is currently in session)
# ------------------------------------------------------------------------------
if "current_content_id" not in st.session_state:
    content_data = collection.find_one({"$expr": {"$lt": [{"$size": "$questions"}, 6]}})
    if content_data:
        st.session_state["current_content_id"] = content_data["content_id"]
        st.session_state["questions"] = content_data.get("questions", [])
    else:
        st.warning("No documents found with less than 6 questions in the collection.")
        st.stop()  # Stop execution if no data is found

# ------------------------------------------------------------------------------
# 3) DISPLAY & EDIT LOGIC
# ------------------------------------------------------------------------------
content_data = collection.find_one({"content_id": st.session_state["current_content_id"]})
if content_data:
    st.subheader(f"📜 Retrieved Content (ID: {content_data['content_id']})")
    st.text_area("Content:", value=content_data["content"], height=300, disabled=True)

    current_questions = content_data.get("questions", [])
    st.write(f"📌 **Total Questions:** {len(current_questions)}")

    # ------------------------------------------------------------------------------
    # EDIT EXISTING QUESTIONS
    # ------------------------------------------------------------------------------
    if current_questions:
        st.write("📋 **Existing Questions (Editable):**")
        updated_questions = []
        
        for index, q in enumerate(current_questions, start=1):
            st.write(f"**Question {index}:**")
            question_text = st.text_area(
                f"Edit Question {index}",
                value=q["question"],
                key=f"edit_q_{index}"
            )
            difficulty = st.selectbox(
                f"Difficulty Level {index}",
                ["easy", "medium", "hard"],
                index=["easy", "medium", "hard"].index(q["difficulty"]),
                key=f"edit_d_{index}"
            )
            answer_text = q.get("answer", "")

            updated_questions.append({
                "question": question_text,
                "difficulty": difficulty,
                "answer": answer_text
            })

        if st.button("Save Changes"):
            collection.update_one(
                {"content_id": st.session_state["current_content_id"]},
                {"$set": {"questions": updated_questions}}
            )
            st.success("✅ Changes saved successfully!")

            # Check if we now have >= 6 questions. If so, auto-fetch next
            if len(updated_questions) >= 6:
                st.session_state.pop("current_content_id", None)
                st.session_state.pop("questions", None)
                st.info("This content has 6 or more questions. Fetching next...")
                rerun()
            else:
                rerun()

    # ------------------------------------------------------------------------------
    # ADD NEW QUESTION
    # ------------------------------------------------------------------------------
    st.subheader("📝 Add a New Question")
    new_question = st.text_area("Enter New Question:", height=100)
    new_difficulty = st.selectbox("Select Difficulty Level:", ["easy", "medium", "hard"])

    if st.button("Save Question"):
        if new_question.strip():
            # Push new question into the array
            collection.update_one(
                {"content_id": st.session_state["current_content_id"]},
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
            st.success("✅ New question added successfully!")

            # Check how many questions exist now
            latest_doc = collection.find_one({"content_id": st.session_state["current_content_id"]})
            if len(latest_doc.get("questions", [])) >= 6:
                st.session_state.pop("current_content_id", None)
                st.session_state.pop("questions", None)
                st.info("This content now has 6 or more questions. Fetching next...")
                rerun()
            else:
                rerun()
        else:
            st.error("⚠️ Please enter a question before saving!")

# ------------------------------------------------------------------------------
# 4) FETCH NEXT CONTENT MANUALLY (OPTIONAL BUTTON)
# ------------------------------------------------------------------------------
st.subheader("🔄 Fetch Next Content (with < 6 questions)")
if st.button("Fetch Next Content"):
    st.session_state.pop("current_content_id", None)
    st.session_state.pop("questions", None)
    rerun()
