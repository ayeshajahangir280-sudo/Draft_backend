from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DraftViewSet, LoginView, LogoutView, me

router = DefaultRouter()
router.register("drafts", DraftViewSet, basename="draft")

urlpatterns = [
    path("auth/login/", LoginView.as_view()),
    path("auth/logout/", LogoutView.as_view()),
    path("auth/me/", me),
    path("", include(router.urls)),
]
