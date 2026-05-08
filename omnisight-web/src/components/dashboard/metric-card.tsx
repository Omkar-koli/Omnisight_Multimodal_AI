import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

type Trend = "up" | "down" | "neutral";

export function MetricCard({
  title,
  value,
  subtitle,
  trend,
  delta,
  accent = false,
}: {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: Trend;
  delta?: string;
  accent?: boolean;
}) {
  const TrendIcon =
    trend === "up" ? TrendingUp : trend === "down" ? TrendingDown : Minus;
  const trendColor =
    trend === "up"
      ? "text-emerald-600 dark:text-emerald-400"
      : trend === "down"
      ? "text-red-500 dark:text-red-400"
      : "text-muted-foreground";

  return (
    <Card
      className={cn(
        "rounded-2xl relative overflow-hidden border transition-shadow hover:shadow-md",
        accent && "border-primary/30"
      )}
    >
      {/* Indigo accent stripe on top */}
      <div
        className={cn(
          "absolute inset-x-0 top-0 h-0.5 rounded-t-2xl",
          accent ? "bg-primary" : "bg-primary/25"
        )}
      />

      <CardContent className="pt-5 pb-4 px-4">
        <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {title}
        </div>
        <div className="mt-1.5 text-2xl font-bold text-foreground tabular-nums">
          {value}
        </div>
        {(subtitle || delta) && (
          <div className="mt-1.5 flex items-center gap-1.5">
            {trend && (
              <TrendIcon className={cn("h-3 w-3 shrink-0", trendColor)} />
            )}
            {delta && (
              <span className={cn("text-xs font-medium", trendColor)}>
                {delta}
              </span>
            )}
            {subtitle && (
              <span className="text-xs text-muted-foreground">{subtitle}</span>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
