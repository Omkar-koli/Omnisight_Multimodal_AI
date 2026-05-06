from __future__ import annotations

from pathlib import Path
import pandas as pd

from omnisight.decision.reasoning import reason_about_product
from omnisight.retrieval.evidence_builder import EvidenceBuilder

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

RECOMMENDATIONS_PATH = PROCESSED_DIR / "recommendations.parquet"
OUTPUT_PATH = PROCESSED_DIR / "llm_recommendations.parquet"
PREVIEW_PATH = PROCESSED_DIR / "llm_recommendations_preview.csv"


def main() -> None:
    if not RECOMMENDATIONS_PATH.exists():
        raise FileNotFoundError("Missing recommendations.parquet")

    recommendations_df = pd.read_parquet(RECOMMENDATIONS_PATH)
    recommendations_df["product_id"] = recommendations_df["product_id"].astype("string")

    builder = EvidenceBuilder()
    rows = []

    # Start small while testing
    sample_df = recommendations_df.head(15).copy()

    for _, row in sample_df.iterrows():
        product_id = str(row["product_id"])
        try:
            evidence = builder.build(product_id)
            result = reason_about_product(evidence)

            rows.append(
                {
                    "product_id": result.product_id,
                    "title": result.title,
                    "final_action": result.final_action,
                    "confidence": result.confidence,
                    "reasoning_summary": result.reasoning_summary,
                    "key_risks": " | ".join(result.key_risks),
                    "key_opportunities": " | ".join(result.key_opportunities),
                    "caution_flags": " | ".join(result.caution_flags),
                    "follow_up_actions": " | ".join(result.follow_up_actions),
                    "supporting_evidence_count": len(result.supporting_evidence),
                }
            )

            print(f"Done: {product_id}")

        except Exception as e:
            rows.append(
                {
                    "product_id": product_id,
                    "title": row.get("title", ""),
                    "final_action": "ERROR",
                    "confidence": 0.0,
                    "reasoning_summary": str(e),
                    "key_risks": "",
                    "key_opportunities": "",
                    "caution_flags": "",
                    "follow_up_actions": "",
                    "supporting_evidence_count": 0,
                }
            )
            print(f"Failed: {product_id} -> {e}")

    out_df = pd.DataFrame(rows)
    out_df.to_parquet(OUTPUT_PATH, index=False)
    out_df.to_csv(PREVIEW_PATH, index=False)

    print(f"Saved: {OUTPUT_PATH}")
    print(f"Saved: {PREVIEW_PATH}")
    print(out_df.head(10).to_string(index=False))


if __name__ == "__main__":
    main()