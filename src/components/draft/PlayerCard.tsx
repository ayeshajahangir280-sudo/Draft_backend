import type { Player } from "@/data/draft";

export function PlayerCard({
  player,
  onSelect,
  disabled,
}: {
  player: Player;
  onSelect: (p: Player) => void;
  disabled?: boolean;
}) {
  return (
    <div className="group flex items-center gap-3 rounded-xl border border-border bg-card/70 p-3 transition-colors hover:border-accent/60 hover:bg-card">
      <img
        src={player.photo}
        alt={player.name}
        loading="lazy"
        className="h-14 w-14 shrink-0 rounded-lg object-cover ring-1 ring-border"
      />
      <div className="min-w-0 flex-1">
        <p className="truncate font-display text-base font-semibold tracking-wide text-foreground">
          {player.name}
        </p>
        <p className="text-xs text-muted-foreground">{player.role}</p>
        <span className="mt-1 inline-block rounded bg-secondary px-1.5 py-0.5 text-[10px] font-semibold tracking-widest text-secondary-foreground">
          CAT {player.category}
        </span>
      </div>
      <button
        type="button"
        disabled={disabled}
        onClick={() => onSelect(player)}
        className="rounded-lg bg-accent px-3 py-2 text-xs font-bold tracking-widest text-accent-foreground transition-transform hover:scale-105 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:scale-100"
      >
        SELECT
      </button>
    </div>
  );
}
