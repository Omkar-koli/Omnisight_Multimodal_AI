"use client";

import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "./empty-state";

export function RecentDecisionsTable({
  items = [],
}: {
  items?: {
    id: number;
    product_id: string;
    title: string;
    baseline_action: string;
    baseline_confidence: number;
    llm_final_action: string;
    llm_confidence: number;
    created_at: string;
  }[];
}) {
  if (!items.length) {
    return (
      <EmptyState
        title="No recent decisions yet"
        description="Open a few product pages so OmniSight can log decision events here."
      />
    );
  }

  return (
    <div className="overflow-x-auto rounded-2xl border">
      <table className="w-full text-sm">
        <thead className="bg-muted/50 text-left">
          <tr>
            <th className="px-4 py-3">Product</th>
            <th className="px-4 py-3">Baseline</th>
            <th className="px-4 py-3">LLM</th>
            <th className="px-4 py-3">LLM Confidence</th>
            <th className="px-4 py-3">Created</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id} className="border-t">
              <td className="px-4 py-3">
                <Link href={`/products/${item.product_id}`} className="hover:underline">
                  <div className="font-medium">{item.title}</div>
                  <div className="text-xs text-muted-foreground">{item.product_id}</div>
                </Link>
              </td>
              <td className="px-4 py-3">
                <Badge>{item.baseline_action}</Badge>
              </td>
              <td className="px-4 py-3">
                <Badge>{item.llm_final_action}</Badge>
              </td>
              <td className="px-4 py-3">{item.llm_confidence}</td>
              <td className="px-4 py-3">{item.created_at}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}