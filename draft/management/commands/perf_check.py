import json
import uuid
from time import perf_counter

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import connection
from django.test.client import RequestFactory
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from draft.models import Draft, Player
from draft.selectors import get_draft_state


class Command(BaseCommand):
    help = "Measure local draft API payload, query count, and selection latency."

    def handle(self, *args, **options):
        draft = Draft.objects.order_by("id").first()
        if not draft:
            self.stderr.write("No draft found. Run python manage.py seed_demo first.")
            return
        if draft.current_round == 0:
            client = APIClient()
            admin = User.objects.filter(is_staff=True).first()
            client.force_authenticate(admin)
            client.post(f"/api/drafts/{draft.id}/start-round/")
            draft.refresh_from_db()

        request = RequestFactory().get("/")
        request.user = draft.draft_teams.first().manager
        with CaptureQueriesContext(connection) as state_queries:
            start = perf_counter()
            state = get_draft_state(draft.id, request=request)
            state_ms = (perf_counter() - start) * 1000
        state_bytes = len(json.dumps(state, default=str).encode("utf-8"))

        active_turn = draft.rounds.get(round_number=draft.current_round).turns.get(status="ACTIVE")
        player = Player.objects.filter(is_active=True, category=draft.active_category).exclude(draft_picks__draft=draft).first()
        client = APIClient()
        client.force_authenticate(active_turn.manager)
        with CaptureQueriesContext(connection) as selection_queries:
            start = perf_counter()
            response = client.post(
                f"/api/drafts/{draft.id}/select-player/",
                {"player_id": player.id, "client_action_id": str(uuid.uuid4())},
                format="json",
            )
            selection_ms = (perf_counter() - start) * 1000
        response_json = response.json()
        event_bytes = len(json.dumps(response_json["event"], default=str).encode("utf-8"))

        self.stdout.write(json.dumps({
            "draft_id": draft.id,
            "state_ms": round(state_ms, 2),
            "state_queries": len(state_queries),
            "state_payload_bytes": state_bytes,
            "selection_status": response.status_code,
            "selection_ms": round(selection_ms, 2),
            "selection_queries": len(selection_queries),
            "event_payload_bytes": event_bytes,
            "revision": response_json["event"]["revision"],
        }, indent=2))
