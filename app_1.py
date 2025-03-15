import streamlit as st
from pymongo import MongoClient
from datetime import datetime
import bcrypt  # Requires "pip install bcrypt"

# ------------------------------------------------------------------------------
# 0) Translation Data & Instructions
# ------------------------------------------------------------------------------
LANG_TEXT = {
    "English": {
        "app_title": "📖 Question Inserter Tool @vipplavAI",
        "choose_action": "Choose an action:",
        "login_label": "Login",
        "register_label": "Register",
        "new_username": "New Username:",
        "new_password": "New Password:",
        "register_btn": "Register",
        "register_success": "User registered successfully! Please login now.",
        "register_error": "Username already exists. Please choose a different name.",
        "login_username": "Username:",
        "login_password": "Password:",
        "login_btn": "Login",
        "login_error": "Invalid username or password.",
        "login_fill_error": "Please enter both username and password.",
        "fill_error": "Please enter both username and password.",
        "welcome_user": "Welcome, {username}!",
        "search_id": "Search content_id:",
        "search_btn": "Search",
        "search_err": "No content found for content_id: {search_id}",
        "no_more_items": "No more items. Nothing with empty or < 6 questions, and no skipped items remain.",
        "content_id_retrieved": "📜 Retrieved Content (ID: {content_id})",
        "content_box_label": "Content:",
        "total_questions": "📌 **Total Questions:** {count}",
        "existing_questions": "📋 **Existing Questions (Editable):**",
        "edit_question_label": "Edit Question {idx}",
        "difficulty_level_label": "Difficulty Level {idx}",
        "delete_question_label": "Delete question {idx}",
        "delete_warning": "Marked question {idx} for deletion.",
        "save_changes_btn": "Save Changes",
        "changes_saved": "✅ Changes saved successfully!",
        "add_new_question_subheader": "📝 Add a New Question",
        "enter_new_q_label": "Enter New Question:",
        "difficulty_select_label": "Select Difficulty Level:",
        "save_question_btn": "Save Question",
        "empty_q_error": "⚠️ Please enter a question before saving!",
        "fetch_next_subheader": "🔄 Fetch Next Content (Skip this one)",
        "fetch_next_btn": "Fetch Next Content",
        "instructions_btn": "Instructions"
    },
    "Telugu": {
        "app_title": "📖 ప్రశ్న ఇన్సర్టర్ సాధనం @vipplavAI",
        "choose_action": "ఒక చర్యను ఎంచుకోండి:",
        "login_label": "లాగిన్",
        "register_label": "రిజిస్టర్",
        "new_username": "క్రొత్త యూజర్ పేరు:",
        "new_password": "క్రొత్త పాస్వర్డ్:",
        "register_btn": "రిజిస్టర్",
        "register_success": "వాడుకరి విజయవంతంగా రిజిస్టర్ అయ్యారు! దయచేసి లాగిన్ అవండి.",
        "register_error": "యూజర్ పేరు ఇప్పటికే ఉంది. దయచేసి వేరే పేరు ఎంచుకోండి.",
        "login_username": "యూజర్ పేరు:",
        "login_password": "పాస్వర్డ్:",
        "login_btn": "లాగిన్",
        "login_error": "చెల్లని యూజర్ పేరు లేదా పాస్వర్డ్.",
        "login_fill_error": "దయచేసి వినియోగదారు పేరు మరియు పాస్‌వర్డ్ రెండింటినీ నమోదు చేయండి.",
        "fill_error": "దయచేసి వినియోగదారు పేరు మరియు పాస్‌వర్డ్ రెండింటినీ నమోదు చేయండి.",
        "welcome_user": "సుస్వాగతం, {username}!",
        "search_id": "కంటెంట్ ఐడి వెతకండి:",
        "search_btn": "వెతకండి",
        "search_err": "ఈ కంటెంట్ ఐడికి `{search_id}` అనువైన విషయం లేదు.",
        "no_more_items": "మరిన్ని అంశాలు లేవు. ఖాళీ ప్రశ్నలు లేవు లేదా < 6 ప్రశ్నలు లేవు, అలాగే స్కిప్ చేసినవి లేవు.",
        "content_id_retrieved": "📜 తిరిగి పొందిన కంటెంట్ (ID: {content_id})",
        "content_box_label": "కంటెంట్:",
        "total_questions": "📌 **మొత్తం ప్రశ్నలు:** {count}",
        "existing_questions": "📋 **ఈ ప్రశ్నలను మార్పు చేయండి:**",
        "edit_question_label": "ప్రశ్న {idx}ని మార్చండి",
        "difficulty_level_label": "సమస్య స్థాయి {idx}",
        "delete_question_label": "ఈ ప్రశ్నను తొలగించు {idx}",
        "delete_warning": "{idx} ప్రశ్న తొలగించబడింది.",
        "save_changes_btn": "మార్పులు సేవ్ చేయండి",
        "changes_saved": "✅ మార్పులు విజయవంతంగా సేవ్ అయ్యాయి!",
        "add_new_question_subheader": "📝 కొత్త ప్రశ్న చేర్చండి",
        "enter_new_q_label": "కొత్త ప్రశ్నను నమోదు చేయండి:",
        "difficulty_select_label": "సమస్య స్థాయిని ఎంచుకోండి:",
        "save_question_btn": "ప్రశ్నని సేవ్ చేయండి",
        "empty_q_error": "⚠️ సేవ్ చేసే ముందు దయచేసి ఒక ప్రశ్నను నమోదు చేయండి!,",
        "fetch_next_subheader": "🔄 మరో కంటెంట్ తీసుకురండి (ఇది స్కిప్ చేయండి)",
        "fetch_next_btn": "తదుపరి కంటెంట్ తీసుకురండి",
        "instructions_btn": "నిర్దేశాలు"
    }
}

