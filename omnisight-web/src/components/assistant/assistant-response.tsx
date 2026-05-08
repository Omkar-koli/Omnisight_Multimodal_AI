"use client";

type ParsedCard = {
  rank: number;
  title: string;
  status?: string;
  keywords: string[];
  reason: string;
  confidence?: string;
  watchSignal?: string;
  raw: string;
};

function cleanText(value: string) {
  return value.replace(/\*\*/g, "").trim();
}

function normalizeContent(content: string) {
  return content
    .replace(/\r/g, "")
    .replace(/(\d+\.\s+\*\*)/g, "\n$1")
    .replace(/(\d+\.\s+[A-Za-z])/g, "\n$1")
    .trim();
}

function parseAssistantContent(content: string) {
  const normalized = normalizeContent(content);

  const numberedMatches = normalized.match(/\n?\d+\.\s[\s\S]*?(?=(\n\d+\.\s)|$)/g) || [];

  const intro = normalized.split(/\n?\d+\.\s/)[0]?.trim() || "";

  const cards: ParsedCard[] = numberedMatches.map((block) => {
    const cleanedBlock = block.trim().replace(/^\d+\.\s*/, "");
    const rankMatch = block.match(/^\s*(\d+)\./);
    const rank = rankMatch ? Number(rankMatch[1]) : 0;

    const parts = cleanedBlock.split(/\s+-\s+/).map((p) => p.trim()).filter(Boolean);

    const title = cleanText(parts[0] || cleanedBlock);

    let status = "";
    let keywords: string[] = [];
    let reasonParts: string[] = [];
    let confidence = "";
    let watchSignal = "";

    for (let i = 1; i < parts.length; i++) {
      const part = cleanText(parts[i]);

      if (
        !status &&
        !/^keywords?:/i.test(part) &&
        !/^confidence:/i.test(part) &&
        !/^watch signal:/i.test(part) &&
        !/^signals?:/i.test(part)
      ) {
        status = part;
        continue;
      }

      if (/^keywords?:/i.test(part)) {
        keywords = part
          .replace(/^keywords?:/i, "")
          .split(",")
          .map((k) => k.trim())
          .filter(Boolean);
        continue;
      }

      if (/^confidence:/i.test(part)) {
        confidence = part.replace(/^confidence:/i, "").trim();
        continue;
      }

      if (/^watch signal:/i.test(part)) {
        watchSignal = part.replace(/^watch signal:/i, "").trim();
        continue;
      }

      if (/^signals?:/i.test(part)) {
        reasonParts.push(part.replace(/^signals?:/i, "").trim());
        continue;
      }

      reasonParts.push(part);
    }

    return {
      rank,
      title,
      status,
      keywords,
      reason: reasonParts.join(". ").trim(),
      confidence,
      watchSignal,
      raw: cleanedBlock,
    };
  });

  return {
    intro,
    cards,
    fallback: normalized,
  };
}

function getStatusColor(status?: string) {
  const value = (status || "").toLowerCase();

  if (value.includes("trending up")) {
    return "bg-green-100 text-green-700 border-green-200";
  }
  if (value.includes("trending down")) {
    return "bg-red-100 text-red-700 border-red-200";
  }
  if (value.includes("stable")) {
    return "bg-slate-100 text-slate-700 border-slate-200";
  }
  if (value.includes("speculative")) {
    return "bg-amber-100 text-amber-700 border-amber-200";
  }
  if (value.includes("moderate")) {
    return "bg-blue-100 text-blue-700 border-blue-200";
  }

  return "bg-muted text-foreground border-border";
}

function StatusSummary({ cards }: { cards: ParsedCard[] }) {
  const total = cards.length || 1;

  const counts = cards.reduce<Record<string, number>>((acc, card) => {
    const key = card.status || "Other";
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});

  const items = Object.entries(counts);

  if (!items.length) return null;

  return (
    <div className="mb-4 rounded-2xl border bg-background p-3">
      <div className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Quick Summary
      </div>

      <div className="space-y-3">
        {items.map(([label, value]) => {
          const pct = Math.round((value / total) * 100);
          return (
            <div key={label}>
              <div className="mb-1 flex items-center justify-between text-xs">
                <span className="font-medium">{label}</span>
                <span className="text-muted-foreground">
                  {value} / {total}
                </span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-foreground"
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ProductCard({ card }: { card: ParsedCard }) {
  return (
    <div className="rounded-2xl border bg-background p-3 shadow-sm">
      <div className="mb-2 flex items-start justify-between gap-3">
        <div>
          {card.rank ? (
            <div className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              Rank #{card.rank}
            </div>
          ) : null}
          <div className="mt-1 text-sm font-semibold leading-5">{card.title}</div>
        </div>

        {card.status ? (
          <span
            className={`shrink-0 rounded-full border px-2.5 py-1 text-[11px] font-medium ${getStatusColor(
              card.status
            )}`}
          >
            {card.status}
          </span>
        ) : null}
      </div>

      {card.keywords.length > 0 ? (
        <div className="mb-3">
          <div className="mb-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            Keywords
          </div>
          <div className="flex flex-wrap gap-2">
            {card.keywords.slice(0, 4).map((keyword, idx) => (
              <span
                key={`${keyword}-${idx}`}
                className="rounded-full bg-muted px-2.5 py-1 text-[11px]"
              >
                {keyword}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      {card.reason ? (
        <div className="mb-3 text-sm leading-6 text-foreground/90">{card.reason}</div>
      ) : null}

      {(card.confidence || card.watchSignal) ? (
        <div className="grid gap-2 md:grid-cols-2">
          {card.confidence ? (
            <div className="rounded-xl bg-muted/60 p-2">
              <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                Confidence
              </div>
              <div className="mt-1 text-xs font-medium">{card.confidence}</div>
            </div>
          ) : null}

          {card.watchSignal ? (
            <div className="rounded-xl bg-muted/60 p-2">
              <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                Watch Signal
              </div>
              <div className="mt-1 text-xs font-medium">{card.watchSignal}</div>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export function AssistantResponse({ content }: { content: string }) {
  const parsed = parseAssistantContent(content);

  if (!parsed.cards.length) {
    return (
      <div className="space-y-3">
        {parsed.fallback.split("\n").map((line, idx) => (
          <p key={idx} className="text-sm leading-6 whitespace-pre-wrap">
            {line}
          </p>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {parsed.intro ? (
        <div className="rounded-2xl border bg-muted/50 p-3 text-sm leading-6">
          {parsed.intro}
        </div>
      ) : null}

      <StatusSummary cards={parsed.cards} />

      <div className="space-y-3">
        {parsed.cards.map((card, idx) => (
          <ProductCard key={`${card.title}-${idx}`} card={card} />
        ))}
      </div>
    </div>
  );
}