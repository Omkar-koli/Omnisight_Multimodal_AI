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
        "rounded-xl relative overflow-hidden border bg-card transition-shadow hover:shadow-sm",
        accent && "border-primary/40"
      )}
    >
      {accent ? (
        <div className="absolute inset-y-0 left-0 w-0.5 bg-primary" />
      ) : null}

      <CardContent className="px-4 py-3.5">
        <div className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
          {title}
        </div>
        <div className="mt-1.5 text-2xl font-semibold tabular-nums text-foreground">
          {value}
        </div>
        {(subtitle || delta) && (
          <div className="mt-1 flex items-center gap-1.5">
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