INSTRUCTIONS = {
    "English": """\
3. Framing Quality Questions in Three Segments

Once the content is displayed, questions must be framed in three difficulty levels:

**Easy Questions (Single-word answers)**
- Goal: To assess basic recall of key terms, names, or definitions.
- Example Format:
'''
Q: What is the capital of France?
A: Paris
'''

**Medium Questions (2-3 line answers)**
- Goal: To check comprehension and encourage slightly detailed responses.
- Example Format:
'''
Q: Why is the Eiffel Tower considered an architectural marvel?
A: The Eiffel Tower is a marvel because it was the tallest structure at the time 
   of its completion and is made of iron lattice, showcasing unique engineering.
'''

**Hard Questions (4-6 line answers)**
- Goal: To encourage critical thinking and detailed explanations.
- Example Format:
'''
Q: How did the construction of the Eiffel Tower impact Paris’s tourism industry?
A: The Eiffel Tower significantly boosted tourism in Paris by becoming an iconic landmark. 
   Over the years, it attracted millions of visitors, contributed to the economy, 
   and became a symbol of France’s artistic and engineering excellence.
'''

4. Adding or Editing Questions

At least 6 questions must be added per content piece.

Steps to Add Questions:
1. Navigate to the Question Management Section.
2. Click on Add New Question.
3. Select the Question Difficulty Level (Easy, Medium, Hard).
4. Enter the Question and Answer in the respective fields.
5. Click Save Question to store it in the system.
6. Repeat this process until a minimum of 6 questions are added.

Steps to Edit a Question:
1. Navigate to the Question List under the relevant content.
2. Click on the Edit button next to the question you want to modify.
3. Make the necessary changes to the question or answer.
4. Click Save Changes to update the question.

5. Reviewing and Finalizing Questions

Before submission, ensure all framed questions meet quality standards:
✔ Are the questions clear and concise?
✔ Do the answers match the difficulty level?
✔ Are there at least 6 questions (2 per level)?
✔ Do they cover different aspects of the content?

Once reviewed, click Submit Questions to finalize.
""",
    "Telugu": """\
3. మూడు విభాగాలలో నాణ్యమైన ప్రశ్నలను రూపొందించడం

కంటెంట్ ప్రదర్శించబడిన తర్వాత, ప్రశ్నలను మూడు క్లిష్ట స్థాయిలలో రూపొందించాలి:

**సులభమైన ప్రశ్నలు (ఒకే-పద సమాధానాలు)**
- లక్ష్యం: కీలక పదాలు, పేర్లు లేదా నిర్వచనాల ప్రాథమిక జ్ఞాపకాలను అంచనా వేయడానికి.
- ఉదాహరణ ఫార్మాట్:
'''
ప్ర: ఫ్రాన్స్ రాజధాని ఏమిటి?
జ: పారిస్
'''

**మధ్యస్థ ప్రశ్నలు (2-3 లైన్ సమాధానాలు)**
- లక్ష్యం: అవగాహనను తనిఖీ చేయడానికి మరియు కొద్దిగా వివరణాత్మక ప్రతిస్పందనలను ప్రోత్సహించడానికి.
- ఉదాహరణ ఫార్మాట్:
'''
ప్ర: ఐఫిల్ టవర్‌ను నిర్మాణ అద్భుతంగా ఎందుకు పరిగణిస్తారు?
జ: ఐఫిల్ టవర్ ఒక అద్భుతం ఎందుకంటే ఇది దాని నిర్మాణం పూర్తయిన సమయంలో 
   ఎత్తైన నిర్మాణం మరియు ఇనుప లాటిస్‌తో తయారు చేయబడింది, 
   ఇది ప్రత్యేకమైన ఇంజనీరింగ్‌ను ప్రదర్శిస్తుంది.
'''

**కఠినమైన ప్రశ్నలు (4-6 లైన్ సమాధానాలు)**
- లక్ష్యం: విమర్శనాత్మక ఆలోచన మరియు వివరణాత్మక వివరణలను ప్రోత్సహించడానికి.
- ఉదాహరణ ఫార్మాట్:
'''
ప్ర: ఐఫిల్ టవర్ నిర్మాణం పారిస్ పర్యాటక పరిశ్రమను ఎలా ప్రభావితం చేసింది?
జ: ఐఫిల్ టవర్ పారిస్‌లో పర్యాటకాన్ని ఒక ఐకానిక్ ల్యాండ్‌మార్క్‌గా మార్చడం ద్వారా గణనీయంగా పెంచింది. 
   సంవత్సరాలుగా, ఇది మిలియన్ల మంది సందర్శకులను ఆకర్షించింది, ఆర్థిక వ్యవస్థకు దోహదపడింది 
   మరియు ఫ్రాన్స్ యొక్క కళాత్మక మరియు ఇంజనీరింగ్ నైపుణ్యానికి చిహ్నంగా మారింది.
'''

4. ప్రశ్నలను జోడించడం లేదా సవరించడం

కంటెంట్ ముక్కకు కనీసం 6 ప్రశ్నలు జోడించాలి.

ప్రశ్నలను జోడించడానికి దశలు:
1. ప్రశ్న నిర్వహణ విభాగానికి నావిగేట్ చేయండి.
2. కొత్త ప్రశ్నను జోడించుపై క్లిక్ చేయండి.
3. ప్రశ్న క్లిష్టత స్థాయిని ఎంచుకోండి (సులభమైన, మధ్యస్థమైన, కఠినమైనది).
4. సంబంధించిన ఫీల్డ్‌లలో ప్రశ్న మరియు సమాధానాన్ని నమోదు చేయండి.
5. సిస్టమ్‌లో నిల్వ చేయడానికి ప్రశ్నను సేవ్ చేయి క్లిక్ చేయండి.
6. కనీసం 6 ప్రశ్నలు జోడించబడే వరకు ఈ ప్రక్రియను పునరావృతం చేయండి.

ప్రశ్నను సవరించడానికి దశలు:
1. సంబంధించిన కంటెంట్ కింద ప్రశ్నల జాబితాకు నావిగేట్ చేయండి.
2. మీరు సవరించాలనుకునే ప్రశ్న పక్కన ఉన్న సవరించు బటన్‌పై క్లిక్ చేయండి.
3. ప్రశ్న లేదా సమాధానానికి అవసరమైన మార్పులు చేయండి.
4. ప్రశ్నను నవీకరించడానికి మార్పులను సేవ్ చేయి క్లిక్ చేయండి.

5. ప్రశ్నలను సమీక్షించడం మరియు తుది రూపం ఇవ్వడం

సమర్పణకు ముందు, ఫ్రేమ్ చేయబడిన అన్ని ప్రశ్నలు నాణ్యతా ప్రమాణాలకు అనుగుణంగా ఉన్నాయని నిర్ధారించుకోండి:
✔ ప్రశ్నలు స్పష్టంగా మరియు సంక్షిప్తంగా ఉన్నాయా?
✔ సమాధానాలు క్లిష్టత స్థాయికి సరిపోతాయా?
✔ కనీసం 6 ప్రశ్నలు (ప్రతి స్థాయికి 2) ఉన్నాయా?
✔ అవి కంటెంట్ యొక్క విభిన్న అంశాలను కవర్ చేస్తాయా?

సమీక్షించిన తర్వాత, తుది రూపం ఇవ్వడానికి ప్రశ్నలను సమర్పించు క్లిక్ చేయండి.
"""
}


