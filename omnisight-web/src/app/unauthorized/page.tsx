export default function UnauthorizedPage() {
  return (
    <div className="flex min-h-[70vh] items-center justify-center">
      <div className="max-w-lg rounded-2xl border p-8 text-center">
        <h1 className="text-2xl font-semibold">Unauthorized</h1>
        <p className="mt-2 text-muted-foreground">
          Your current role does not have access to this page.
        </p>
      </div>
    </div>
  );
}