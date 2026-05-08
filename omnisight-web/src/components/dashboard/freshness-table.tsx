import { EmptyState } from "./empty-state";

export function FreshnessTable({
  items = [],
}: {
  items?: {
    dataset_name: string;
    last_refreshed_at: string;
    freshness_status: string;
    notes: string;
  }[];
}) {
  if (!items.length) {
    return (
      <EmptyState
        title="No freshness data yet"
        description="Run refresh jobs to populate dataset freshness."
      />
    );
  }

  return (
    <div className="overflow-x-auto rounded-2xl border">
      <table className="w-full text-sm">
        <thead className="bg-muted/50 text-left">
          <tr>
            <th className="px-4 py-3">Dataset</th>
            <th className="px-4 py-3">Last Refreshed</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3">Notes</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.dataset_name} className="border-t">
              <td className="px-4 py-3">{item.dataset_name}</td>
              <td className="px-4 py-3">{item.last_refreshed_at}</td>
              <td className="px-4 py-3">{item.freshness_status}</td>
              <td className="px-4 py-3">{item.notes}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}