# ------------------------------------------------------------------------------
# 1) Initialize connection to MongoDB
# ------------------------------------------------------------------------------
@st.cache_resource
def init_connection():
    return MongoClient(st.secrets["mongo"]["uri"])

client = init_connection()
db = client["Q_and_A"]

content_collection = db["content_data"]
users_collection = db["users"]

# ------------------------------------------------------------------------------
# 2) Authentication Helpers
# ------------------------------------------------------------------------------
def hash_password(password: str) -> bytes:
    """Generate salted hash for the given password."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

def check_password(password: str, hashed: bytes) -> bool:
    """Compare a plain password with the hashed password."""
    return bcrypt.checkpw(password.encode("utf-8"), hashed)

def register_user(username: str, password: str) -> bool:
    existing_user = users_collection.find_one({"username": username})
    if existing_user:
        return False
    hashed_pw = hash_password(password)
    new_user = {
        "username": username,
        "hashed_password": hashed_pw,
        "activity_logs": []
    }
    users_collection.insert_one(new_user)
    return True

def login_user(username: str, password: str) -> bool:
    user_doc = users_collection.find_one({"username": username})
    if not user_doc:
        return False
    hashed_pw = user_doc["hashed_password"]
    return check_password(password, hashed_pw)

def log_user_action(content_id, action, username):
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
# 4) Session State Defaults
# ------------------------------------------------------------------------------
if "language" not in st.session_state:
    st.session_state["language"] = "English"
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = None
if "show_instructions" not in st.session_state:
    st.session_state["show_instructions"] = False
if "skipped_ids" not in st.session_state:
    st.session_state["skipped_ids"] = []

L = LANG_TEXT[st.session_state["language"]]

# ------------------------------------------------------------------------------
# 5) Top Row: Title (left), Language + Instructions (right)
# ------------------------------------------------------------------------------
top_left, top_right = st.columns([6, 2])
with top_left:
    st.title(L["app_title"])

with top_right:
    lang_choice = st.selectbox(
        "Language / భాష:",
        ["English", "Telugu"],
        index=0 if st.session_state["language"] == "English" else 1
    )
    if lang_choice != st.session_state["language"]:
        st.session_state["language"] = lang_choice
        L = LANG_TEXT[st.session_state["language"]]

    if st.button(L["instructions_btn"]):
        st.session_state["show_instructions"] = not st.session_state["show_instructions"]

# ------------------------------------------------------------------------------
# 6) Show instructions if toggled
# ------------------------------------------------------------------------------
if st.session_state["show_instructions"]:
    st.markdown("----")
    st.markdown("## Instructions")
    st.markdown(INSTRUCTIONS[st.session_state["language"]])
    st.markdown("----")

# ------------------------------------------------------------------------------
# 7) Login / Register if not logged in
# ------------------------------------------------------------------------------
if not st.session_state["logged_in"]:
    auth_choice = st.radio(L["choose_action"], [L["login_label"], L["register_label"]], key="auth_radio")
    
    if auth_choice == L["register_label"]:
        reg_username = st.text_input(L["new_username"], key="reg_user")
        reg_password = st.text_input(L["new_password"], type="password", key="reg_pass")
        if st.button(L["register_btn"], key="register_btn"):
            if reg_username.strip() and reg_password.strip():
                success = register_user(reg_username, reg_password)
                if success:
                    st.success(L["register_success"])
                else:
                    st.error(L["register_error"])
            else:
                st.error(L["fill_error"])
    else:
        log_username = st.text_input(L["login_username"], key="login_user")
        log_password = st.text_input(L["login_password"], type="password", key="login_pass")
        if st.button(L["login_btn"], key="login_btn"):
            if log_username.strip() and log_password.strip():
                success = login_user(log_username, log_password)
                if success:
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = log_username
                    st.session_state["show_instructions"] = True
                    st.stop()
                else:
                    st.error(L["login_error"])
            else:
                st.error(L["login_fill_error"])
    
    st.stop()
else:
    st.markdown(L["welcome_user"].format(username=st.session_state["username"]))

# ------------------------------------------------------------------------------
# 8) SEARCH BOX
# ------------------------------------------------------------------------------
search_id = st.text_input(L["search_id"], key="search_box")
search_button = st.button(L["search_btn"], key="search_btn")
if search_button:
    found = content_collection.find_one({"content_id": search_id})
    if found:
        st.session_state["current_content_id"] = found["content_id"]
        st.session_state["questions"] = found.get("questions", [])
    else:
        st.error(L["search_err"].format(search_id=search_id))

# ------------------------------------------------------------------------------
# 9) AUTO-FETCH LOGIC
# ------------------------------------------------------------------------------
def fetch_next_content():
    query_empty = {
        "questions": {"$size": 0},
        "content_id": {"$nin": st.session_state["skipped_ids"]},
    }
    doc = content_collection.find_one(query_empty)
    if not doc:
        query_lt6 = {
            "$expr": {"$lt": [{"$size": "$questions"}, 6]},
            "content_id": {"$nin": st.session_state["skipped_ids"]},
        }
        doc = content_collection.find_one(query_lt6)

    if not doc:
        if st.session_state["skipped_ids"]:
            skipped_id = st.session_state["skipped_ids"].pop(0)
            doc = content_collection.find_one({"content_id": skipped_id})

    if doc:
        st.session_state["current_content_id"] = doc["content_id"]
        st.session_state["questions"] = doc.get("questions", [])
    else:
        st.warning(L["no_more_items"])
        st.stop()

if "current_content_id" not in st.session_state:
    fetch_next_content()

# ------------------------------------------------------------------------------
# 10) SHOW & EDIT CURRENT CONTENT
# ------------------------------------------------------------------------------
if "current_content_id" in st.session_state:
    content_data = content_collection.find_one({"content_id": st.session_state["current_content_id"]})
    if content_data:
        st.subheader(L["content_id_retrieved"].format(content_id=content_data["content_id"]))
        st.text_area(L["content_box_label"], value=content_data.get("content", ""), height=300, disabled=True)

        questions_list = content_data.get("questions", [])
        st.write(L["total_questions"].format(count=len(questions_list)))

        # 10a) EDIT/DELETE
        if questions_list:
            st.write(L["existing_questions"])
            updated_questions = []
            for idx, q in enumerate(questions_list, start=1):
                st.write(f"**{L['edit_question_label'].format(idx=idx)}**")

                question_text = st.text_area(
                    f"{L['edit_question_label'].format(idx=idx)}",
                    value=q["question"],
                    key=f"edit_q_{idx}"
                )
                diff_options = ["easy", "medium", "hard"]
                difficulty_index = diff_options.index(q["difficulty"])
                difficulty_label = L["difficulty_level_label"].format(idx=idx)
                difficulty_choice = st.selectbox(
                    difficulty_label,
                    diff_options,
                    index=difficulty_index,
                    key=f"edit_d_{idx}"
                )
                answer_text = q.get("answer", "")

                # "Delete question" checkbox
                delete_flag = st.checkbox(L["delete_question_label"].format(idx=idx), key=f"delete_{idx}")
                if not delete_flag:
                    updated_questions.append({
                        "question": question_text,
                        "difficulty": difficulty_choice,
                        "answer": answer_text
                    })
                else:
                    st.warning(L["delete_warning"].format(idx=idx))

            if st.button(L["save_changes_btn"], key="save_changes_btn"):
                content_collection.update_one(
                    {"content_id": content_data["content_id"]},
                    {"$set": {"questions": updated_questions}}
                )
                # Log user actions
                if len(updated_questions) < len(questions_list):
                    log_user_action(content_data["content_id"], "deleted question(s)", st.session_state["username"])
                if updated_questions != questions_list:
                    log_user_action(content_data["content_id"], "edited questions", st.session_state["username"])

                st.success(L["changes_saved"])
                # Do NOT call st.stop() here, so the rest of the page (including "Fetch Next") is visible.

        # 10b) ADD NEW
        st.subheader(L["add_new_question_subheader"])
        new_question = st.text_area(L["enter_new_q_label"], height=100, key="new_ques")
        new_difficulty = st.selectbox(L["difficulty_select_label"], ["easy", "medium", "hard"], key="new_diff")

        if st.button(L["save_question_btn"], key="save_question_btn"):
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
                log_user_action(content_data["content_id"], "added question", st.session_state["username"])
                st.success(L["changes_saved"])
                # Again, do NOT call st.stop() so the "Fetch Next Content" button is shown.
            else:
                st.error(L["empty_q_error"])

# ------------------------------------------------------------------------------
# 11) FETCH NEXT (SKIP)
# ------------------------------------------------------------------------------
st.subheader(L["fetch_next_subheader"])
if st.button(L["fetch_next_btn"], key="fetch_next_btn"):
    current_id = st.session_state.get("current_content_id")
    if current_id:
        st.session_state["skipped_ids"].append(current_id)
        log_user_action(current_id, "skipped", st.session_state["username"])
        st.session_state.pop("current_content_id", None)
        st.session_state.pop("questions", None)
    st.stop()
