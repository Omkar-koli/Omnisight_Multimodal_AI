"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { ReviewQueueItem } from "@/lib/types";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

export function ReviewOpsTable({ items }: { items: ReviewQueueItem[] }) {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("ALL");

  const filtered = useMemo(() => {
    return items.filter((item) => {
      const matchesSearch =
        `${item.product_id} ${item.reviewer_name} ${item.notes}`
          .toLowerCase()
          .includes(search.toLowerCase());

      const matchesFilter =
        filter === "ALL" ? true : item.review_action === filter;

      return matchesSearch && matchesFilter;
    });
  }, [items, search, filter]);

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row">
        <Input
          placeholder="Search by product, reviewer, or notes"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />

        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="h-10 rounded-md border bg-background px-3 text-sm"
        >
          <option value="ALL">ALL</option>
          <option value="APPROVE">APPROVE</option>
          <option value="REJECT">REJECT</option>
          <option value="DEFER">DEFER</option>
        </select>
      </div>

      <div className="overflow-x-auto rounded-2xl border">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-left">
            <tr>
              <th className="px-4 py-3">Product</th>
              <th className="px-4 py-3">Reviewer</th>
              <th className="px-4 py-3">Action</th>
              <th className="px-4 py-3">Notes</th>
              <th className="px-4 py-3">Created</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((item) => (
              <tr key={item.id} className="border-t">
                <td className="px-4 py-3">
                  <Link href={`/products/${item.product_id}`} className="hover:underline">
                    {item.product_id}
                  </Link>
                </td>
                <td className="px-4 py-3">{item.reviewer_name}</td>
                <td className="px-4 py-3">
                  <Badge>{item.review_action}</Badge>
                </td>
                <td className="px-4 py-3">{item.notes}</td>
                <td className="px-4 py-3">{item.created_at}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}