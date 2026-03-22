import streamlit as st

def llm_agent_response(question, analyzer_result, rag_obj):
    context_parts = []

    if analyzer_result:
        if analyzer_result['pass']:
            context_parts.append("Test PASSED")
        else:
            context_parts.append("Test FAILED")
            for v in analyzer_result['violations'][:5]:
                context_parts.append(
                    f"{v['signal']} at {v['timestamp']} = {v['value']} ({v['rule']})"
                )

    if rag_obj and rag_obj.retriever:
        doc_info = rag_obj.answer_question(question)
        if "No relevant" not in doc_info:
            context_parts.append(doc_info)

    if not context_parts:
        return "Not enough data"

    context = "\n".join(context_parts)

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return "Missing GROQ_API_KEY"

    url = "https://api.groq.com/openai/v1/chat/completions"

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
        ],
        "temperature": 0.2
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        r = requests.post(url, headers=headers, json=payload)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return str(e)
    
import pandas as pd
import plotly.express as px
import requests
import os
import tempfile
from dotenv import load_dotenv

from app.analyzer import BatteryTestAnalyzer
from app.rag import RequirementRAG

# Load env
load_dotenv()

st.set_page_config(page_title="Battery Test Failure Assistant", layout="wide")
st.title("🔋 Battery Test Failure Assistant")


# SESSION STATE INIT

if 'rag' not in st.session_state:
    st.session_state.rag = RequirementRAG()

if 'analyzer_result' not in st.session_state:
    st.session_state.analyzer_result = None

if 'analyzer_obj' not in st.session_state:
    st.session_state.analyzer_obj = None


# SIDEBAR

with st.sidebar:
    st.header("Upload Files")
    log_file = st.file_uploader("Test Log (CSV or MPT)", type=["csv", "mpt"])
    config_file = st.file_uploader("Threshold Config (JSON)", type=["json"])
    req_file = st.file_uploader("Requirement Document (PDF or TXT)", type=["pdf", "txt"])

    analyze_btn = st.button("Analyze", type="primary")

    # Load requirement doc
    if req_file is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(req_file.name)[1]) as tmp:
            tmp.write(req_file.getvalue())
            tmp_path = tmp.name

        with st.spinner("Loading requirement document..."):
            st.session_state.rag.load_document(tmp_path)

        os.unlink(tmp_path)
        st.success("Requirement document loaded.")


# TABS

tab1, tab2, tab3, tab4 = st.tabs([
    "Analysis", "Requirement Q&A", "Report", "Smart Assistant"
])


# TAB 1: ANALYSIS

with tab1:
    if analyze_btn and log_file and config_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(log_file.name)[1]) as tmp_log:
            tmp_log.write(log_file.getvalue())
            log_path = tmp_log.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp_cfg:
            tmp_cfg.write(config_file.getvalue())
            cfg_path = tmp_cfg.name

        with st.spinner("Analyzing..."):
            analyzer = BatteryTestAnalyzer(log_path, cfg_path)
            result = analyzer.run()

        os.unlink(log_path)
        os.unlink(cfg_path)

        if "error" in result:
            st.error(result["error"])
        else:
            st.session_state.analyzer_result = result
            st.session_state.analyzer_obj = analyzer

            st.success("✅ Test PASSED" if result["pass"] else "❌ Test FAILED")

            col1, col2 = st.columns(2)

            with col1:
                st.subheader("📊 Statistics")
                st.dataframe(pd.DataFrame(result["statistics"]).T)

            with col2:
                st.subheader("📋 Violations")
                if result["violations"]:
                    st.dataframe(pd.DataFrame(result["violations"]))
                else:
                    st.info("No violations")

            st.subheader("📝 Summary")
            st.text(result["summary"])

            df = analyzer.df

            st.subheader("📈 Plots")
            st.plotly_chart(px.line(df, x="timestamp", y="voltage"), use_container_width=True)
            st.plotly_chart(px.line(df, x="timestamp", y="current"), use_container_width=True)
            st.plotly_chart(px.line(df, x="timestamp", y="temperature"), use_container_width=True)

    elif analyze_btn:
        st.warning("Upload both log + config")


# TAB 2: RAG Q&A

with tab2:
    st.header("Ask about Requirements")

    if st.session_state.rag.retriever:
        q = st.text_input("Your question")
        if q:
            with st.spinner("Searching..."):
                ans = st.session_state.rag.answer_question(q)
            st.markdown(ans)
    else:
        st.info("Upload requirement document first")


# TAB 3: REPORT

with tab3:
    st.header("📄 Report")

    result = st.session_state.analyzer_result

    if result:
        report = f"Test Result: {'PASS' if result['pass'] else 'FAIL'}\n\n"
        report += f"Summary: {result['summary']}\n\nViolations:\n"

        for v in result['violations']:
            report += f"- {v['signal']} at t={v['timestamp']}: {v['value']} ({v['rule']})\n"

        st.text(report)

        st.download_button("Download Report", report, file_name="report.txt")
    else:
        st.info("Run analysis first")


# TAB 4: LLM

with tab4:
    st.header("Smart Assistant")

    result = st.session_state.analyzer_result

    if result is None:
        st.info("Run analysis first")
    else:
        q = st.text_input("Ask anything")

        if q:
            with st.spinner("Thinking..."):
                answer = llm_agent_response(q, result, st.session_state.rag)
            st.markdown(answer)



