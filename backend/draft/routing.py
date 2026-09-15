from django.urls import re_path

from .consumers import DraftConsumer

websocket_urlpatterns = [
    re_path(r"ws/drafts/(?P<draft_id>\d+)/$", DraftConsumer.as_asgi()),
]
