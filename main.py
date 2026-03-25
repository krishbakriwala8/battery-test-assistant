
import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import os
import tempfile
import time
from dotenv import load_dotenv

from app.analyzer import BatteryTestAnalyzer
from app.rag import RequirementRAG

# Load env
load_dotenv()


# ── CACHING ──────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def run_analysis(log_bytes: bytes, log_suffix: str, cfg_bytes: bytes):
    """
    Cache analysis results keyed by the raw file bytes.
    Re-runs only when the uploaded files actually change.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=log_suffix) as tmp_log:
        tmp_log.write(log_bytes)
        log_path = tmp_log.name

    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp_cfg:
        tmp_cfg.write(cfg_bytes)
        cfg_path = tmp_cfg.name

    try:
        analyzer = BatteryTestAnalyzer(log_path, cfg_path)
        result = analyzer.run()
        # Serialise the dataframe so it survives the cache boundary
        df_json = analyzer.df.to_json(orient="split") if hasattr(analyzer, "df") else None
    finally:
        os.unlink(log_path)
        os.unlink(cfg_path)

    return result, df_json


def llm_agent_response(question, analyzer_result, rag_obj):
    context_parts = []

    if analyzer_result:
        if analyzer_result["pass"]:
            context_parts.append("Test PASSED")
        else:
            context_parts.append("Test FAILED")
            for v in analyzer_result["violations"][:5]:
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
        "temperature": 0.2,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        r = requests.post(url, headers=headers, json=payload)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return str(e)


# ── PAGE CONFIG ───────────────────────────────────────────────────────────────

st.set_page_config(page_title="Battery Test Failure Assistant", layout="wide")
st.title("🔋 Battery Test Failure Assistant")


# ── SESSION STATE ─────────────────────────────────────────────────────────────

if "rag" not in st.session_state:
    st.session_state.rag = RequirementRAG()

if "analyzer_result" not in st.session_state:
    st.session_state.analyzer_result = None

if "analyzer_df_json" not in st.session_state:
    st.session_state.analyzer_df_json = None


# ── SIDEBAR ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Upload Files")
    log_file = st.file_uploader("Test Log (CSV or MPT)", type=["csv", "mpt"])
    config_file = st.file_uploader("Threshold Config (JSON)", type=["json"])
    req_file = st.file_uploader("Requirement Document (PDF or TXT)", type=["pdf", "txt"])

    analyze_btn = st.button("Analyze", type="primary")

    if req_file is not None:
        req_key = f"rag_loaded_{req_file.name}_{req_file.size}"
        if st.session_state.get("_req_key") != req_key:
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=os.path.splitext(req_file.name)[1]
            ) as tmp:
                tmp.write(req_file.getvalue())
                tmp_path = tmp.name

            with st.spinner("Loading requirement document..."):
                st.session_state.rag.load_document(tmp_path)

            os.unlink(tmp_path)
            st.session_state["_req_key"] = req_key
            st.success("Requirement document loaded.")
        else:
            st.success("Requirement document already loaded.")


# ── ANALYSIS WITH PROGRESS BAR ────────────────────────────────────────────────

if analyze_btn:
    if log_file and config_file:
        progress_bar = st.progress(0, text="Starting analysis…")

        progress_bar.progress(15, text="Reading uploaded files…")
        time.sleep(0.1)

        log_bytes = log_file.getvalue()
        cfg_bytes = config_file.getvalue()
        log_suffix = os.path.splitext(log_file.name)[1]

        progress_bar.progress(35, text="Parsing log data…")
        time.sleep(0.1)

        progress_bar.progress(55, text="Running threshold checks…")
        result, df_json = run_analysis(log_bytes, log_suffix, cfg_bytes)

        progress_bar.progress(80, text="Building statistics…")
        time.sleep(0.1)

        if "error" not in result:
            st.session_state.analyzer_result = result
            st.session_state.analyzer_df_json = df_json

        progress_bar.progress(100, text="Done!")
        time.sleep(0.4)
        progress_bar.empty()

        if "error" in result:
            st.error(result["error"])
        else:
            st.success("✅ Test PASSED" if result["pass"] else "❌ Test FAILED")
    else:
        st.warning("Upload both log + config files before running analysis.")


# ── MAIN TABS ─────────────────────────────────────────────────────────────────

main_tab1, main_tab2, main_tab3 = st.tabs(
    ["📊 Analysis", "📖 Requirement Q&A", "🤖 Smart Assistant"]
)


# ── ANALYSIS TAB (sub-tabs: Overview / Plots / Violations / Report) ───────────

with main_tab1:
    result = st.session_state.analyzer_result
    df_json = st.session_state.analyzer_df_json

    if result is None:
        st.info("Upload a log file and config, then click **Analyze**.")
    else:
        # ── sub-tabs ──────────────────────────────────────────────────────────
        ov_tab, plot_tab, viol_tab, report_tab = st.tabs(
            ["🗂 Overview", "📈 Plots", "⚠️ Violations", "📄 Report"]
        )

        # Overview ─────────────────────────────────────────────────────────────
        with ov_tab:
            status_color = "green" if result["pass"] else "red"
            status_label = "PASSED ✅" if result["pass"] else "FAILED ❌"
            st.markdown(
                f"### Test Status: <span style='color:{status_color}'>{status_label}</span>",
                unsafe_allow_html=True,
            )

            st.subheader("Summary")
            st.text(result["summary"])

            st.subheader("Statistics")
            st.dataframe(pd.DataFrame(result["statistics"]).T, use_container_width=True)

        # Plots ────────────────────────────────────────────────────────────────
        with plot_tab:
            if df_json:
                df = pd.read_json(df_json, orient="split")
                st.plotly_chart(
                    px.line(df, x="timestamp", y="voltage", title="Voltage over Time"),
                    use_container_width=True,
                )
                st.plotly_chart(
                    px.line(df, x="timestamp", y="current", title="Current over Time"),
                    use_container_width=True,
                )
                st.plotly_chart(
                    px.line(df, x="timestamp", y="temperature", title="Temperature over Time"),
                    use_container_width=True,
                )
            else:
                st.info("No dataframe available for plotting.")

        # Violations ───────────────────────────────────────────────────────────
        with viol_tab:
            if result["violations"]:
                st.dataframe(
                    pd.DataFrame(result["violations"]), use_container_width=True
                )
            else:
                st.success("No violations found.")

        # Report ───────────────────────────────────────────────────────────────
        with report_tab:
            report_text = f"Test Result: {'PASS' if result['pass'] else 'FAIL'}\n\n"
            report_text += f"Summary: {result['summary']}\n\nViolations:\n"
            for v in result["violations"]:
                report_text += (
                    f"- {v['signal']} at t={v['timestamp']}: {v['value']} ({v['rule']})\n"
                )

            st.text(report_text)
            st.download_button(
                "⬇️ Download Report", report_text, file_name="battery_report.txt"
            )


# ── REQUIREMENT Q&A TAB ───────────────────────────────────────────────────────

with main_tab2:
    st.header("Ask about Requirements")

    if st.session_state.rag.retriever:
        q = st.text_input("Your question", key="rag_q")
        if q:
            with st.spinner("Searching…"):
                ans = st.session_state.rag.answer_question(q)
            st.markdown(ans)
    else:
        st.info("Upload a requirement document in the sidebar first.")


# ── SMART ASSISTANT TAB ───────────────────────────────────────────────────────

with main_tab3:
    st.header("Smart Assistant")

    result = st.session_state.analyzer_result

    if result is None:
        st.info("Run analysis first.")
    else:
        q = st.text_input("Ask anything about the test results", key="llm_q")
        if q:
            with st.spinner("Thinking…"):
                answer = llm_agent_response(q, result, st.session_state.rag)
            st.markdown(answer)


