export function EmptyState({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-md border border-dashed bg-muted/30 px-6 py-10 text-center">
      <div className="text-sm font-medium text-foreground">{title}</div>
      <div className="mt-1.5 text-xs text-muted-foreground">{description}</div>
    </div>
  );
}
