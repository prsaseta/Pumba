from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
import json
from django.core.cache import cache 

class GameConsumer(WebsocketConsumer):
    def connect(self):
        # Si ocurre algo, rechazamos la conexión
        error = False
        # TODO ¿Hacer algo si se conecta desde dos pestañas?
        # TODO Obtener Player asociado y orden en la lista de Players
        # TODO Comprobar que la ID de la partida existe y etc

        # Cogemos el usuario autenticado
        user = None
        try:
            user = self.scope["user"]
            if user is None:
                error = True
        except:
            error = True

        # Intentamos obtener la partida
        self.match_id = self.scope['url_route']['kwargs']['match_id']
        self.match_group_name = 'match_%s' % self.match_id
        game = None
        try:
            game = cache.get(self.match_group_name)
            if game is None:
                error = True
        except:
            error = True

        # Nos aseguramos de que el usuario se supone que debe estar en la partida
        # Buscamos en la lista de jugadores y guardamos su índice
        index = None
        for i in range(len(game.players)):
            player = game.players[i]
            if player.controller.user == user:
                index = i
                break
        if index is None:
            error = True
        self.player_index = index

        if not error:
            # Se une al grupo de canales de la partida
            async_to_sync(self.channel_layer.group_add)(
                self.match_group_name,
                self.channel_name
            )
            # Enviamos notificación por chat
            async_to_sync(self.channel_layer.group_send)(
            self.match_group_name,
            {
                'type': 'chat_notification',
                'message': "User " + game.players[self.player_index].name + " joined the game"
            }
        )
            self.accept()

    def disconnect(self, close_code):
        # TODO Darle control a la IA
        game = cache.get(self.match_group_name)
        username = game.players[self.player_index].name
        # Avisamos al resto de jugadores
        async_to_sync(self.channel_layer.group_send)(
            self.match_group_name,
            {
                'type': 'chat_notification',
                'message': "User " + username + " disconnected from the game"
            }
        )
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            self.match_group_name,
            self.channel_name
        )

    # Recibe mensajes del websocket
    def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        game = cache.get(self.match_group_name)
        username = game.players[self.player_index].name

        # Reenvía mensaje de chat a todos los canales, incluyéndose a sí mismo
        # El "type" indica qué método ejecutar de los consumidores que reciban el mensaje
        # Cuidado: el type no significa lo mismo mandándoselo al grupo que mandándoselo al cliente
        # En el grupo dice método a ejecutar, en cliente indica tipo de mensaje
        async_to_sync(self.channel_layer.group_send)(
            self.match_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'username': username
            }
        )

    # Receive message from room group
    def chat_message(self, event):
        message = event['message']
        username = event['username']

        # Send message to WebSocket
        self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': message,
            'username': username
        }))

    # Envía una notificación de chat
    def chat_notification(self, event):
        # Recupera el mensaje
        message = event['message']

        # Envía el mensaje al websocket en cliente
        self.send(text_data=json.dumps({
            'type': 'chat_notification',
            'message': message
        }))