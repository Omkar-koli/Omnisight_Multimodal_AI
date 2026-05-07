from __future__ import annotations

from pathlib import Path
import math
import pandas as pd
from typing import Any, Dict

from omnisight.features.demand_features import build_decision_features

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MERGED_DIR = PROJECT_ROOT / "data" / "processed" / "merged"
CATEGORIES_DIR = PROJECT_ROOT / "data" / "processed" / "categories"

PRODUCTS_PATH = MERGED_DIR / "products_current.parquet"
FEATURE_BASE_PATH = MERGED_DIR / "feature_base.parquet"
OUTPUT_PATH = MERGED_DIR / "decision_features.parquet"

def product_seed(product_id: str) -> int:
    return sum(ord(ch) for ch in str(product_id))


def build_weekly_sales_history(
    product_id: str,
    weekly_units_sold: float,
    trend_strength_score: float,
    review_risk_score: float,
) -> list[float]:
    seed = product_seed(product_id)
    base = max(1.0, float(weekly_units_sold))

    seasonal_amp = 0.08 + (seed % 7) * 0.01
    trend_bias = (trend_strength_score - 0.5) * 0.25
    risk_drag = review_risk_score * 0.08

    history = []
    for i in range(12):
        seasonal = 1.0 + seasonal_amp * math.sin((i + (seed % 5)) / 2.0)
        drift = 1.0 + ((i - 11) / 11.0) * trend_bias
        jitter = 1.0 + (((seed + i * 13) % 9) - 4) * 0.015
        value = base * seasonal * drift * jitter * (1.0 - risk_drag)
        history.append(round(max(1.0, value), 2))

    return history


def build_trend_series(
    product_id: str,
    latest_trend_index: float,
    avg_trend_change_pct: float,
) -> list[float]:
    seed = product_seed(product_id)
    latest = max(0.0, float(latest_trend_index or 0.0))
    delta = float(avg_trend_change_pct or 0.0)

    history = []
    for i in range(12):
        backstep = 11 - i
        value = latest * (1.0 - backstep * (delta / 100.0) * 0.6)
        wobble = (((seed + i * 17) % 11) - 5) * 0.8
        history.append(round(max(0.0, value + wobble), 2))

    return history

def deterministic_int_from_product_id(product_id: str) -> int:
    return sum(ord(ch) for ch in str(product_id))

def normalize_text_list(value) -> list[str]:
    if value is None:
        return []

    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]

    if isinstance(value, tuple):
        return [str(v).strip() for v in value if str(v).strip()]

    if hasattr(value, "tolist"):
        raw = value.tolist()
        if isinstance(raw, list):
            return [str(v).strip() for v in raw if str(v).strip()]
        raw = str(raw).strip()
        return [raw] if raw else []

    text = str(value).strip()
    if not text:
        return []

    # split common delimiters if present
    for delim in ["|", ";", "\n", ","]:
        if delim in text:
            return [part.strip() for part in text.split(delim) if part.strip()]

    return [text]

def first_nonempty_text_list(row: Dict[str, Any], candidate_keys: list[str]) -> list[str]:
    for key in candidate_keys:
        values = normalize_text_list(row.get(key))
        if len(values) > 0:
            return values
    return []

def dedupe_keep_order(values: list[str]) -> list[str]:
    seen = set()
    out: list[str] = []
    for value in values:
        key = value.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(value.strip())
    return out


def collect_first_available_terms(row: pd.Series, candidate_cols: list[str], limit: int = 5) -> list[str]:
    collected: list[str] = []

    for col in candidate_cols:
        if col not in row.index:
            continue
        collected.extend(normalize_text_list(row.get(col)))

    return dedupe_keep_order(collected)[:limit]


