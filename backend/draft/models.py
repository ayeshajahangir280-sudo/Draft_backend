from django.conf import settings
from django.db import models
from django.db.models import Q


class UserRole(models.TextChoices):
    ADMIN = "ADMIN", "Admin"
    MANAGER = "MANAGER", "Manager"


class DraftStatus(models.TextChoices):
    SETUP = "SETUP", "Setup"
    LIVE = "LIVE", "Live"
    ROUND_COMPLETE = "ROUND_COMPLETE", "Round complete"
    COMPLETED = "COMPLETED", "Completed"


class RoundStatus(models.TextChoices):
    UPCOMING = "UPCOMING", "Upcoming"
    ACTIVE = "ACTIVE", "Active"
    COMPLETED = "COMPLETED", "Completed"


class TurnStatus(models.TextChoices):
    UPCOMING = "UPCOMING", "Upcoming"
    ACTIVE = "ACTIVE", "Active"
    COMPLETED = "COMPLETED", "Completed"


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=16, choices=UserRole.choices, default=UserRole.MANAGER, db_index=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class Team(models.Model):
    name = models.CharField(max_length=120, unique=True)
    short = models.CharField(max_length=12, blank=True)
    logo = models.ImageField(upload_to="team-logos/", blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)
    manager = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="managed_team"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["manager"])]

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=32, unique=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class Player(models.Model):
    name = models.CharField(max_length=120)
    photo = models.URLField(blank=True)
    category = models.CharField(max_length=32, db_index=True)
    category_ref = models.ForeignKey(
        Category, on_delete=models.PROTECT, null=True, blank=True, related_name="players"
    )
    playing_role = models.CharField(max_length=64)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "name"]
        indexes = [
            models.Index(fields=["is_active", "category"]),
            models.Index(fields=["category", "name"]),
        ]

    def __str__(self):
        return self.name


class Draft(models.Model):
    name = models.CharField(max_length=160)
    status = models.CharField(max_length=24, choices=DraftStatus.choices, default=DraftStatus.SETUP, db_index=True)
    active_category = models.CharField(max_length=32, default="A", db_index=True)
    current_round = models.PositiveIntegerField(default=0)
    revision = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["active_category"]),
        ]

    def __str__(self):
        return self.name


class DraftTeam(models.Model):
    draft = models.ForeignKey(Draft, on_delete=models.CASCADE, related_name="draft_teams")
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="draft_entries")
    manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="draft_entries")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["draft", "team"], name="unique_team_per_draft"),
            models.UniqueConstraint(fields=["draft", "manager"], name="unique_manager_per_draft"),
        ]
        indexes = [
            models.Index(fields=["draft", "team"]),
            models.Index(fields=["draft", "manager"]),
        ]

    def __str__(self):
        return f"{self.team} in {self.draft}"


class DraftPlayer(models.Model):
    draft = models.ForeignKey(Draft, on_delete=models.CASCADE, related_name="draft_players")
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="draft_entries")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["draft", "player"], name="unique_player_per_draft_pool")]


class DraftRound(models.Model):
    draft = models.ForeignKey(Draft, on_delete=models.CASCADE, related_name="rounds")
    round_number = models.PositiveIntegerField()
    status = models.CharField(max_length=16, choices=RoundStatus.choices, default=RoundStatus.UPCOMING, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["draft", "round_number"], name="unique_round_number_per_draft")]
        indexes = [
            models.Index(fields=["draft", "status"]),
            models.Index(fields=["draft", "round_number"]),
        ]

    def __str__(self):
        return f"{self.draft} R{self.round_number}"


class DraftTurn(models.Model):
    round = models.ForeignKey(DraftRound, on_delete=models.CASCADE, related_name="turns")
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="draft_turns")
    manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="draft_turns")
    position = models.PositiveIntegerField()
    status = models.CharField(max_length=16, choices=TurnStatus.choices, default=TurnStatus.UPCOMING, db_index=True)
    selected_player = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, blank=True, related_name="turns")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["round", "position"], name="unique_turn_position_per_round"),
            models.UniqueConstraint(
                fields=["round"],
                condition=Q(status=TurnStatus.ACTIVE),
                name="one_active_turn_per_round",
            ),
            models.UniqueConstraint(
                fields=["round", "selected_player"],
                condition=Q(selected_player__isnull=False),
                name="one_selected_player_per_round_turns",
            ),
        ]
        indexes = [
            models.Index(fields=["round", "status"]),
            models.Index(fields=["round", "position"]),
            models.Index(fields=["manager", "status"]),
        ]

    def __str__(self):
        return f"{self.round} #{self.position} {self.team}"


class DraftPick(models.Model):
    draft = models.ForeignKey(Draft, on_delete=models.CASCADE, related_name="picks")
    round = models.ForeignKey(DraftRound, on_delete=models.CASCADE, related_name="picks")
    turn = models.OneToOneField(DraftTurn, on_delete=models.CASCADE, related_name="pick")
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="draft_picks")
    manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="draft_picks")
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="draft_picks")
    category = models.CharField(max_length=32)
    pick_number = models.PositiveIntegerField()
    client_action_id = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["pick_number"]
        constraints = [
            models.UniqueConstraint(fields=["draft", "player"], name="unique_player_pick_per_draft"),
            models.UniqueConstraint(fields=["draft", "pick_number"], name="unique_pick_number_per_draft"),
            models.UniqueConstraint(fields=["draft", "client_action_id"], name="unique_client_action_per_draft"),
        ]
        indexes = [
            models.Index(fields=["draft", "team"]),
            models.Index(fields=["draft", "player"]),
            models.Index(fields=["draft", "client_action_id"]),
            models.Index(fields=["team", "created_at"]),
        ]

    def __str__(self):
        return f"{self.draft} pick {self.pick_number}: {self.player}"
