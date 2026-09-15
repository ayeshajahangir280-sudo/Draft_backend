from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def broadcast_draft_event(draft_id, event):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    async_to_sync(channel_layer.group_send)(
        f"draft_{draft_id}",
        {"type": "draft.event", "event": event},
    )
