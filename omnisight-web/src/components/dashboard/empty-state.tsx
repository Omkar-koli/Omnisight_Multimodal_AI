export function EmptyState({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-2xl border border-dashed p-8 text-center">
      <div className="text-base font-medium">{title}</div>
      <div className="mt-2 text-sm text-muted-foreground">{description}</div>
    </div>
  );
}