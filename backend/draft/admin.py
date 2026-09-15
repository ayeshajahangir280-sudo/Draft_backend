from django.contrib import admin

from .models import Draft, DraftPick, DraftRound, DraftTeam, DraftTurn, Player, Team, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role")
    list_filter = ("role",)
    search_fields = ("user__username", "user__email")


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "short", "manager", "created_at")
    search_fields = ("name", "short", "manager__username")
    list_select_related = ("manager",)


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "playing_role", "is_active")
    list_filter = ("category", "playing_role", "is_active")
    search_fields = ("name",)


class DraftTeamInline(admin.TabularInline):
    model = DraftTeam
    extra = 0
    autocomplete_fields = ("team", "manager")


@admin.register(Draft)
class DraftAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "active_category", "current_round", "revision", "updated_at")
    list_filter = ("status", "active_category")
    search_fields = ("name",)
    inlines = [DraftTeamInline]


@admin.register(DraftTeam)
class DraftTeamAdmin(admin.ModelAdmin):
    list_display = ("draft", "team", "manager", "created_at")
    list_filter = ("draft",)
    search_fields = ("draft__name", "team__name", "manager__username")
    list_select_related = ("draft", "team", "manager")


@admin.register(DraftRound)
class DraftRoundAdmin(admin.ModelAdmin):
    list_display = ("draft", "round_number", "status", "started_at", "completed_at")
    list_filter = ("status", "draft")
    search_fields = ("draft__name",)
    list_select_related = ("draft",)


@admin.register(DraftTurn)
class DraftTurnAdmin(admin.ModelAdmin):
    list_display = ("round", "position", "team", "manager", "status", "selected_player")
    list_filter = ("status", "round__draft")
    search_fields = ("team__name", "manager__username", "selected_player__name")
    list_select_related = ("round", "team", "manager", "selected_player")


@admin.register(DraftPick)
class DraftPickAdmin(admin.ModelAdmin):
    list_display = ("draft", "pick_number", "round", "team", "manager", "player", "category", "client_action_id")
    list_filter = ("draft", "category")
    search_fields = ("player__name", "team__name", "manager__username", "client_action_id")
    list_select_related = ("draft", "round", "turn", "team", "manager", "player")
