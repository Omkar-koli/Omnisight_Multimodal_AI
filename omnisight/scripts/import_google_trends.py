from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRENDS_RAW_DIR = PROJECT_ROOT / "data" / "raw" / "trends"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MAPPING_PATH = PROJECT_ROOT / "configs" / "mappings" / "trend_keyword_map.csv"


def find_header_row(csv_path: Path) -> int:
    with csv_path.open("r", encoding="utf-8-sig") as f:
        for idx, line in enumerate(f):
            first_cell = line.split(",")[0].strip().lower()
            if first_cell in {"week", "month", "day", "date"}:
                return idx
    return 0


def parse_trends_file(csv_path: Path) -> pd.DataFrame:
    header_row = find_header_row(csv_path)
    df = pd.read_csv(csv_path, skiprows=header_row)

    df.columns = [str(col).strip() for col in df.columns]
    date_col = df.columns[0]
    value_col = df.columns[-1]

    trend_keyword = csv_path.stem.replace("_", " ")

    out = pd.DataFrame(
        {
            "week": pd.to_datetime(df[date_col], errors="coerce"),
            "trend_index": pd.to_numeric(
                df[value_col].astype(str).str.replace("<1", "0", regex=False),
                errors="coerce",
            ),
        }
    )
    out = out.dropna(subset=["week", "trend_index"]).copy()
    out["trend_keyword"] = trend_keyword
    out["source_system"] = "google_trends"

    return out


def main() -> None:
    csv_files = sorted(TRENDS_RAW_DIR.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError("No Google Trends CSV files found in data/raw/trends")

    frames = [parse_trends_file(path) for path in csv_files]
    trends_df = pd.concat(frames, ignore_index=True)

    trends_df = trends_df.sort_values(["trend_keyword", "week"]).reset_index(drop=True)
    trends_df["trend_change_pct"] = (
        trends_df.groupby("trend_keyword")["trend_index"]
        .pct_change()
        .fillna(0)
        .mul(100)
        .round(2)
    )

    if MAPPING_PATH.exists():
        mapping_df = pd.read_csv(MAPPING_PATH)
        trends_df = trends_df.merge(mapping_df, on="trend_keyword", how="left")
    else:
        trends_df["product_id"] = pd.NA

    trends_df = trends_df[
        ["trend_keyword", "product_id", "week", "trend_index", "trend_change_pct", "source_system"]
    ]

    trends_df.to_parquet(PROCESSED_DIR / "trends.parquet", index=False)
    print("Saved trends.parquet")


if __name__ == "__main__":
    main()