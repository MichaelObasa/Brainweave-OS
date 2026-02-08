import streamlit as st
import requests
import os
import json

# CONFIG
API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Brainweave OS", page_icon="🧠", layout="wide")

st.title("🧠 Brainweave OS")
st.markdown("### Mission Control")

# TABS
tab1, tab2 = st.tabs(["📺 YouTube Ingest", "🖼️ Vision Analysis"])

# --- TAB 1: YOUTUBE ---
with tab1:
    col1, col2 = st.columns([3, 1])
    with col1:
        url = st.text_input("Paste YouTube URL here:")
    with col2:
        # Spacing to align button
        st.write("") 
        st.write("")
        submit_yt = st.button("Ingest Video", type="primary")

    if submit_yt and url:
        with st.spinner("🎧 Transcribing & Analyzing... this takes about 30-60s..."):
            try:
                # Call your local API
                payload = {"url": url, "save_markdown": True, "overwrite": True}
                res = requests.post(f"{API_URL}/ingest/youtube", json=payload)
                
                if res.status_code == 200:
                    data = res.json()
                    st.success(f"✅ Analysis Complete!")
                    
                    # --- SAFETY FIX STARTS HERE ---
                    file_info = data.get('file_save_info')
                    
                    if file_info:
                        if file_info.get('saved') is False:
                            # START DEBUGGING: Show the actual error from the server
                            st.error(f"❌ Save Failed: {file_info.get('path')}")
                        else:
                            filename = file_info.get('filename', 'Unknown File')
                            st.info(f"📂 **Saved to:** `{filename}`")
                    else:
                        st.warning("⚠️ Metadata extracted, but file info is missing completely.")
                    # --- SAFETY FIX ENDS HERE ---
                    
                    with st.expander("View Extracted Metadata", expanded=True):
                        st.json(data.get('metadata', {}))
                else:
                    st.error(f"Error {res.status_code}: {res.text}")
            except Exception as e:
                st.error(f"Connection Failed. Is the Uvicorn server running? {e}")

# --- TAB 2: VISION ---
with tab2:
    st.write("Upload a chart, receipt, or screenshot.")
    uploaded_file = st.file_uploader("Drag & Drop File", type=["jpg", "png", "jpeg", "webp"])
    
    if uploaded_file is not None:
        st.image(uploaded_file, caption="Preview", width=300)
        
        if st.button("Analyze & Route", type="primary"):
            with st.spinner("👁️ AI Vision is analyzing..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
                    res = requests.post(f"{API_URL}/ingest/upload", files=files)
                    
                    if res.status_code == 200:
                        data = res.json()
                        st.success("✅ Processed & Routed!")
                        
                        # Show where it went
                        final_path = data.get('file', 'Unknown')
                        folder = os.path.dirname(final_path)
                        st.info(f"📂 **Moved to:** `{folder}`")
                        
                        st.json(data.get('meta', {}))
                    else:
                        st.error(f"Error: {res.text}")
                except Exception as e:
                    st.error(f"Connection Failed: {e}")