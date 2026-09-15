import type { Player, Team } from "@/data/draft";

export type DraftTurn = {
  id: number;
  position: number;
  status: "UPCOMING" | "ACTIVE" | "COMPLETED";
  team: Team;
  manager_id: number;
  manager_name: string;
  selected_player_id?: number | null;
};

export type DraftPick = {
  id: number;
  player: Player;
  team: Team;
  round_number: number;
  pick_number: number;
  category: string;
  client_action_id?: string;
};

export type DraftState = {
  draft: {
    id: number;
    name: string;
    status: "SETUP" | "LIVE" | "ROUND_COMPLETE" | "COMPLETED";
    active_category: string;
    current_round: number;
    revision: number;
  };
  revision: number;
  active_category: string;
  current_round: number;
  current_turn: DraftTurn | null;
  turn_order: DraftTurn[];
  available_players: Player[];
  latest_pick: DraftPick | null;
  teams: Array<Team & { manager_id: number; manager_name: string; picks: Array<Player & { round_number: number; pick_number: number }> }>;
};

export type DraftEvent =
  | { type: "category.changed"; revision: number; active_category: string }
  | { type: "round.started"; revision: number; round_number: number; turn_order: DraftTurn[] }
  | {
      type: "player.selected" | "round.completed";
      revision: number;
      pick: DraftPick;
      completed_turn_id: number;
      next_turn: DraftTurn | null;
      round_completed: boolean;
    };

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
export const DEFAULT_DRAFT_ID = Number(import.meta.env.VITE_DRAFT_ID ?? "1");

class TimeoutError extends Error {
  constructor() {
    super("Request timed out. Syncing authoritative draft state.");
    this.name = "TimeoutError";
  }
}

async function request<T>(path: string, options: RequestInit = {}, timeoutMs = 8000): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...(options.headers ?? {}),
      },
      signal: controller.signal,
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail ?? JSON.stringify(body) ?? response.statusText);
    }
    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw new TimeoutError();
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
}

export function fetchDraftState(draftId = DEFAULT_DRAFT_ID) {
  return request<DraftState>(`/api/drafts/${draftId}/state/`, {}, 10000);
}

export function setDraftCategory(draftId: number, category: string) {
  return request<DraftEvent>(`/api/drafts/${draftId}/set-category/`, {
    method: "POST",
    body: JSON.stringify({ category }),
  });
}

export function startNextRound(draftId: number) {
  return request<DraftEvent>(`/api/drafts/${draftId}/next-round/`, { method: "POST" });
}

export function randomizeOrStart(draftId: number) {
  return request<DraftEvent>(`/api/drafts/${draftId}/start-round/`, { method: "POST" });
}

export function selectDraftPlayer(draftId: number, playerId: string | number, clientActionId: string) {
  return request<{ idempotent: boolean; event: DraftEvent; pick: DraftPick }>(
    `/api/drafts/${draftId}/select-player/`,
    {
      method: "POST",
      body: JSON.stringify({ player_id: Number(playerId), client_action_id: clientActionId }),
    },
    6000,
  );
}

export function draftWsUrl(draftId: number) {
  const base = new URL(API_BASE);
  base.protocol = base.protocol === "https:" ? "wss:" : "ws:";
  base.pathname = `/ws/drafts/${draftId}/`;
  base.search = "";
  return base.toString();
}
