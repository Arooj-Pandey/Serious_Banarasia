import streamlit as st
import requests

st.set_page_config(page_title="Varanasi Chatbot", page_icon="🕉️", layout="wide")

st.title("Explore Varanasi with Shivendra 🕉️")
st.markdown("""
    <style>
    .main {
        background-color: #f5f5f5;
        padding: 20px;
        border-radius: 10px;
    }
    .response {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    }
    .response h4 {
        color: #ff5733;
    }
    .response p {
        color: #333333;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown("<div class='main'>", unsafe_allow_html=True)

st.header("Ask Shivendra about Varanasi")
user_input = st.text_input("Type your question here...")

if st.button("Ask"):
    if user_input:
        with st.spinner("Shivendra is thinking..."):
            response = requests.post("http://api.example.com/ask", json={"question": user_input})
            if response.status_code == 200:
                data = response.json()
                for item in data['responses']:
                    st.markdown(f"""
                        <div class='response'>
                            <h4>{item['title']}</h4>
                            <p>{item['snippet']}</p>
                            <a href="{item['link']}" target="_blank">Read more</a>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.error("Error: Unable to get response from Shivendra.")
    else:
        st.warning("Please enter a question.")

st.markdown("</div>", unsafe_allow_html=True)