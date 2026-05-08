import { EmptyState } from "./empty-state";

export function OverrideBreakdownTable({
  items = [],
}: {
  items?: {
    baseline_action: string;
    total_reviews: number;
    approve_count: number;
    reject_count: number;
    defer_count: number;
    override_rate: number;
  }[];
}) {
  if (!items.length) {
    return (
      <EmptyState
        title="No override breakdown yet"
        description="Review some product decisions to see which baseline actions are most often rejected or deferred."
      />
    );
  }

  return (
    <div className="overflow-x-auto rounded-2xl border">
      <table className="w-full text-sm">
        <thead className="bg-muted/50 text-left">
          <tr>
            <th className="px-4 py-3">Baseline Action</th>
            <th className="px-4 py-3">Total Reviews</th>
            <th className="px-4 py-3">Approved</th>
            <th className="px-4 py-3">Rejected</th>
            <th className="px-4 py-3">Deferred</th>
            <th className="px-4 py-3">Override Rate</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.baseline_action} className="border-t">
              <td className="px-4 py-3">{item.baseline_action}</td>
              <td className="px-4 py-3">{item.total_reviews}</td>
              <td className="px-4 py-3">{item.approve_count}</td>
              <td className="px-4 py-3">{item.reject_count}</td>
              <td className="px-4 py-3">{item.defer_count}</td>
              <td className="px-4 py-3">{item.override_rate}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}