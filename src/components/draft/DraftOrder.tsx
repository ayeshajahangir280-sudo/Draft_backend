import type { Team } from "@/data/draft";

export function DraftOrder({
  order,
  currentIndex,
  picks,
  onOpenTeam,
}: {
  order: Team[];
  currentIndex: number;
  picks: Record<string, Array<string | number>>;
  onOpenTeam: (t: Team) => void;
}) {
  const current = order[currentIndex];
  return (
    <div className="flex h-full flex-col gap-4">
      <div>
        <h2 className="font-display text-sm font-bold tracking-[0.25em] text-muted-foreground">
          DRAFT ORDER
        </h2>
        <div className="mt-3 rounded-xl border border-accent/40 bg-gradient-to-br from-accent/20 to-transparent p-3">
          <p className="text-[10px] font-bold tracking-[0.25em] text-accent">CURRENT PICK</p>
          <p className="font-display text-lg font-bold leading-tight text-foreground">
            {current ? current.name : "Round complete"}
          </p>
        </div>
      </div>

      <ol className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
        {order.map((t, i) => {
          const done = i < currentIndex;
          const active = i === currentIndex;
          return (
            <li key={t.id}>
              <button
                type="button"
                onClick={() => onOpenTeam(t)}
                className={`flex w-full items-center gap-3 rounded-lg border px-3 py-2.5 text-left transition-colors ${
                  active
                    ? "border-accent bg-accent/15"
                    : done
                      ? "border-border/60 bg-card/40 opacity-70"
                      : "border-border bg-card/60 hover:border-accent/50"
                }`}
              >
                <span className="w-5 font-display text-sm font-bold text-muted-foreground">
                  {i + 1}
                </span>
                <span className="min-w-0 flex-1 truncate text-sm font-semibold text-foreground">
                  {t.name}
                </span>
                {done && <span className="text-xs font-bold text-emerald-400">✓</span>}
                {active && (
                  <span className="text-[10px] font-bold tracking-widest text-accent">CURRENT</span>
                )}
                <span className="rounded bg-secondary px-1.5 py-0.5 text-[10px] font-semibold text-secondary-foreground">
                  {(picks[String(t.id)] ?? []).length}
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
