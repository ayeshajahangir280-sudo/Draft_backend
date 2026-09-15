from channels.generic.websocket import AsyncJsonWebsocketConsumer


class DraftConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.draft_id = self.scope["url_route"]["kwargs"]["draft_id"]
        self.group_name = f"draft_{self.draft_id}"
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        if content.get("type") == "ping":
            await self.send_json({"type": "pong"})

    async def draft_event(self, event):
        await self.send_json(event["event"])
