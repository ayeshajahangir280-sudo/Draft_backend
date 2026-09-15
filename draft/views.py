from django.contrib.auth.models import User
import csv
import io
from openpyxl import load_workbook
from django.db import transaction
from django.db.models import Count
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Category, Draft, DraftPick, DraftPlayer, DraftTeam, Player, Team, UserProfile, UserRole
from .permissions import IsAdminRole
from .selectors import get_draft_state
from .serializers import (
    DraftSerializer,
    LoginSerializer,
    PlayerSerializer,
    SelectPlayerSerializer,
    SetCategorySerializer,
    TeamSerializer,
    CategorySerializer,
    UserSerializer,
    logout_user,
)
from .services import create_round_with_order, select_player, set_category


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data)


class LogoutView(APIView):
    def post(self, request):
        logout_user(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(UserSerializer(request.user).data)


class DraftViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Draft.objects.all().order_by("-created_at")
    serializer_class = DraftSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["get"])
    def state(self, request, pk=None):
        return Response(get_draft_state(pk, request=request))

    @action(detail=True, methods=["get"], url_path="available-players")
    def available_players(self, request, pk=None):
        state = get_draft_state(pk, request=request)
        return Response({"revision": state["revision"], "players": state["available_players"]})

    @action(detail=True, methods=["post"], url_path="set-category", permission_classes=[IsAuthenticated, IsAdminRole])
    def set_category_action(self, request, pk=None):
        draft = self.get_object()
        serializer = SetCategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(set_category(draft, serializer.validated_data["category"]))

    @action(detail=True, methods=["post"], url_path="randomize-order", permission_classes=[IsAuthenticated, IsAdminRole])
    def randomize_order(self, request, pk=None):
        draft = self.get_object()
        next_round_number = max(draft.current_round, 1)
        if draft.current_round:
            return Response({"detail": "Use next-round after a round has started."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(create_round_with_order(draft, round_number=next_round_number))

    @action(detail=True, methods=["post"], url_path="start-round", permission_classes=[IsAuthenticated, IsAdminRole])
    def start_round(self, request, pk=None):
        draft = self.get_object()
        if draft.current_round:
            return Response({"detail": "Round already started."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(create_round_with_order(draft, round_number=1))

    @action(detail=True, methods=["post"], url_path="next-round", permission_classes=[IsAuthenticated, IsAdminRole])
    def next_round(self, request, pk=None):
        draft = self.get_object()
        if draft.status != "ROUND_COMPLETE":
            return Response({"detail": "Current round is not complete."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(create_round_with_order(draft, round_number=draft.current_round + 1))

    @action(detail=True, methods=["post"], url_path="select-player")
    def select_player_action(self, request, pk=None):
        serializer = SelectPlayerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = select_player(
            int(pk),
            request.user,
            serializer.validated_data["player_id"],
            serializer.validated_data["client_action_id"],
        )
        return Response(result)

    @action(detail=True, methods=["get"], url_path="teams")
    def teams(self, request, pk=None):
        teams = Team.objects.filter(draft_entries__draft_id=pk).select_related("manager").order_by("draft_entries__created_at")
        return Response(TeamSerializer(teams, many=True, context={"request": request}).data)

    @action(detail=True, methods=["get"], url_path=r"teams/(?P<team_id>\d+)/picks")
    def team_picks(self, request, pk=None, team_id=None):
        entry = DraftTeam.objects.select_related("team", "manager").get(draft_id=pk, team_id=team_id)
        picks = (
            DraftPick.objects.filter(draft_id=pk, team_id=team_id)
            .select_related("player", "round")
            .order_by("pick_number")
        )
        players = [
            {
                "id": pick.player_id,
                "name": pick.player.name,
                "photo": pick.player.photo,
                "category": pick.category,
                "role": pick.player.playing_role,
                "round_number": pick.round.round_number,
                "pick_number": pick.pick_number,
            }
            for pick in picks
        ]
        return Response(
            {
                "team": TeamSerializer(entry.team, context={"request": request}).data,
                "manager": UserSerializer(entry.manager).data,
                "total_picks": len(players),
                "players": players,
            }
        )

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated, IsAdminRole])
    def create_draft(self, request):
        name = str(request.data.get("name", "")).strip()
        team_ids = request.data.get("team_ids", [])
        player_ids = request.data.get("player_ids", [])
        if not name or len(team_ids) < 2 or not player_ids:
            return Response({"detail": "Draft name, at least two teams, and players are required."}, status=400)
        teams = list(Team.objects.filter(id__in=team_ids, is_active=True).select_related("manager"))
        if len(teams) != len(set(team_ids)) or any(not team.manager or not team.manager.is_active for team in teams):
            return Response({"detail": "Every participating team must have an active manager."}, status=400)
        players = list(Player.objects.filter(id__in=player_ids, is_active=True, category_ref__isnull=False))
        if len(players) != len(set(player_ids)):
            return Response({"detail": "All selected players must be active and have valid categories."}, status=400)
        draft = Draft.objects.create(name=name, active_category=players[0].category)
        DraftTeam.objects.bulk_create([DraftTeam(draft=draft, team=t, manager=t.manager) for t in teams])
        DraftPlayer.objects.bulk_create([DraftPlayer(draft=draft, player=p) for p in players])
        result = DraftSerializer(draft).data
        result["setup_summary"] = {
            "teams": len(teams),
            "managers": len({team.manager_id for team in teams}),
            "players": len(players),
            "categories": len({player.category_ref_id for player in players}),
        }
        return Response(result, status=201)

    @action(detail=True, methods=["post"], url_path="start-draft", permission_classes=[IsAuthenticated, IsAdminRole])
    def start_draft(self, request, pk=None):
        draft = self.get_object()
        teams = list(draft.draft_teams.select_related("manager"))
        players = draft.draft_players.filter(
            player__is_active=True, player__category_ref__is_active=True
        ).select_related("player", "player__category_ref")
        errors = []
        if len(teams) < 2:
            errors.append("At least two participating teams are required.")
        if any(not entry.manager or not entry.manager.is_active for entry in teams):
            errors.append("Every participating team must have an active manager.")
        if not players.exists():
            errors.append("At least one active player with a valid category is required.")
        if errors:
            return Response({"detail": "Draft cannot start.", "errors": errors}, status=400)
        draft.status = "LIVE"
        draft.save(update_fields=["status", "updated_at"])
        return Response(DraftSerializer(draft).data)


class AdminCategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(is_active=True) if self.request.query_params.get("active") == "true" else queryset

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active"])


class AdminTeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.select_related("manager").order_by("-created_at", "-id")
    serializer_class = TeamSerializer
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(is_active=True) if self.request.query_params.get("active") == "true" else queryset

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])


class AdminPlayerViewSet(viewsets.ModelViewSet):
    queryset = Player.objects.all()
    serializer_class = PlayerSerializer
    permission_classes = [IsAuthenticated, IsAdminRole]

    def perform_create(self, serializer):
        category_name = self.request.data.get("category", "").strip()
        category = Category.objects.filter(name=category_name, is_active=True).first()
        if not category:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"category": "Choose an existing active category."})
        serializer.save(category_ref=category)

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get("search", "").strip()
        category = self.request.query_params.get("category", "").strip()
        if search:
            queryset = queryset.filter(name__icontains=search)
        if category:
            queryset = queryset.filter(category=category)
        return queryset

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])

    @action(detail=False, methods=["post"], url_path="import")
    def import_players(self, request):
        upload = request.FILES.get("file")
        if not upload:
            return Response({"detail": "file is required"}, status=400)
        rows = []
        if upload.name.lower().endswith(".xlsx"):
            sheet = load_workbook(upload, read_only=True, data_only=True).active
            values = list(sheet.values)
            headers, values = values[0], values[1:]
            rows = [dict(zip(headers, row)) for row in values]
        else:
            rows = list(csv.DictReader(io.TextIOWrapper(upload.file, encoding="utf-8-sig")))
        existing = set(Player.objects.values_list("name", flat=True))
        imported, skipped, errors, pending = 0, 0, [], []
        for line, row in enumerate(rows, 2):
            name = str(row.get("Player Name") or row.get("name") or "").strip()
            category = str(row.get("Category") or row.get("category") or "").strip()
            role = str(row.get("Playing Role") or row.get("role") or "").strip()
            if not name or not category or not role:
                errors.append({"row": line, "error": "Player Name, Category and Playing Role are required"}); continue
            if not Category.objects.filter(name=category, is_active=True).exists():
                errors.append({"row": line, "error": f"Unknown or inactive category: {category}"}); continue
            if name in existing:
                skipped += 1; continue
            category_obj = Category.objects.get(name=category)
            pending.append(Player(name=name, category=category, category_ref=category_obj, playing_role=role, photo=str(row.get("Photo URL") or row.get("photo") or "")))
            existing.add(name)
        if errors:
            return Response({"imported": 0, "skipped": skipped, "errors": errors})
        Player.objects.bulk_create(pending)
        imported = len(pending)
        return Response({"imported": imported, "skipped": skipped, "errors": errors})


class AdminManagerViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def list(self, request):
        users = User.objects.filter(profile__role=UserRole.MANAGER).select_related("profile", "managed_team")
        return Response(UserSerializer(users, many=True).data)

    def create(self, request):
        data = request.data
        username = data.get("username") or data.get("email")
        if not username or not data.get("password") or not data.get("name"):
            return Response({"detail": "name, username/email and password are required"}, status=400)
        if User.objects.filter(username=username).exists():
            return Response({"detail": "Username already exists"}, status=400)
        user = User.objects.create_user(username=username, password=data["password"], first_name=data["name"])
        UserProfile.objects.create(user=user, role=UserRole.MANAGER)
        team = Team.objects.filter(id=data.get("team_id")).first()
        if team:
            team.manager = user
            team.save(update_fields=["manager", "updated_at"])
        return Response(UserSerializer(user).data, status=201)

    def partial_update(self, request, pk=None):
        user = User.objects.get(pk=pk)
        if request.data.get("password"):
            user.set_password(request.data["password"])
        if "active" in request.data:
            user.is_active = bool(request.data["active"])
        user.save()
        if "team_id" in request.data:
            Team.objects.filter(manager=user).update(manager=None)
            Team.objects.filter(id=request.data["team_id"]).update(manager=user)
        return Response(UserSerializer(user).data)
