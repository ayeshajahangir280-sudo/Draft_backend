import logging
import random
import time

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import Draft, DraftPick, DraftRound, DraftStatus, DraftTeam, DraftTurn, Player, RoundStatus, TurnStatus, UserRole
from .permissions import user_role
from .realtime import broadcast_draft_event
from .serializers import PickSerializer, TurnSerializer

logger = logging.getLogger("draft")


def _increment_revision(draft):
    Draft.objects.filter(pk=draft.pk).update(revision=F("revision") + 1)
    draft.revision += 1
    return draft.revision


def _active_round(draft):
    return DraftRound.objects.select_for_update().get(draft=draft, round_number=draft.current_round, status=RoundStatus.ACTIVE)


def set_category(draft, category):
    with transaction.atomic():
        draft = Draft.objects.select_for_update().get(pk=draft.pk)
        draft.active_category = category
        revision = _increment_revision(draft)
        draft.save(update_fields=["active_category", "updated_at"])
    event = {"type": "category.changed", "revision": revision, "active_category": category}
    broadcast_draft_event(draft.id, event)
    return event


def create_round_with_order(draft, *, round_number=None):
    with transaction.atomic():
        draft = Draft.objects.select_for_update().get(pk=draft.pk)
        if round_number is None:
            round_number = max(draft.current_round + 1, 1)
        teams = list(DraftTeam.objects.select_related("team", "manager").filter(draft=draft))
        if not teams:
            raise ValidationError("Draft has no teams.")
        random.shuffle(teams)
        now = timezone.now()
        DraftRound.objects.filter(draft=draft, status=RoundStatus.ACTIVE).update(status=RoundStatus.COMPLETED, completed_at=now)
        round_obj = DraftRound.objects.create(draft=draft, round_number=round_number, status=RoundStatus.ACTIVE, started_at=now)
        turns = [
            DraftTurn(
                round=round_obj,
                team=entry.team,
                manager=entry.manager,
                position=i,
                status=TurnStatus.ACTIVE if i == 1 else TurnStatus.UPCOMING,
                started_at=now if i == 1 else None,
            )
            for i, entry in enumerate(teams, start=1)
        ]
        DraftTurn.objects.bulk_create(turns)
        draft.current_round = round_number
        draft.status = DraftStatus.LIVE
        revision = _increment_revision(draft)
        draft.save(update_fields=["current_round", "status", "updated_at"])
    payload = {
        "type": "round.started",
        "revision": revision,
        "round_number": round_number,
        "turn_order": TurnSerializer(DraftTurn.objects.filter(round=round_obj).select_related("team", "manager").order_by("position"), many=True).data,
    }
    broadcast_draft_event(draft.id, payload)
    return payload


def select_player(draft_id, manager, player_id, client_action_id):
    started = time.perf_counter()
    pick = None
    next_turn = None
    round_completed = False
    try:
        with transaction.atomic():
            draft = Draft.objects.select_for_update().get(pk=draft_id)
            existing = (
                DraftPick.objects.filter(draft=draft, client_action_id=client_action_id)
                .select_related("player", "team", "round")
                .first()
            )
            if existing:
                return _selection_response(draft, existing, idempotent=True)
            if draft.status != DraftStatus.LIVE:
                raise ValidationError("Draft is not live.")
            if user_role(manager) != UserRole.MANAGER:
                raise PermissionDenied("Only managers can select players.")
            if not DraftTeam.objects.filter(draft=draft, manager=manager).exists():
                raise PermissionDenied("Manager is not participating in this draft.")
            round_obj = _active_round(draft)
            turn = (
                DraftTurn.objects.select_for_update()
                .select_related("team", "manager")
                .get(round=round_obj, status=TurnStatus.ACTIVE)
            )
            if turn.manager_id != manager.id:
                raise PermissionDenied("It is not this manager's turn.")
            if turn.selected_player_id:
                raise ValidationError("This turn already has a selected player.")
            player = Player.objects.select_for_update().get(pk=player_id, is_active=True)
            if player.category != draft.active_category:
                raise ValidationError("Player is not in the active category.")
            if DraftPick.objects.filter(draft=draft, player=player).exists():
                raise ValidationError("Player has already been selected.")
            pick_number = DraftPick.objects.filter(draft=draft).count() + 1
            pick = DraftPick.objects.create(
                draft=draft,
                round=round_obj,
                turn=turn,
                team=turn.team,
                manager=manager,
                player=player,
                category=player.category,
                pick_number=pick_number,
                client_action_id=client_action_id,
            )
            now = timezone.now()
            turn.status = TurnStatus.COMPLETED
            turn.selected_player = player
            turn.completed_at = now
            turn.save(update_fields=["status", "selected_player", "completed_at"])
            next_turn = (
                DraftTurn.objects.select_for_update()
                .filter(round=round_obj, status=TurnStatus.UPCOMING, position__gt=turn.position)
                .order_by("position")
                .first()
            )
            if next_turn:
                next_turn.status = TurnStatus.ACTIVE
                next_turn.started_at = now
                next_turn.save(update_fields=["status", "started_at"])
            else:
                round_obj.status = RoundStatus.COMPLETED
                round_obj.completed_at = now
                round_obj.save(update_fields=["status", "completed_at"])
                draft.status = DraftStatus.ROUND_COMPLETE
                round_completed = True
            revision = _increment_revision(draft)
            draft.save(update_fields=["status", "updated_at"])
    except IntegrityError:
        pick = DraftPick.objects.filter(draft_id=draft_id, client_action_id=client_action_id).select_related("player", "team", "round").first()
        if pick:
            draft = Draft.objects.get(pk=draft_id)
            return _selection_response(draft, pick, idempotent=True)
        raise ValidationError("Selection conflicted with another request. Refresh draft state.")

    response = _selection_response(draft, pick, next_turn=next_turn, round_completed=round_completed)
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    logger.info(
        "player_selection draft_id=%s round_id=%s turn_id=%s manager_id=%s player_id=%s client_action_id=%s revision=%s duration_ms=%s success=true",
        draft_id,
        pick.round_id,
        pick.turn_id,
        manager.id,
        player_id,
        client_action_id,
        draft.revision,
        duration_ms,
    )
    transaction.on_commit(lambda: broadcast_draft_event(draft_id, response["event"]))
    return response


def _selection_response(draft, pick, *, next_turn=None, round_completed=False, idempotent=False):
    latest_pick = DraftPick.objects.select_related("player", "team", "round").get(pk=pick.pk)
    if next_turn is None and not round_completed:
        next_turn = (
            DraftTurn.objects.filter(round=pick.round, status=TurnStatus.ACTIVE)
            .select_related("team", "manager")
            .first()
        )
    event = {
        "type": "player.selected",
        "revision": draft.revision,
        "pick": PickSerializer(latest_pick).data,
        "completed_turn_id": pick.turn_id,
        "next_turn": TurnSerializer(next_turn).data if next_turn else None,
        "round_completed": round_completed,
    }
    if round_completed:
        event["type"] = "round.completed"
    return {"idempotent": idempotent, "event": event, "pick": event["pick"]}
