import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { DraftOrder } from "@/components/draft/DraftOrder";
import { PlayerCard } from "@/components/draft/PlayerCard";
import {
  CATEGORIES,
  PLAYERS,
  TEAMS,
  shuffle,
  type Category,
  type Player,
  type Team,
} from "@/data/draft";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Stride Player Draft — Live Draft Board" },
      {
        name: "description",
        content:
          "Interactive cricket player draft board: turn-based manager picks, category filters and live team rosters.",
      },
      { property: "og:title", content: "Stride Player Draft — Live Draft Board" },
      {
        property: "og:description",
        content: "Interactive cricket player draft board demo with turn-based manager picks.",
      },
    ],
  }),
  component: DraftScreen,
});

type Pick = { player: Player; team: Team; round: number };

function DraftScreen() {
  const [order, setOrder] = useState<Team[]>(() => shuffle(TEAMS));
  const [currentIndex, setCurrentIndex] = useState(0);
  const [round, setRound] = useState(1);
  const [picks, setPicks] = useState<Pick[]>([]);
  const [category, setCategory] = useState<Category>("A");
  const [confirming, setConfirming] = useState<Player | null>(null);
  const [lastPick, setLastPick] = useState<Pick | null>(null);
  const [rosterTeam, setRosterTeam] = useState<Team | null>(null);

  const takenIds = useMemo(() => new Set(picks.map((p) => p.player.id)), [picks]);
  const available = useMemo(
    () => PLAYERS.filter((p) => !takenIds.has(p.id) && p.category === category),
    [takenIds, category],
  );
  const picksByTeam = useMemo(() => {
    const m: Record<string, string[]> = {};
    for (const p of picks) (m[p.team.id] ??= []).push(p.player.id);
    return m;
  }, [picks]);

  const currentTeam = order[currentIndex];
  const roundComplete = currentIndex >= order.length;

  function confirm() {
    if (!confirming || !currentTeam) return;
    const pick: Pick = { player: confirming, team: currentTeam, round };
    setPicks((p) => [...p, pick]);
    setLastPick(pick);
    setConfirming(null);
    setCurrentIndex((i) => i + 1);
  }

  function startNextRound() {
    setOrder(shuffle(TEAMS));
    setCurrentIndex(0);
    setRound((r) => r + 1);
    setLastPick(null);
  }

  function resetDemo() {
    setOrder(shuffle(TEAMS));
    setCurrentIndex(0);
    setRound(1);
    setPicks([]);
    setLastPick(null);
    setConfirming(null);
    setCategory("A");
  }

  return (
    <main className="min-h-screen stage-bg">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-6 py-3">
        <div className="flex items-baseline gap-3">
          <h1 className="font-display text-2xl font-bold tracking-[0.18em] text-foreground">
            STRIDE PLAYER DRAFT
          </h1>
          <span className="rounded bg-accent px-2 py-0.5 font-display text-xs font-bold tracking-widest text-accent-foreground">
            ROUND {round}
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <span className="tracking-[0.2em]">DEMO ADMIN CONTROLS</span>
          <span className="opacity-40">|</span>
          <span>Active Category</span>
          {CATEGORIES.map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => setCategory(c)}
              className={`h-7 w-7 rounded border text-xs font-bold transition-colors ${
                category === c
                  ? "border-accent bg-accent text-accent-foreground"
                  : "border-border text-muted-foreground hover:border-accent/60"
              }`}
            >
              {c}
            </button>
          ))}
          <button
            type="button"
            onClick={() => {
              setOrder(shuffle(TEAMS));
              setCurrentIndex(0);
            }}
            className="rounded border border-border px-2 py-1 hover:border-accent/60"
          >
            Randomize Order
          </button>
          <button
            type="button"
            onClick={startNextRound}
            className="rounded border border-border px-2 py-1 hover:border-accent/60"
          >
            Start Next Round
          </button>
          <button
            type="button"
            onClick={resetDemo}
            className="rounded border border-border px-2 py-1 hover:border-destructive/60"
          >
            Reset Demo
          </button>
        </div>
      </header>

      <div className="grid gap-4 p-4 lg:h-[calc(100vh-57px)] lg:grid-cols-[260px_1fr_360px]">
        <section className="min-h-0 rounded-2xl border border-border bg-card/40 p-4">
          <DraftOrder
            order={order}
            currentIndex={currentIndex}
            picks={picksByTeam}
            onOpenTeam={setRosterTeam}
          />
        </section>

        <section className="flex min-h-[420px] items-center justify-center rounded-2xl border border-border bg-gradient-to-b from-card/70 to-card/20 p-8 text-center">
          {roundComplete ? (
            <div className="pop-in">
              <p className="font-display text-5xl font-bold tracking-[0.15em] text-accent">
                ROUND {round} COMPLETE
              </p>
              <p className="mt-3 text-sm text-muted-foreground">
                All 8 managers have made their pick.
              </p>
              <button
                type="button"
                onClick={startNextRound}
                className="mt-8 rounded-xl bg-accent px-8 py-3 font-display text-lg font-bold tracking-[0.2em] text-accent-foreground transition-transform hover:scale-105"
              >
                START NEXT ROUND
              </button>
            </div>
          ) : lastPick ? (
            <div key={lastPick.player.id} className="pop-in">
              <p className="font-display text-sm font-bold tracking-[0.4em] text-accent">
                PLAYER SELECTED
              </p>
              <img
                src={lastPick.player.photo}
                alt={lastPick.player.name}
                className="mx-auto mt-5 h-44 w-44 rounded-2xl object-cover ring-2 ring-accent/60"
              />
              <h2 className="mt-5 font-display text-5xl font-bold tracking-wide text-foreground">
                {lastPick.player.name}
              </h2>
              <p className="mt-1 text-lg text-muted-foreground">
                {lastPick.player.role} · Category {lastPick.player.category}
              </p>
              <p className="mt-6 font-display text-2xl font-bold tracking-[0.15em] text-accent">
                SELECTED BY {lastPick.team.name.toUpperCase()}
              </p>
              <p className="mt-6 text-sm text-muted-foreground">
                Next up:{" "}
                <span className="font-semibold text-foreground">{currentTeam?.name}</span>
              </p>
            </div>
          ) : (
            <div className="pop-in">
              <p className="font-display text-sm font-bold tracking-[0.4em] text-muted-foreground">
                ON THE CLOCK
              </p>
              <h2 className="mt-4 font-display text-6xl font-bold tracking-wide text-foreground">
                {currentTeam?.name.toUpperCase()} ARE ON THE CLOCK
              </h2>
              <p className="mt-4 text-muted-foreground">
                Select a player from the available players
              </p>
            </div>
          )}
        </section>

        <section className="flex min-h-0 flex-col rounded-2xl border border-border bg-card/40 p-4">
          <h2 className="font-display text-sm font-bold tracking-[0.25em] text-muted-foreground">
            AVAILABLE PLAYERS
          </h2>
          <div className="mt-3 flex gap-2">
            {CATEGORIES.map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => setCategory(c)}
                className={`flex-1 rounded-lg border py-1.5 font-display text-sm font-bold tracking-widest transition-colors ${
                  category === c
                    ? "border-accent bg-accent text-accent-foreground"
                    : "border-border text-muted-foreground hover:border-accent/60"
                }`}
              >
                {c}
              </button>
            ))}
          </div>
          <div className="mt-3 min-h-0 flex-1 space-y-2 overflow-y-auto pr-1 lg:max-h-none max-h-[460px]">
            {available.map((p) => (
              <PlayerCard
                key={p.id}
                player={p}
                disabled={roundComplete}
                onSelect={setConfirming}
              />
            ))}
            {available.length === 0 && (
              <p className="py-10 text-center text-sm text-muted-foreground">
                No players left in Category {category}.
              </p>
            )}
          </div>
        </section>
      </div>

      {confirming && currentTeam && (
        <Overlay onClose={() => setConfirming(null)}>
          <h3 className="font-display text-2xl font-bold tracking-wide text-foreground">
            Confirm Player Selection?
          </h3>
          <div className="mt-5 flex items-center gap-4">
            <img
              src={confirming.photo}
              alt={confirming.name}
              className="h-20 w-20 rounded-xl object-cover ring-1 ring-border"
            />
            <div className="text-left">
              <p className="font-display text-xl font-bold text-foreground">{confirming.name}</p>
              <p className="text-sm text-muted-foreground">
                {confirming.role} · Category {confirming.category}
              </p>
            </div>
          </div>
          <p className="mt-5 text-xs tracking-[0.2em] text-muted-foreground">SELECTED BY</p>
          <p className="font-display text-xl font-bold text-accent">{currentTeam.name}</p>
          <div className="mt-6 flex justify-end gap-3">
            <button
              type="button"
              onClick={() => setConfirming(null)}
              className="rounded-lg border border-border px-4 py-2 text-sm font-semibold text-muted-foreground hover:text-foreground"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={confirm}
              className="rounded-lg bg-accent px-5 py-2 text-sm font-bold tracking-wide text-accent-foreground transition-transform hover:scale-105"
            >
              Confirm Selection
            </button>
          </div>
        </Overlay>
      )}

      {rosterTeam && (
        <Overlay onClose={() => setRosterTeam(null)}>
          <h3 className="font-display text-2xl font-bold tracking-wide text-foreground">
            {rosterTeam.name}
          </h3>
          <p className="mt-1 text-xs tracking-[0.25em] text-muted-foreground">SELECTED PLAYERS</p>
          <ul className="mt-4 space-y-2 text-left">
            {picks
              .filter((p) => p.team.id === rosterTeam.id)
              .map((p) => (
                <li
                  key={p.player.id}
                  className="flex items-center gap-3 rounded-lg border border-border bg-card/60 p-2"
                >
                  <img src={p.player.photo} alt="" className="h-9 w-9 rounded object-cover" />
                  <span className="text-sm text-foreground">
                    {p.player.name} — {p.player.role} — Category {p.player.category}
                  </span>
                </li>
              ))}
            {picks.filter((p) => p.team.id === rosterTeam.id).length === 0 && (
              <li className="py-6 text-center text-sm text-muted-foreground">No picks yet.</li>
            )}
          </ul>
          <div className="mt-6 text-right">
            <button
              type="button"
              onClick={() => setRosterTeam(null)}
              className="rounded-lg border border-border px-4 py-2 text-sm font-semibold text-muted-foreground hover:text-foreground"
            >
              Close
            </button>
          </div>
        </Overlay>
      )}
    </main>
  );
}

function Overlay({ children, onClose }: { children: React.ReactNode; onClose: () => void }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="pop-in w-full max-w-md rounded-2xl border border-border bg-popover p-6 text-center shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  );
}
