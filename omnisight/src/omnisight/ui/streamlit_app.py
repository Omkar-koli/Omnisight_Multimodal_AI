from __future__ import annotations

from pathlib import Path
import pandas as pd
import streamlit as st

from omnisight.ui.api_client import OmniSightAPIClient

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
IMAGE_DIR = PROJECT_ROOT / "data" / "raw" / "product_images"

PREVIEW_PATH = PROCESSED_DIR / "recommendations_preview.csv"


@st.cache_data
def load_preview() -> pd.DataFrame:
    if PREVIEW_PATH.exists():
        return pd.read_csv(PREVIEW_PATH)
    return pd.DataFrame()


def display_metric_cards(result: dict) -> None:
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Baseline Action", result.get("baseline_action", ""))
    col2.metric("Baseline Confidence", result.get("baseline_confidence", 0.0))
    col3.metric("LLM Action", result.get("llm_final_action", ""))
    col4.metric("LLM Confidence", result.get("llm_confidence", 0.0))


def display_lists(title: str, items: list[str]) -> None:
    st.subheader(title)
    if not items:
        st.caption("No items available.")
        return
    for item in items:
        st.markdown(f"- {item}")


def display_supporting_evidence(items: list[dict]) -> None:
    st.subheader("Supporting Evidence")
    if not items:
        st.caption("No supporting evidence returned.")
        return

    for idx, item in enumerate(items, start=1):
        source = item.get("source", "unknown")
        summary = item.get("summary", "")
        with st.expander(f"Evidence {idx} — {source}"):
            st.write(summary)


def display_image(product_id: str) -> None:
    image_path = IMAGE_DIR / f"{product_id}.jpg"
    if image_path.exists():
        st.image(str(image_path), caption=f"Product Image — {product_id}", use_container_width=True)
    else:
        st.caption("No local product image found.")


def main() -> None:
    st.set_page_config(
        page_title="OmniSight Dashboard",
        page_icon="📦",
        layout="wide",
    )

    st.title("📦 OmniSight — Decision Dashboard")
    st.caption("Multimodal restocking decision support powered by rules, retrieval, and LLM reasoning.")

    preview_df = load_preview()

    st.sidebar.header("Connection")
    api_base_url = st.sidebar.text_input("FastAPI Base URL", value="http://127.0.0.1:8000")

    client = OmniSightAPIClient(api_base_url)

    st.sidebar.header("Product Selection")

    if not preview_df.empty and {"product_id", "title"}.issubset(preview_df.columns):
        preview_df["label"] = preview_df["product_id"].astype(str) + " | " + preview_df["title"].astype(str)
        selected_label = st.sidebar.selectbox(
            "Pick a product from preview",
            options=[""] + preview_df["label"].tolist(),
        )

        selected_product_id = ""
        if selected_label:
            selected_product_id = selected_label.split(" | ", 1)[0]
    else:
        selected_product_id = ""

    manual_product_id = st.sidebar.text_input("Or enter product_id manually", value=selected_product_id)

    st.sidebar.header("API Check")
    if st.sidebar.button("Check API Health"):
        try:
            health = client.health()
            st.sidebar.success(f"API OK: {health}")
        except Exception as e:
            st.sidebar.error(f"API connection failed: {e}")

    if st.button("Run OmniSight Decision"):
        product_id = manual_product_id.strip()

        if not product_id:
            st.warning("Please select or enter a product_id.")
            return

        try:
            with st.spinner("Calling OmniSight API..."):
                result = client.get_decision(product_id)

            st.success("Decision loaded successfully.")

            st.header(result.get("title", "Untitled Product"))
            st.caption(f"Product ID: {result.get('product_id', '')}")

            image_col, summary_col = st.columns([1, 2])

            with image_col:
                display_image(product_id)

            with summary_col:
                display_metric_cards(result)
                st.subheader("Reasoning Summary")
                st.write(result.get("reasoning_summary", ""))

            tab1, tab2, tab3 = st.tabs(["Risks & Opportunities", "Evidence", "Raw Response"])

            with tab1:
                left, right = st.columns(2)
                with left:
                    display_lists("Key Risks", result.get("key_risks", []))
                    display_lists("Caution Flags", result.get("caution_flags", []))
                with right:
                    display_lists("Key Opportunities", result.get("key_opportunities", []))
                    display_lists("Follow-up Actions", result.get("follow_up_actions", []))

            with tab2:
                display_supporting_evidence(result.get("supporting_evidence", []))

            with tab3:
                st.json(result)

        except Exception as e:
            st.error(f"Failed to get decision: {e}")

    st.divider()

    st.subheader("Preview Products")
    if preview_df.empty:
        st.caption("recommendations_preview.csv not found yet.")
    else:
        show_cols = [c for c in ["product_id", "title", "action", "confidence"] if c in preview_df.columns]
        st.dataframe(preview_df[show_cols], use_container_width=True)


if __name__ == "__main__":
    main()