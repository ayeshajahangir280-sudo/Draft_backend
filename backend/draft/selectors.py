from django.db.models import Prefetch

from .models import Draft, DraftPick, DraftRound, DraftStatus, DraftTurn, Player, RoundStatus
from .serializers import DraftSerializer, PickSerializer, PlayerSerializer, TeamSerializer, TurnSerializer


def current_round_qs():
    return DraftRound.objects.prefetch_related(
        Prefetch(
            "turns",
            queryset=DraftTurn.objects.select_related("team", "manager", "selected_player").order_by("position"),
        )
    )


def get_draft_state(draft_id, request=None):
    draft = (
        Draft.objects.prefetch_related(
            Prefetch("draft_teams", queryset=_draft_team_queryset()),
            Prefetch("rounds", queryset=current_round_qs()),
        )
        .get(pk=draft_id)
    )
    round_obj = next((r for r in draft.rounds.all() if r.round_number == draft.current_round), None)
    turns = list(round_obj.turns.all()) if round_obj else []
    current_turn = next((t for t in turns if t.status == "ACTIVE"), None)
    picked_player_ids = set(DraftPick.objects.filter(draft=draft).values_list("player_id", flat=True))
    available_players = Player.objects.filter(is_active=True, category=draft.active_category).exclude(id__in=picked_player_ids)
    latest_pick = (
        DraftPick.objects.filter(draft=draft)
        .select_related("player", "team", "round")
        .order_by("-pick_number")
        .first()
    )
    picks = (
        DraftPick.objects.filter(draft=draft)
        .select_related("player", "team", "round")
        .order_by("pick_number")
    )
    picks_by_team = {}
    for pick in picks:
        picks_by_team.setdefault(str(pick.team_id), []).append(
            {
                "id": pick.player_id,
                "name": pick.player.name,
                "photo": pick.player.photo,
                "category": pick.category,
                "role": pick.player.playing_role,
                "round_number": pick.round.round_number,
                "pick_number": pick.pick_number,
            }
        )
    teams = []
    for entry in draft.draft_teams.all():
        team_data = TeamSerializer(entry.team, context={"request": request}).data
        team_data["manager_id"] = entry.manager_id
        team_data["manager_name"] = entry.manager.username
        team_data["picks"] = picks_by_team.get(str(entry.team_id), [])
        teams.append(team_data)
    return {
        "draft": DraftSerializer(draft).data,
        "revision": draft.revision,
        "active_category": draft.active_category,
        "current_round": round_obj.round_number if round_obj else draft.current_round,
        "current_turn": TurnSerializer(current_turn, context={"request": request}).data if current_turn else None,
        "turn_order": TurnSerializer(turns, many=True, context={"request": request}).data,
        "available_players": PlayerSerializer(available_players, many=True).data,
        "latest_pick": PickSerializer(latest_pick, context={"request": request}).data if latest_pick else None,
        "teams": teams,
    }


def _draft_team_queryset():
    from .models import DraftTeam

    return DraftTeam.objects.select_related("team", "manager").order_by("created_at")
