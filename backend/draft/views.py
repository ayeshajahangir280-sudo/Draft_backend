from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Draft, DraftPick, DraftTeam, Player, Team
from .permissions import IsAdminRole
from .selectors import get_draft_state
from .serializers import (
    DraftSerializer,
    LoginSerializer,
    PlayerSerializer,
    SelectPlayerSerializer,
    SetCategorySerializer,
    TeamSerializer,
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

    @action(detail=True, methods=["get"], permission_classes=[AllowAny])
    def state(self, request, pk=None):
        return Response(get_draft_state(pk, request=request))

    @action(detail=True, methods=["get"], url_path="available-players", permission_classes=[AllowAny])
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
