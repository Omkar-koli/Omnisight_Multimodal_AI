"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { QueueItem } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";

export function QueueTable({ items = [] }: { items?: QueueItem[] }) {
  const [search, setSearch] = useState("");
  const [actionFilter, setActionFilter] = useState("ALL");

  const filtered = useMemo(() => {
    return (items ?? []).filter((item) => {
      const matchesSearch =
        `${item.product_id} ${item.title}`.toLowerCase().includes(search.toLowerCase());

      const matchesAction =
        actionFilter === "ALL" ? true : item.action === actionFilter;

      return matchesSearch && matchesAction;
    });
  }, [items, search, actionFilter]);

  const actions = ["ALL", ...Array.from(new Set((items ?? []).map((i) => i.action)))];

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row">
        <Input
          placeholder="Search by product ID or title"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />

        <select
          value={actionFilter}
          onChange={(e) => setActionFilter(e.target.value)}
          className="h-10 rounded-md border bg-background px-3 text-sm"
        >
          {actions.map((action) => (
            <option key={action} value={action}>
              {action}
            </option>
          ))}
        </select>
      </div>

      <div className="overflow-x-auto rounded-2xl border">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-left">
            <tr>
              <th className="px-4 py-3">Product</th>
              <th className="px-4 py-3">Action</th>
              <th className="px-4 py-3">Confidence</th>
              <th className="px-4 py-3">Days to Stockout</th>
              <th className="px-4 py-3">Stockout Risk</th>
              <th className="px-4 py-3">Review Risk</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((item) => (
              <tr key={item.product_id} className="border-t">
                <td className="px-4 py-3">
                  <Link href={`/products/${item.product_id}`} className="hover:underline">
                    <div className="font-medium">{item.title}</div>
                    <div className="text-xs text-muted-foreground">{item.product_id}</div>
                  </Link>
                </td>
                <td className="px-4 py-3">
                  <Badge>{item.action}</Badge>
                </td>
                <td className="px-4 py-3">{item.confidence}</td>
                <td className="px-4 py-3">{item.days_to_stockout}</td>
                <td className="px-4 py-3">{item.stockout_risk_score}</td>
                <td className="px-4 py-3">{item.review_risk_score}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}