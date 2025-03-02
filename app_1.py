import streamlit as st
from pymongo import MongoClient

# Initialize connection to MongoDB
@st.cache_resource
def init_connection():
    return MongoClient(st.secrets["mongo"]["uri"])

client = init_connection()
db = client["Q_and_A"]  # Database Name
collection = db["content_data"]  # Collection Name

# Streamlit UI
st.title("📖 Fetch & Edit Content from MongoDB")

# Automatically Fetch Content Where ques_not_avail = True
if "current_content_id" not in st.session_state:
    content_data = collection.find_one({"ques_not_avail": True})
    
    if content_data:
        st.session_state["current_content_id"] = content_data["content_id"]
        st.session_state["questions"] = content_data.get("questions", [])

# Show Fetched Content
if "current_content_id" in st.session_state:
    content_data = collection.find_one({"content_id": st.session_state["current_content_id"]})

    if content_data:
        st.subheader(f"📜 Retrieved Content (ID: {content_data['content_id']})")
        st.text_area("Content:", value=content_data["content"], height=300, disabled=True)

        st.write(f"📌 **Total Questions:** {len(content_data.get('questions', []))}")

        # Display Existing Questions with Edit Option
        if len(content_data["questions"]) > 0:
            st.write("📋 **Existing Questions (Editable):**")
            updated_questions = []
            for index, q in enumerate(content_data["questions"], start=1):
                st.write(f"**Question {index}:**")
                question_text = st.text_area(f"Edit Question {index}", value=q["question"], key=f"edit_q_{index}")
                difficulty = st.selectbox(
                    f"Difficulty Level {index}", 
                    ["easy", "medium", "hard"], 
                    index=["easy", "medium", "hard"].index(q["difficulty"]),
                    key=f"edit_d_{index}"
                )

                updated_questions.append({"question": question_text, "difficulty": difficulty, "answer": q.get("answer", "")})

            if st.button("Save Changes"):
                collection.update_one(
                    {"content_id": st.session_state["current_content_id"]},
                    {"$set": {"questions": updated_questions}}
                )
                st.success("✅ Changes saved successfully!")
                st.rerun()

        # Add New Question Section
        st.subheader("📝 Add a New Question")
        new_question = st.text_area("Enter New Question:", height=100)
        new_difficulty = st.selectbox("Select Difficulty Level:", ["easy", "medium", "hard"])

        if st.button("Save Question"):
            if new_question.strip():
                collection.update_one(
                    {"content_id": st.session_state["current_content_id"]},
                    {
                        "$push": {"questions": {"question": new_question, "difficulty": new_difficulty, "answer": ""}},
                        "$set": {"ques_not_avail": False}  # Update tag once the first question is added
                    },
                    upsert=True
                )
                st.success("✅ New question added successfully!")
                st.rerun()
            else:
                st.error("⚠️ Please enter a question before saving!")

# Fetch Content Button at the Bottom for Convenience
st.subheader("🔄 Fetch Next Content")
if st.button("Fetch Next Content"):
    st.session_state.pop("current_content_id", None)  # Clear current state
    st.rerun()
