import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import Community, CommunityChatRoom, ChatMessage


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.community_slug = self.scope['url_route']['kwargs']['community_slug']
        self.room_group_name = f'chat_{self.community_slug}'

        # Проверяем, существует ли сообщество
        community_exists = await self.check_community_exists()
        if not community_exists:
            await self.close()
            return

        # Добавляем в группу
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data['message']
        username = self.scope['user'].username

        # Сохраняем сообщение в БД
        room = await self.get_or_create_room()
        user = await self.get_user(username)
        await self.save_message(room, user, message)

        # Отправляем сообщение в группу
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'username': username,
                'timestamp': data.get('timestamp', ''),
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'username': event['username'],
            'timestamp': event['timestamp'],
        }))

    @database_sync_to_async
    def check_community_exists(self):
        return Community.objects.filter(slug=self.community_slug, is_active=True, has_chat=True).exists()

    @database_sync_to_async
    def get_user(self, username):
        return User.objects.get(username=username)

    @database_sync_to_async
    def get_or_create_room(self):
        community = Community.objects.get(slug=self.community_slug)
        room, _ = CommunityChatRoom.objects.get_or_create(community=community)
        return room

    @database_sync_to_async
    def save_message(self, room, user, message):
        ChatMessage.objects.create(room=room, user=user, message=message)