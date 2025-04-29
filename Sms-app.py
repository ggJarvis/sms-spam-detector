import streamlit as st
import pickle
import nltk
import pandas as pd
import time
from nltk.stem.porter import PorterStemmer
from nltk.corpus import stopwords

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')


ps = PorterStemmer()

# page setup
st.set_page_config(
    page_title="Spam Guardian",
    page_icon="🛡️📧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS for styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem !important;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 2rem;
    }
    .subheader {
        font-size: 1.5rem;
        color: #475569;
        text-align: center;
        margin-bottom: 2rem;
    }
    .result-box {
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        text-align: center;
    }
    .spam-box {
        background-color: #FECACA;
        border: 2px solid #DC2626;
    }
    .not-spam-box {
        background-color: #DCFCE7;
        border: 2px solid #16A34A;
    }
    .prediction-label {
        font-size: 2rem;
        font-weight: bold;
    }
    .spam-label {
        color: #DC2626;
    }
    .not-spam-label {
        color: #16A34A;
    }
    .probability-bar {
        height: 2rem;
        margin: 1rem 0;
        border-radius: 0.5rem;
    }
    .footer {
        text-align: center;
        margin-top: 2rem;
        color: #64748B;
    }
    .stTextInput {
        margin-bottom: 1rem;
    }
    .stButton > button {
        width: 100%;
        height: 3rem;
        font-size: 1.2rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


def transform_message(message):
    """Process message for prediction"""
    if not message:
        return ""

    # Convert to lowercase
    message = message.lower()

    # Tokenize
    message = nltk.word_tokenize(message)

    # Remove non-alphanumeric and stopwords
    stop_words = set(stopwords.words('english'))
    message = [word for word in message if word.isalnum() and word not in stop_words]

    # Stemming
    message = [ps.stem(word) for word in message]

    return " ".join(message)


# Load models
@st.cache_resource
def load_models():
    try:
        tfidf = pickle.load(open('vectorizer.pkl', 'rb'))
        model = pickle.load(open('model.pkl', 'rb'))
        return tfidf, model
    except FileNotFoundError:
        st.error(
            "Model files not found. Please make sure 'vectorizer.pkl' and 'model.pkl' are in the correct directory.")
        return None, None


tfidf, model = load_models()



# Main content
st.markdown("<h1 class='main-header'>🛡️📧 Spam Guardian</h1>", unsafe_allow_html=True)
st.markdown("<p class='subheader'>Advanced Email & SMS Spam Detection</p>", unsafe_allow_html=True)

col1, col2 = st.columns([3, 1])

with col1:
    # Text input
    input_message = st.text_area(
        "Enter the message to analyze:",
        height=150,
        key="text_input",
        value=st.session_state.get("sample_text", "")
    )

with col2:
    st.markdown("<br><br>", unsafe_allow_html=True)
    # Statistics
    st.markdown("### 📊 Quick Stats")
    if input_message:
        word_count = len(input_message.split())
        char_count = len(input_message)
        exclamation_count = input_message.count('!')
        url_count = input_message.lower().count('http')

        st.write(f"**Words:** {word_count}")
        st.write(f"**Characters:** {char_count}")
        st.write(f"**Exclamations:** {exclamation_count}")
        st.write(f"**URLs:** {url_count}")

# Analysis button
analyze_button = st.button('🔍 Analyze Message', use_container_width=True)

# Create a container for results
result_container = st.container()

if analyze_button and input_message:
    with st.spinner('Analyzing message...'):
        # Add a small delay to show the spinning animation
        time.sleep(0.5)

        # Process message
        transformed_message = transform_message(input_message)

        if transformed_message:
            # Vectorize
            vector_input = tfidf.transform([transformed_message])

            # Predict
            result = model.predict(vector_input)[0]

            # Get probability scores if available
            try:
                probabilities = model.predict_proba(vector_input)[0]
                spam_probability = probabilities[1] if result == 1 else probabilities[0]
            except:
                spam_probability = 1.0 if result == 1 else 0.0

            with result_container:
                # Display result
                if result == 1:
                    st.markdown(f"""
                    <div class='result-box spam-box'>
                        <div class='prediction-label spam-label'>⚠️ SPAM DETECTED ⚠️</div>
                        <p>This message has been identified as spam with {spam_probability:.1%} confidence.</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class='result-box not-spam-box'>
                        <div class='prediction-label not-spam-label'>✅ NOT SPAM</div>
                        <p>This message appears to be legitimate with {1 - spam_probability:.1%} confidence.</p>
                    </div>
                    """, unsafe_allow_html=True)

                # Progress bar for spam probability
                st.write("### Spam Probability")
                st.progress(spam_probability)

                # Message analysis
                st.write("### Message Analysis")

                col1, col2 = st.columns(2)



                # Key indicators
                st.write("### Key Indicators")

                indicators = {
                    "Excessive capitalization": sum(1 for c in input_message if c.isupper()) / max(1,
                                                                                                   len(input_message)) > 0.2,
                    "Contains urgent language": any(word in input_message.lower() for word in
                                                    ["urgent", "immediately", "now", "hurry", "limited time"]),
                    "Contains financial terms": any(word in input_message.lower() for word in
                                                    ["money", "cash", "bank", "credit", "loan", "free", "win", "prize",
                                                     "offer"]),
                    "Contains contact requests": any(
                        word in input_message.lower() for word in ["call", "contact", "phone", "reply", "click"]),
                    "Suspicious formatting": input_message.count('!') > 2 or input_message.count('$') > 0
                }

                indicator_df = pd.DataFrame({
                    "Indicator": indicators.keys(),
                    "Present": ["Yes" if v else "No" for v in indicators.values()]
                })

                st.dataframe(indicator_df, use_container_width=True)

                # Tips based on result
                st.write("### Tips & Recommendations")
                if result == 1:
                    st.info("""
                    ⚠️ **This message appears to be spam. Consider these precautions:**

                    - Do not respond or click any links
                    - Do not call any provided phone numbers
                    - Do not provide personal information
                    - Consider blocking the sender
                    - Report the message to your email provider or phone carrier
                    """)
                else:
                    st.success("""
                    ✅ **This message appears to be legitimate, but always remain cautious:**

                    - Verify the sender if you're unsure
                    - Be careful with any unexpected attachments
                    - Never share sensitive information like passwords
                    - Trust your instincts if something seems suspicious
                    """)
        else:
            st.warning("⚠️ Please enter a valid message to analyze.")

else:
    with result_container:
        st.info("Enter a message and press 'Analyze Message' to check if it's spam.")

# Footer
st.markdown("<div class='footer'>Spam Guardian - Protecting your inbox with advanced AI</div>", unsafe_allow_html=True)