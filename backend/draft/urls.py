from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminCategoryViewSet, AdminManagerViewSet, AdminPlayerViewSet, AdminTeamViewSet,
    DraftViewSet, LoginView, LogoutView, me,
)

router = DefaultRouter()
router.register("drafts", DraftViewSet, basename="draft")
router.register("admin/categories", AdminCategoryViewSet, basename="admin-category")
router.register("admin/teams", AdminTeamViewSet, basename="admin-team")
router.register("admin/players", AdminPlayerViewSet, basename="admin-player")
router.register("admin/managers", AdminManagerViewSet, basename="admin-manager")

urlpatterns = [
    path("auth/login/", LoginView.as_view()),
    path("auth/logout/", LogoutView.as_view()),
    path("auth/me/", me),
    path("", include(router.urls)),
]
