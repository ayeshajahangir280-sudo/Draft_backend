from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Draft, DraftPick, DraftRound, DraftTeam, DraftTurn, Player, Team, UserRole


def absolute_media_url(request, value):
    if not value:
        return ""
    url = value.url if hasattr(value, "url") else str(value)
    return request.build_absolute_uri(url) if request else url


class UserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source="profile.role", read_only=True)
    team_id = serializers.IntegerField(source="managed_team.id", read_only=True, default=None)

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "role", "team_id"]


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        request = self.context["request"]
        user = authenticate(request, username=attrs["username"], password=attrs["password"])
        if not user:
            raise serializers.ValidationError("Invalid username or password.")
        attrs["user"] = user
        return attrs

    def save(self):
        login(self.context["request"], self.validated_data["user"])
        return self.validated_data["user"]


class TeamSerializer(serializers.ModelSerializer):
    manager_id = serializers.IntegerField(source="manager.id", read_only=True)
    manager_name = serializers.CharField(source="manager.username", read_only=True, default="")
    logo = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ["id", "name", "short", "logo", "manager_id", "manager_name"]

    def get_logo(self, obj):
        return absolute_media_url(self.context.get("request"), obj.logo)


class PlayerSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source="playing_role")

    class Meta:
        model = Player
        fields = ["id", "name", "photo", "category", "role"]


class DraftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Draft
        fields = ["id", "name", "status", "active_category", "current_round", "revision"]


class TurnSerializer(serializers.ModelSerializer):
    team = TeamSerializer(read_only=True)
    manager_id = serializers.IntegerField(source="manager.id", read_only=True)
    manager_name = serializers.CharField(source="manager.username", read_only=True)
    selected_player_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = DraftTurn
        fields = ["id", "position", "status", "team", "manager_id", "manager_name", "selected_player_id"]


class PickSerializer(serializers.ModelSerializer):
    player = PlayerSerializer(read_only=True)
    team = TeamSerializer(read_only=True)
    round_number = serializers.IntegerField(source="round.round_number", read_only=True)

    class Meta:
        model = DraftPick
        fields = ["id", "player", "team", "round_number", "pick_number", "category", "created_at", "client_action_id"]


class SetCategorySerializer(serializers.Serializer):
    category = serializers.CharField(max_length=32)


class SelectPlayerSerializer(serializers.Serializer):
    player_id = serializers.IntegerField()
    client_action_id = serializers.UUIDField()


class TeamPicksSerializer(serializers.Serializer):
    team = TeamSerializer()
    manager = UserSerializer()
    total_picks = serializers.IntegerField()
    players = serializers.ListField()


def logout_user(request):
    logout(request)
