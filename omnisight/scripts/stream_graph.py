from __future__ import annotations

import json

from omnisight.graph.build_graph import build_omnisight_graph


def main() -> None:
    product_id = input("Enter product_id: ").strip()
    if not product_id:
        print("No product_id entered.")
        return

    graph = build_omnisight_graph()

    config = {
        "configurable": {
            "thread_id": f"omnisight-{product_id}"
        }
    }

    print("=" * 90)
    print("STREAMING GRAPH UPDATES")
    print("=" * 90)

    for chunk in graph.stream(
        {"product_id": product_id},
        config=config,
        stream_mode="updates",
        version="v2",
    ):
        if chunk["type"] == "updates":
            print("\n--- UPDATE ---")
            print(json.dumps(chunk["data"], indent=2, default=str))

    print("\nDone.")


if __name__ == "__main__":
    main()