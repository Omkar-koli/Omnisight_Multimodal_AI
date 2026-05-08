"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import {
  getDecisionHistory,
  submitDecisionReview,
} from "@/lib/api";
import {
  ReviewAction,
  ReviewActionResponse,
} from "@/lib/types";
import { canReview } from "@/lib/roles";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function ReviewPanel({ productId }: { productId: string }) {
  const { data: session } = useSession();
  const role = session?.user?.role || "viewer";
  const reviewerName =
    session?.user?.name || session?.user?.email || "Unknown Reviewer";

  const [notes, setNotes] = useState("");
  const [action, setAction] = useState<ReviewAction>("APPROVE");
  const [history, setHistory] = useState<ReviewActionResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  async function loadHistory() {
    try {
      const res = await getDecisionHistory(productId);
      setHistory(res.items);
    } catch (err: any) {
      setMessage(String(err));
    }
  }

  useEffect(() => {
    loadHistory();
  }, [productId]);

  async function handleSubmit() {
    if (!canReview(role)) {
      setMessage("Your role cannot submit review actions.");
      return;
    }

    try {
      setLoading(true);
      setMessage("");

      await submitDecisionReview(productId, {
        reviewer_name: reviewerName,
        review_action: action,
        notes,
      });

      setNotes("");
      setMessage("Review saved.");
      await loadHistory();
    } catch (err: any) {
      setMessage(String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <Card className="rounded-2xl">
        <CardHeader>
          <CardTitle>Review Decision</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-md border px-3 py-2 text-sm">
            Signed in as: {reviewerName} ({role})
          </div>

          <select
            className="w-full rounded-md border px-3 py-2"
            value={action}
            onChange={(e) => setAction(e.target.value as ReviewAction)}
            disabled={!canReview(role)}
          >
            <option value="APPROVE">Approve</option>
            <option value="REJECT">Reject</option>
            <option value="DEFER">Defer</option>
          </select>

          <textarea
            className="min-h-[120px] w-full rounded-md border px-3 py-2"
            placeholder="Reviewer notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            disabled={!canReview(role)}
          />

          <Button onClick={handleSubmit} disabled={loading || !canReview(role)}>
            {loading ? "Saving..." : "Save Review"}
          </Button>

          {message ? (
            <div className="text-sm text-muted-foreground">{message}</div>
          ) : null}
        </CardContent>
      </Card>

      <Card className="rounded-2xl">
        <CardHeader>
          <CardTitle>Review History</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {history.length === 0 ? (
            <div className="text-sm text-muted-foreground">No reviews yet.</div>
          ) : (
            history.map((item) => (
              <div key={item.id} className="rounded-xl border p-3">
                <div className="font-medium">
                  {item.review_action} by {item.reviewer_name}
                </div>
                <div className="text-xs text-muted-foreground">
                  {item.created_at}
                </div>
                <div className="mt-2 text-sm">{item.notes}</div>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}