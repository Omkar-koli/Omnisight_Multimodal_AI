import { EmptyState } from "./empty-state";

export function JobRunsTable({
  items = [],
}: {
  items?: {
    id: number;
    job_name: string;
    status: string;
    started_at: string;
    finished_at: string;
    duration_seconds: number;
    message: string;
  }[];
}) {
  if (!items.length) {
    return (
      <EmptyState
        title="No job history yet"
        description="Job runs will appear here after refresh jobs execute."
      />
    );
  }

  return (
    <div className="overflow-x-auto rounded-2xl border">
      <table className="w-full text-sm">
        <thead className="bg-muted/50 text-left">
          <tr>
            <th className="px-4 py-3">Job</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3">Started</th>
            <th className="px-4 py-3">Finished</th>
            <th className="px-4 py-3">Duration (s)</th>
            <th className="px-4 py-3">Message</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id} className="border-t">
              <td className="px-4 py-3">{item.job_name}</td>
              <td className="px-4 py-3">{item.status}</td>
              <td className="px-4 py-3">{item.started_at}</td>
              <td className="px-4 py-3">{item.finished_at}</td>
              <td className="px-4 py-3">{item.duration_seconds}</td>
              <td className="px-4 py-3">{item.message}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}