def looks_like_placeholder_inventory(df: pd.DataFrame) -> bool:
    if df.empty:
        return True

    if "current_inventory" not in df.columns or "weekly_units_sold" not in df.columns:
        return True

    inv_unique = pd.to_numeric(df["current_inventory"], errors="coerce").nunique(dropna=True)
    weekly_unique = pd.to_numeric(df["weekly_units_sold"], errors="coerce").nunique(dropna=True)

    return inv_unique <= 1 and weekly_unique <= 1


def load_inventory_df(products_df: pd.DataFrame, feature_base_df: pd.DataFrame) -> pd.DataFrame:
    candidate_paths = [
        MERGED_DIR / "inventory_current.parquet",
        MERGED_DIR / "inventory.parquet",
    ]

    for path in candidate_paths:
        if not path.exists():
            continue

        candidate_df = pd.read_parquet(path).copy()
        if "product_id" not in candidate_df.columns:
            continue

        candidate_df["product_id"] = candidate_df["product_id"].astype("string")

        if looks_like_placeholder_inventory(candidate_df):
            print(f"Ignoring placeholder inventory from: {path}")
            continue

        print(f"Loaded inventory from: {path}")
        return candidate_df

    print("No real inventory parquet found. Building deterministic synthetic inventory fallback.")

    base = products_df[["product_id"]].copy()
    base["product_id"] = base["product_id"].astype("string")

    feature_base_clean = feature_base_df.drop_duplicates(subset=["product_id"]).copy()
    feature_lookup = feature_base_clean.set_index("product_id").to_dict(orient="index")

    current_inventory: list[float] = []
    weekly_units_sold: list[float] = []
    lead_time_days: list[float] = []
    supplier: list[str] = []
    min_order_qty: list[float] = []

    for product_id in base["product_id"].tolist():
        feat = feature_lookup.get(product_id, {})

        review_count = float(feat.get("review_count", 0) or 0)
        avg_rating = float(feat.get("avg_rating", 0) or 0)
        latest_trend_index = float(feat.get("latest_trend_index", 0) or 0)
        avg_trend_change_pct = float(feat.get("avg_trend_change_pct", 0) or 0)

        seed = sum(ord(ch) for ch in str(product_id))

        demand_signal = min(review_count / 15.0, 25.0) + min(latest_trend_index / 12.0, 12.0)
        trend_boost = max(avg_trend_change_pct, 0.0) * 1.4
        rating_boost = max(avg_rating - 3.0, 0.0) * 2.5
        jitter = 1.0 + (((seed % 11) - 5) * 0.03)

        weekly = max(
            1.0,
            round((3.0 + demand_signal + trend_boost + rating_boost) * jitter, 2),
        )

        cover_weeks = 2.8 + ((seed % 6) * 0.75)   # ~2.8 to ~6.55 weeks
        if avg_trend_change_pct > 5:
            cover_weeks -= 0.4
        if avg_rating < 3.7:
            cover_weeks += 0.6

        cover_weeks = max(2.2, min(7.0, cover_weeks))

        inventory = max(
            6.0,
            round((weekly * cover_weeks) + (seed % 12), 2),
        )

        lead = 7 + (seed % 12)   # 7 to 18 days
        moq = 4 + (seed % 12)

        current_inventory.append(float(inventory))
        weekly_units_sold.append(float(weekly))
        lead_time_days.append(float(lead))
        supplier.append(f"supplier_{(seed % 5) + 1}")
        min_order_qty.append(float(moq))

    assert len(current_inventory) == len(base), f"current_inventory length {len(current_inventory)} != base length {len(base)}"
    assert len(weekly_units_sold) == len(base), f"weekly_units_sold length {len(weekly_units_sold)} != base length {len(base)}"
    assert len(lead_time_days) == len(base), f"lead_time_days length {len(lead_time_days)} != base length {len(base)}"
    assert len(supplier) == len(base), f"supplier length {len(supplier)} != base length {len(base)}"
    assert len(min_order_qty) == len(base), f"min_order_qty length {len(min_order_qty)} != base length {len(base)}"

    base["current_inventory"] = current_inventory
    base["weekly_units_sold"] = weekly_units_sold
    base["lead_time_days"] = lead_time_days
    base["supplier"] = supplier
    base["min_order_qty"] = min_order_qty
    base["source_system"] = "synthetic_inventory_fallback"

    return base


