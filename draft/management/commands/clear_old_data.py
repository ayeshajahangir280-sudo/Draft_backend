from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from draft.models import Category, Draft, Player, Project, Team, UserRole


class Command(BaseCommand):
    help = "Permanently delete all non-admin Phase 1 and legacy draft data."

    @transaction.atomic
    def handle(self, *args, **options):
        # Delete draft records first because some legacy relationships use restrictive FKs.
        Draft.objects.all().delete()
        Player.objects.all().delete()
        Category.objects.all().delete()
        Project.objects.all().delete()
        Team.objects.all().delete()
        User.objects.exclude(is_staff=True).exclude(is_superuser=True).exclude(profile__role=UserRole.ADMIN).delete()
        self.stdout.write(self.style.SUCCESS("Deleted all non-admin users, managers, teams, projects, categories, players, and drafts."))
