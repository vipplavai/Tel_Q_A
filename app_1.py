import streamlit as st
from pymongo import MongoClient

# Show the actual Streamlit version (just for debugging)
st.write("Running Streamlit version:", st.__version__)

# Initialize connection to MongoDB
@st.cache_resource
def init_connection():
    return MongoClient(st.secrets["mongo"]["uri"])

client = init_connection()
db = client["Q_and_A"]  # Database Name
collection = db["content_data"]  # Collection Name

# Streamlit UI
st.title("📖 Fetch & Edit Content from MongoDB")

# ------------------------------------------------------------------------------
# 1) SEARCH BOX & LOGIC
# ------------------------------------------------------------------------------
st.write("Enter a content_id to load it directly, otherwise the app will auto-fetch the next item with empty questions or < 6 questions.")
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
# 2) AUTO-FETCH CONTENT 
#    First priority: questions array is empty
#    Second priority: questions array size < 6
# ------------------------------------------------------------------------------
if "current_content_id" not in st.session_state:
    # 2a) Try to fetch content whose questions array is empty
    content_data = collection.find_one({"questions": {"$size": 0}})

    # 2b) If none found, fetch the next doc with < 6 questions
    if not content_data:
        content_data = collection.find_one({"$expr": {"$lt": [{"$size": "$questions"}, 6]}})

    if content_data:
        st.session_state["current_content_id"] = content_data["content_id"]
        st.session_state["questions"] = content_data.get("questions", [])
    else:
        st.warning("No documents found with an empty or < 6 questions array.")
        st.stop()

# ------------------------------------------------------------------------------
# 3) SHOW FETCHED CONTENT
# ------------------------------------------------------------------------------
if "current_content_id" in st.session_state:
    content_data = collection.find_one({"content_id": st.session_state["current_content_id"]})
    if content_data:
        st.subheader(f"📜 Retrieved Content (ID: {content_data['content_id']})")
        st.text_area("Content:", value=content_data["content"], height=300, disabled=True)

        questions_list = content_data.get("questions", [])
        st.write(f"📌 **Total Questions:** {len(questions_list)}")

        # ----------------------------------------------------------------------
        # EDIT EXISTING QUESTIONS
        # ----------------------------------------------------------------------
        if questions_list:
            st.write("📋 **Existing Questions (Editable):**")
            updated_questions = []
            for index, q in enumerate(questions_list, start=1):
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
                updated_questions.append({
                    "question": question_text,
                    "difficulty": difficulty,
                    "answer": q.get("answer", "")
                })

            if st.button("Save Changes"):
                collection.update_one(
                    {"content_id": st.session_state["current_content_id"]},
                    {"$set": {"questions": updated_questions}}
                )
                st.success("✅ Changes saved successfully!")
                st.rerun()

        # ----------------------------------------------------------------------
        # ADD NEW QUESTION
        # ----------------------------------------------------------------------
        st.subheader("📝 Add a New Question")
        new_question = st.text_area("Enter New Question:", height=100)
        new_difficulty = st.selectbox("Select Difficulty Level:", ["easy", "medium", "hard"])

        if st.button("Save Question"):
            if new_question.strip():
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
                st.rerun()
            else:
                st.error("⚠️ Please enter a question before saving!")

# ------------------------------------------------------------------------------
# 4) FETCH NEXT CONTENT BUTTON
# ------------------------------------------------------------------------------
st.subheader("🔄 Fetch Next Content")
if st.button("Fetch Next Content"):
    st.session_state.pop("current_content_id", None)
    st.session_state.pop("questions", None)
    st.rerun()
