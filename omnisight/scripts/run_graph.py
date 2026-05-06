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

    result = graph.invoke(
        {"product_id": product_id},
        config=config,
    )

    print("=" * 90)
    print("GRAPH FINAL STATE")
    print("=" * 90)
    print(json.dumps(result, indent=2, default=str))

    final_response = result.get("final_response", {})
    print("\n" + "=" * 90)
    print("FINAL RESPONSE")
    print("=" * 90)
    print(json.dumps(final_response, indent=2, default=str))


if __name__ == "__main__":
    main()