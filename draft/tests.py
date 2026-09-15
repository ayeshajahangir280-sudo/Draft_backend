import uuid

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import Draft, DraftPick, DraftTeam, Player, Team, UserProfile, UserRole
from .services import create_round_with_order


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class DraftApiTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("admin", password="pw", is_staff=True)
        UserProfile.objects.update_or_create(user=self.admin, defaults={"role": UserRole.ADMIN})
        self.managers = []
        self.teams = []
        self.draft = Draft.objects.create(name="Test Draft", active_category="A")
        for i in range(1, 9):
            manager = User.objects.create_user(f"manager{i}", password="pw")
            UserProfile.objects.update_or_create(user=manager, defaults={"role": UserRole.MANAGER})
            team = Team.objects.create(name=f"Team {i}", short=f"T{i}", manager=manager)
            DraftTeam.objects.create(draft=self.draft, team=team, manager=manager)
            self.managers.append(manager)
            self.teams.append(team)
        self.players_a = [
            Player.objects.create(name=f"A Player {i}", category="A", playing_role="Batsman", photo="")
            for i in range(1, 10)
        ]
        self.player_b = Player.objects.create(name="B Player", category="B", playing_role="Bowler", photo="")
        self.client = APIClient()

    def login(self, user):
        self.client.force_authenticate(user=user)

    def start_round(self):
        create_round_with_order(self.draft, round_number=1)
        self.draft.refresh_from_db()

    def active_turn(self):
        return self.draft.rounds.get(round_number=self.draft.current_round).turns.get(status="ACTIVE")

    def test_admin_can_change_category_and_manager_cannot(self):
        self.login(self.admin)
        res = self.client.post(f"/api/drafts/{self.draft.id}/set-category/", {"category": "B"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.draft.refresh_from_db()
        self.assertEqual(self.draft.active_category, "B")

        self.login(self.managers[0])
        res = self.client.post(f"/api/drafts/{self.draft.id}/set-category/", {"category": "A"}, format="json")
        self.assertEqual(res.status_code, 403)

    def test_start_round_creates_stable_order_and_first_active(self):
        self.login(self.admin)
        res = self.client.post(f"/api/drafts/{self.draft.id}/start-round/")
        self.assertEqual(res.status_code, 200)
        self.draft.refresh_from_db()
        turns = list(self.draft.rounds.get(round_number=1).turns.order_by("position"))
        self.assertEqual(len(turns), 8)
        self.assertEqual(len({t.manager_id for t in turns}), 8)
        self.assertEqual(turns[0].status, "ACTIVE")
        self.assertTrue(all(t.status == "UPCOMING" for t in turns[1:]))

    def test_only_active_manager_can_select_and_turn_moves_forward(self):
        self.start_round()
        active = self.active_turn()
        wrong = next(m for m in self.managers if m.id != active.manager_id)
        self.login(wrong)
        res = self.client.post(
            f"/api/drafts/{self.draft.id}/select-player/",
            {"player_id": self.players_a[0].id, "client_action_id": str(uuid.uuid4())},
            format="json",
        )
        self.assertEqual(res.status_code, 403)

        self.login(active.manager)
        res = self.client.post(
            f"/api/drafts/{self.draft.id}/select-player/",
            {"player_id": self.players_a[0].id, "client_action_id": str(uuid.uuid4())},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(DraftPick.objects.count(), 1)
        active.refresh_from_db()
        self.assertEqual(active.status, "COMPLETED")
        self.assertEqual(active.selected_player_id, self.players_a[0].id)
        self.assertTrue(active.round.turns.filter(status="ACTIVE").exists())

    def test_selected_player_unavailable_state_and_roster(self):
        self.start_round()
        active = self.active_turn()
        self.login(active.manager)
        self.client.post(
            f"/api/drafts/{self.draft.id}/select-player/",
            {"player_id": self.players_a[0].id, "client_action_id": str(uuid.uuid4())},
            format="json",
        )
        res = self.client.get(f"/api/drafts/{self.draft.id}/state/")
        self.assertEqual(res.status_code, 200)
        available_ids = {p["id"] for p in res.data["available_players"]}
        self.assertNotIn(self.players_a[0].id, available_ids)
        team = active.team
        roster = self.client.get(f"/api/drafts/{self.draft.id}/teams/{team.id}/picks/")
        self.assertEqual(roster.data["total_picks"], 1)

    def test_wrong_category_rejected(self):
        self.start_round()
        active = self.active_turn()
        self.login(active.manager)
        res = self.client.post(
            f"/api/drafts/{self.draft.id}/select-player/",
            {"player_id": self.player_b.id, "client_action_id": str(uuid.uuid4())},
            format="json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(DraftPick.objects.count(), 0)

    def test_idempotent_duplicate_click_returns_same_pick(self):
        self.start_round()
        active = self.active_turn()
        action_id = str(uuid.uuid4())
        self.login(active.manager)
        payload = {"player_id": self.players_a[0].id, "client_action_id": action_id}
        first = self.client.post(f"/api/drafts/{self.draft.id}/select-player/", payload, format="json")
        second = self.client.post(f"/api/drafts/{self.draft.id}/select-player/", payload, format="json")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.data["idempotent"])
        self.assertEqual(DraftPick.objects.count(), 1)

    def test_manager_cannot_select_twice_during_one_turn(self):
        self.start_round()
        active = self.active_turn()
        self.login(active.manager)
        self.client.post(
            f"/api/drafts/{self.draft.id}/select-player/",
            {"player_id": self.players_a[0].id, "client_action_id": str(uuid.uuid4())},
            format="json",
        )
        res = self.client.post(
            f"/api/drafts/{self.draft.id}/select-player/",
            {"player_id": self.players_a[1].id, "client_action_id": str(uuid.uuid4())},
            format="json",
        )
        self.assertEqual(res.status_code, 403)
        self.assertEqual(DraftPick.objects.count(), 1)

    def test_round_completion_and_next_round_preserves_unavailable_players(self):
        self.start_round()
        for i in range(8):
            self.draft.refresh_from_db()
            active = self.active_turn()
            self.login(active.manager)
            self.client.post(
                f"/api/drafts/{self.draft.id}/select-player/",
                {"player_id": self.players_a[i].id, "client_action_id": str(uuid.uuid4())},
                format="json",
            )
        self.draft.refresh_from_db()
        self.assertEqual(self.draft.status, "ROUND_COMPLETE")

        self.login(self.admin)
        res = self.client.post(f"/api/drafts/{self.draft.id}/next-round/")
        self.assertEqual(res.status_code, 200)
        state = self.client.get(f"/api/drafts/{self.draft.id}/state/").data
        available_ids = {p["id"] for p in state["available_players"]}
        self.assertNotIn(self.players_a[0].id, available_ids)
        self.assertEqual(state["current_round"], 2)

    def test_unauthorized_user_cannot_load_draft_state(self):
        self.client.force_authenticate(user=None)
        res = self.client.get(f"/api/drafts/{self.draft.id}/state/")
        self.assertIn(res.status_code, (401, 403))

    def test_authenticated_user_can_load_draft_state(self):
        self.login(self.managers[0])
        res = self.client.get(f"/api/drafts/{self.draft.id}/state/")
        self.assertEqual(res.status_code, 200)