def main() -> None:
    if not PRODUCTS_PATH.exists():
        raise FileNotFoundError(f"Missing {PRODUCTS_PATH}")
    if not FEATURE_BASE_PATH.exists():
        raise FileNotFoundError(f"Missing {FEATURE_BASE_PATH}")

    products_df = pd.read_parquet(PRODUCTS_PATH).copy()
    feature_base_df = pd.read_parquet(FEATURE_BASE_PATH).copy()

    for df in (products_df, feature_base_df):
        df["product_id"] = df["product_id"].astype("string")

    inventory_df = load_inventory_df(products_df, feature_base_df)
    inventory_df["product_id"] = inventory_df["product_id"].astype("string")

    # Keep product/category fields from products_df
    product_cols = [
        "product_id",
        "title",
        "brand",
        "price",
        "description",
        "category",
        "category_slug",
        "category_label",
        "image_url",
        "source_system",
    ]
    product_cols = [c for c in product_cols if c in products_df.columns]
    products_core = products_df[product_cols].copy()

    # Drop overlapping descriptive columns from feature base, but KEEP feature metrics
    drop_from_feature_base = [
        c for c in [
            "title",
            "brand",
            "price",
            "description",
            "category",
            "category_slug",
            "category_label",
            "image_url",
            "source_system",
        ]
        if c in feature_base_df.columns
    ]
    feature_metrics = feature_base_df.drop(columns=drop_from_feature_base).copy()

    merged = products_core.merge(feature_metrics, on="product_id", how="left")

    drop_from_inventory = [
        c for c in [
            "category",
            "category_slug",
            "category_label",
            "source_system",
            "title",
            "brand",
            "price",
            "description",
            "image_url",
        ]
        if c in inventory_df.columns
    ]
    inventory_core = inventory_df.drop(columns=drop_from_inventory).copy()

    merged = merged.merge(inventory_core, on="product_id", how="left")

    # Fill operational fields safely
    if "current_inventory" in merged.columns:
        merged["current_inventory"] = pd.to_numeric(merged["current_inventory"], errors="coerce").fillna(0.0)
    if "weekly_units_sold" in merged.columns:
        merged["weekly_units_sold"] = pd.to_numeric(merged["weekly_units_sold"], errors="coerce").fillna(0.0)
    if "lead_time_days" in merged.columns:
        merged["lead_time_days"] = pd.to_numeric(merged["lead_time_days"], errors="coerce").fillna(7.0)
    if "min_order_qty" in merged.columns:
        merged["min_order_qty"] = pd.to_numeric(merged["min_order_qty"], errors="coerce").fillna(1.0)
    if "supplier" in merged.columns:
        merged["supplier"] = merged["supplier"].fillna("unknown_supplier")

    decision_df = build_decision_features(merged)
        # Add richer synthetic time-series and analysis support columns
    if "trend_strength_score" not in decision_df.columns:
        decision_df["trend_strength_score"] = 0.5
    if "review_risk_score" not in decision_df.columns:
        decision_df["review_risk_score"] = 0.0
    if "latest_trend_index" not in decision_df.columns:
        decision_df["latest_trend_index"] = 0.0
    if "avg_trend_change_pct" not in decision_df.columns:
        decision_df["avg_trend_change_pct"] = 0.0
    if "review_count" not in decision_df.columns:
        decision_df["review_count"] = 0
    if "avg_rating" not in decision_df.columns:
        decision_df["avg_rating"] = 0.0
    if "days_to_stockout" not in decision_df.columns:
        decision_df["days_to_stockout"] = 999.0

    decision_df["weekly_sales_history"] = decision_df.apply(
        lambda row: build_weekly_sales_history(
            product_id=str(row["product_id"]),
            weekly_units_sold=float(row.get("weekly_units_sold", 0.0) or 0.0),
            trend_strength_score=float(row.get("trend_strength_score", 0.5) or 0.5),
            review_risk_score=float(row.get("review_risk_score", 0.0) or 0.0),
        ),
        axis=1,
    )

    decision_df["trend_values"] = decision_df.apply(
        lambda row: build_trend_series(
            product_id=str(row["product_id"]),
            latest_trend_index=float(row.get("latest_trend_index", 0.0) or 0.0),
            avg_trend_change_pct=float(row.get("avg_trend_change_pct", 0.0) or 0.0),
        ),
        axis=1,
    )

    decision_df["recent_review_avg"] = pd.to_numeric(
        decision_df["avg_rating"], errors="coerce"
    ).fillna(0.0)

    decision_df["older_review_avg"] = (
        pd.to_numeric(decision_df["avg_rating"], errors="coerce").fillna(0.0)
        - (pd.to_numeric(decision_df["review_risk_score"], errors="coerce").fillna(0.0) * 0.35)
    ).clip(lower=0.0)

    decision_df["recent_review_count"] = (
        pd.to_numeric(decision_df["review_count"], errors="coerce").fillna(0) * 0.40
    ).astype(int)

    decision_df["older_review_count"] = (
        pd.to_numeric(decision_df["review_count"], errors="coerce").fillna(0) * 0.60
    ).astype(int)

    decision_df["stockout_count_90d"] = decision_df.apply(
        lambda row: 2
        if float(row.get("days_to_stockout", 999.0) or 999.0) <= 14
        else (1 if float(row.get("days_to_stockout", 999.0) or 999.0) <= 28 else 0),
        axis=1,
    )

        # -----------------------------
    # Text evidence for trend explanations
    # -----------------------------
    # These columns are optional. If upstream data contains them, preserve and normalize them.
    # If not present, they stay empty and downstream logic should mark trend reasoning as low confidence.

    decision_df["trend_search_keywords"] = decision_df.apply(
        lambda row: collect_first_available_terms(
            row,
            [
                "trend_search_keywords",
                "google_trends_keywords",
                "trend_keywords",
                "related_queries_top",
                "related_query_terms",
                "trend_keyword",
            ],
            limit=5,
        ),
        axis=1,
    )

    decision_df["recent_review_keywords_30d"] = decision_df.apply(
        lambda row: collect_first_available_terms(
            row,
            [
                "recent_review_keywords_30d",
                "recent_review_title_keywords",
                "recent_review_phrases_30d",
                "review_title_keywords_30d",
                "review_keywords",
            ],
            limit=5,
        ),
        axis=1,
    )

    decision_df["recent_review_titles_30d"] = decision_df.apply(
        lambda row: collect_first_available_terms(
            row,
            [
                "recent_review_titles_30d",
                "recent_review_headlines_30d",
                "review_titles_30d",
                "review_headlines",
                "recent_review_titles",
            ],
            limit=10,
        ),
        axis=1,
    )

    # Preserve category fields for downstream retrieval / UI / analytics
    front_cols = [
        "product_id",
        "title",
        "brand",
        "price",
        "description",
        "category",
        "category_slug",
        "category_label",
        "image_url",
        "source_system",
    ]
    front_cols = [c for c in front_cols if c in decision_df.columns]

    metric_cols = [c for c in decision_df.columns if c not in front_cols]
    decision_df = decision_df[front_cols + metric_cols].copy()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    decision_df.to_parquet(OUTPUT_PATH, index=False)

    print(f"Saved decision features to: {OUTPUT_PATH}")
    print(decision_df.head(10).to_string(index=False))

    if "category_slug" in decision_df.columns:
        print("\nCategory counts:")
        print(decision_df["category_slug"].value_counts(dropna=False))



if __name__ == "__main__":
    main()