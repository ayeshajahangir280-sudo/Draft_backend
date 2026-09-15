import { createFileRoute } from "@tanstack/react-router";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { DraftOrder } from "@/components/draft/DraftOrder";
import { PlayerCard } from "@/components/draft/PlayerCard";
import {
  DEFAULT_DRAFT_ID,
  draftWsUrl,
  fetchDraftState,
  randomizeOrStart,
  selectDraftPlayer,
  setDraftCategory,
  startNextRound as startNextRoundApi,
  type DraftEvent,
  type DraftPick,
  type DraftState,
} from "@/lib/draftApi";
import {
  CATEGORIES,
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

type Pick = { player: Player; team: Team; round: number; pick_number?: number };
type ConnectionStatus = "SYNCING" | "LIVE" | "RECONNECTING" | "OFFLINE";

function DraftScreen() {
  const draftId = DEFAULT_DRAFT_ID;
  const [draftState, setDraftState] = useState<DraftState | null>(null);
  const [connection, setConnection] = useState<ConnectionStatus>("SYNCING");
  const [error, setError] = useState<string | null>(null);
  const [pendingActionId, setPendingActionId] = useState<string | null>(null);
  const [round, setRound] = useState(1);
  const [picks, setPicks] = useState<Pick[]>([]);
  const [category, setCategory] = useState<Category>("A");
  const [confirming, setConfirming] = useState<Player | null>(null);
  const [lastPick, setLastPick] = useState<Pick | null>(null);
  const [rosterTeam, setRosterTeam] = useState<Team | null>(null);
  const lastRevision = useRef(0);
  const syncingRef = useRef(false);

  const applyState = useCallback((state: DraftState) => {
    if (state.revision < lastRevision.current) return;
    lastRevision.current = state.revision;
    setDraftState(state);
    setRound(state.current_round || 1);
    setCategory(state.active_category);
    const allPicks = state.teams.flatMap((team) =>
      team.picks.map((player) => ({ player, team, round: player.round_number, pick_number: player.pick_number })),
    );
    allPicks.sort((a, b) => (a.pick_number ?? 0) - (b.pick_number ?? 0));
    setPicks(allPicks);
    if (state.latest_pick) {
      setLastPick({
        player: state.latest_pick.player,
        team: state.latest_pick.team,
        round: state.latest_pick.round_number,
        pick_number: state.latest_pick.pick_number,
      });
    } else {
      setLastPick(null);
    }
  }, []);

  const syncState = useCallback(async () => {
    if (syncingRef.current) return;
    syncingRef.current = true;
    setConnection((current) => (current === "LIVE" ? "SYNCING" : current));
    try {
      const state = await fetchDraftState(draftId);
      applyState(state);
      setError(null);
      setConnection("LIVE");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not sync draft state.");
      setConnection("OFFLINE");
    } finally {
      syncingRef.current = false;
    }
  }, [applyState, draftId]);

  const applyEvent = useCallback(
    (event: DraftEvent) => {
      if (event.revision <= lastRevision.current) return;
      if (event.revision > lastRevision.current + 1) {
        void syncState();
        return;
      }
      lastRevision.current = event.revision;
      if (event.type === "category.changed") {
        setCategory(event.active_category);
        setDraftState((state) =>
          state
            ? {
                ...state,
                revision: event.revision,
                active_category: event.active_category,
                draft: { ...state.draft, active_category: event.active_category, revision: event.revision },
              }
            : state,
        );
        void syncState();
        return;
      }
      if (event.type === "round.started") {
        setRound(event.round_number);
        setLastPick(null);
        setDraftState((state) =>
          state
            ? {
                ...state,
                revision: event.revision,
                current_round: event.round_number,
                current_turn: event.turn_order.find((turn) => turn.status === "ACTIVE") ?? null,
                turn_order: event.turn_order,
                draft: { ...state.draft, status: "LIVE", current_round: event.round_number, revision: event.revision },
              }
            : state,
        );
        return;
      }
      setPendingActionId(null);
      setConfirming(null);
      const pick = event.pick;
      setPicks((current) =>
        current.some((item) => item.player.id === pick.player.id)
          ? current
          : [...current, { player: pick.player, team: pick.team, round: pick.round_number, pick_number: pick.pick_number }],
      );
      setLastPick({ player: pick.player, team: pick.team, round: pick.round_number, pick_number: pick.pick_number });
      setDraftState((state) => {
        if (!state) return state;
        const turnOrder = state.turn_order.map((turn) => {
          if (turn.id === event.completed_turn_id) {
            return { ...turn, status: "COMPLETED" as const, selected_player_id: pick.player.id as number };
          }
          if (event.next_turn && turn.id === event.next_turn.id) return event.next_turn;
          return turn;
        });
        return {
          ...state,
          revision: event.revision,
          latest_pick: pick,
          current_turn: event.next_turn,
          turn_order: turnOrder,
          available_players: state.available_players.filter((player) => player.id !== pick.player.id),
          draft: {
            ...state.draft,
            revision: event.revision,
            status: event.round_completed ? "ROUND_COMPLETE" : state.draft.status,
          },
          teams: state.teams.map((team) =>
            team.id === pick.team.id && !team.picks.some((player) => player.id === pick.player.id)
              ? { ...team, picks: [...team.picks, { ...pick.player, round_number: pick.round_number, pick_number: pick.pick_number }] }
              : team,
          ),
        };
      });
    },
    [syncState],
  );

  useEffect(() => {
    void syncState();
  }, [syncState]);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let stopped = false;
    let retry = 0;
    let reconnectTimer: number | undefined;

    function connect() {
      if (stopped) return;
      socket = new WebSocket(draftWsUrl(draftId));
      socket.onopen = () => {
        retry = 0;
        setConnection("SYNCING");
        void syncState();
      };
      socket.onmessage = (message) => {
        try {
          applyEvent(JSON.parse(message.data) as DraftEvent);
          setConnection("LIVE");
        } catch {
          void syncState();
        }
      };
      socket.onclose = () => {
        if (stopped) return;
        setConnection("RECONNECTING");
        const delay = Math.min(8000, 1000 * 2 ** retry) + Math.floor(Math.random() * 300);
        retry += 1;
        reconnectTimer = window.setTimeout(connect, delay);
      };
      socket.onerror = () => {
        socket?.close();
      };
    }

    connect();
    return () => {
      stopped = true;
      if (reconnectTimer) window.clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, [applyEvent, draftId, syncState]);

  const order = useMemo(() => draftState?.turn_order.map((turn) => turn.team) ?? [], [draftState]);
  const currentIndex = useMemo(() => {
    const index = draftState?.turn_order.findIndex((turn) => turn.status === "ACTIVE") ?? -1;
    return index >= 0 ? index : order.length;
  }, [draftState, order.length]);
  const takenIds = useMemo(() => new Set(picks.map((p) => p.player.id)), [picks]);
  const available = useMemo(() => draftState?.available_players.filter((p) => !takenIds.has(p.id) && p.category === category) ?? [], [draftState, takenIds, category]);
  const picksByTeam = useMemo(() => {
    const m: Record<string, Array<string | number>> = {};
    for (const p of picks) (m[String(p.team.id)] ??= []).push(p.player.id);
    return m;
  }, [picks]);

  const currentTeam = order[currentIndex];
  const roundComplete = currentIndex >= order.length;

  async function confirm() {
    if (!confirming || !currentTeam) return;
    const actionId = crypto.randomUUID();
    setPendingActionId(actionId);
    setError(null);
    try {
      const result = await selectDraftPlayer(draftId, confirming.id, actionId);
      applyEvent(result.event);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Selection could not be confirmed.");
      setPendingActionId(null);
      void syncState();
    }
  }

  async function startNextRound() {
    setError(null);
    try {
      const event = draftState?.draft.status === "ROUND_COMPLETE" ? await startNextRoundApi(draftId) : await randomizeOrStart(draftId);
      applyEvent(event);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start round.");
      void syncState();
    }
  }

  async function changeCategory(nextCategory: Category) {
    setCategory(nextCategory);
    setError(null);
    try {
      const event = await setDraftCategory(draftId, nextCategory);
      applyEvent(event);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not change category.");
      void syncState();
    }
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
          <span className={connection === "LIVE" ? "text-emerald-400" : connection === "SYNCING" ? "text-accent" : "text-destructive"}>
            {connection}
          </span>
          <span className="opacity-40">|</span>
          <span>Active Category</span>
          {CATEGORIES.map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => changeCategory(c)}
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
              void startNextRound();
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
            onClick={() => void syncState()}
            className="rounded border border-border px-2 py-1 hover:border-destructive/60"
          >
            Sync
          </button>
        </div>
      </header>
      {error && (
        <div className="border-b border-destructive/30 bg-destructive/10 px-6 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

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
                disabled={roundComplete || pendingActionId !== null || connection === "OFFLINE"}
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
              disabled={pendingActionId !== null}
              className="rounded-lg bg-accent px-5 py-2 text-sm font-bold tracking-wide text-accent-foreground transition-transform hover:scale-105"
            >
              {pendingActionId ? "Confirming..." : "Confirm Selection"}
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
