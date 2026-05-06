from __future__ import annotations

import json
from pathlib import Path

from omnisight.decision.reasoning import reason_about_product
from omnisight.retrieval.evidence_builder import EvidenceBuilder

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def main() -> None:
    product_id = input("Enter product_id: ").strip()
    if not product_id:
        print("No product_id entered.")
        return

    builder = EvidenceBuilder()
    evidence = builder.build(product_id)

    result = reason_about_product(evidence)

    print("=" * 80)
    print("EVIDENCE PACKAGE")
    print("=" * 80)
    print(json.dumps(evidence, indent=2, default=str))

    print("\n" + "=" * 80)
    print("LLM REASONING OUTPUT")
    print("=" * 80)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()