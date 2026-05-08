import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SystemStatusResponse } from "@/lib/types";

export function SystemStatusCard({ status }: { status: SystemStatusResponse }) {
  return (
    <Card className="rounded-2xl">
      <CardHeader>
        <CardTitle>System Status</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <div>API: {status.api_status}</div>
        <div>Qdrant: {status.qdrant_status}</div>
        <div>Recommendations Loaded: {status.recommendations_loaded ? "Yes" : "No"}</div>
        <div>Review DB Ready: {status.review_db_ready ? "Yes" : "No"}</div>
        <div>Total Recommendations: {status.total_recommendations}</div>
        <div>Total Reviews: {status.total_reviews}</div>
      </CardContent>
    </Card>
  );
}