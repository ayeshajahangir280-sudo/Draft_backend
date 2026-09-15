from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Category, Draft, DraftPick, DraftRound, DraftTeam, DraftTurn, Player, Project, Team, UserRole


def absolute_media_url(request, value):
    if not value:
        return ""
    url = value.url if hasattr(value, "url") else str(value)
    return request.build_absolute_uri(url) if request else url


class UserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source="profile.role", read_only=True)
    team_id = serializers.IntegerField(source="managed_team.id", read_only=True, default=None)
    active = serializers.BooleanField(source="is_active", read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "role", "team_id", "active"]

class AdminUserSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(choices=UserRole.choices, write_only=True, default=UserRole.MANAGER)
    password = serializers.CharField(write_only=True, required=False)
    role_name = serializers.CharField(source="profile.role", read_only=True)
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "password", "role", "role_name", "is_active"]
    def create(self, validated_data):
        role = validated_data.pop("role", UserRole.MANAGER)
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        user.set_password(password or User.objects.make_random_password())
        user.save()
        from .models import UserProfile
        UserProfile.objects.update_or_create(user=user, defaults={"role": role})
        return user

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["id", "name", "description", "is_active", "created_at"]


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
    logo_file = serializers.ImageField(source="logo", write_only=True, required=False)

    class Meta:
        model = Team
        fields = ["id", "name", "short", "logo", "logo_file", "manager_id", "manager_name", "is_active"]

    def get_logo(self, obj):
        return absolute_media_url(self.context.get("request"), obj.logo)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "sort_order", "is_active"]


class PlayerSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source="playing_role")

    class Meta:
        model = Player
        fields = ["id", "project", "name", "photo", "category", "category_ref", "role", "is_active"]
    category_ref = serializers.PrimaryKeyRelatedField(read_only=True)


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
