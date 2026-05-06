from __future__ import annotations

from pathlib import Path

import pandas as pd
from ucimlrepo import fetch_ucirepo

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "uci_online_retail"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def snake_case_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (
        df.columns.str.strip()
        .str.replace(" ", "_", regex=False)
        .str.replace(r"[^a-zA-Z0-9_]", "", regex=True)
        .str.lower()
    )
    return df


def main() -> None:
    ds = fetch_ucirepo(id=352)
    X = ds.data.features.copy()
    X = snake_case_columns(X)

    rename_map = {
        "invoiceno": "invoice_no",
        "stockcode": "stock_code",
        "description": "description",
        "quantity": "quantity",
        "invoicedate": "invoice_date",
        "unitprice": "unit_price",
        "customerid": "customer_id",
        "country": "country",
    }
    X = X.rename(columns=rename_map)

    if "invoice_date" in X.columns:
        X["invoice_date"] = pd.to_datetime(X["invoice_date"], errors="coerce", dayfirst=True)

    if "quantity" in X.columns:
        X["quantity"] = pd.to_numeric(X["quantity"], errors="coerce")

    if "unit_price" in X.columns:
        X["unit_price"] = pd.to_numeric(X["unit_price"], errors="coerce")

    if {"quantity", "unit_price"}.issubset(X.columns):
        X["line_revenue"] = X["quantity"] * X["unit_price"]

    X["source_system"] = "uci_online_retail"

    X.to_csv(RAW_DIR / "online_retail_raw.csv", index=False)
    X.to_parquet(PROCESSED_DIR / "transactions_uci.parquet", index=False)

    print("Saved transactions_uci.parquet")


if __name__ == "__main__":
    main()