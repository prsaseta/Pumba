# chat/routing.py
from django.conf.urls import url

from . import consumers

websocket_urlpatterns = [
    # El primer argumento, independientemente de como se llame, el consumer lo recibe como "match_id"
    url(r'^ws/game/(?P<match_id>[^/]+)/$', consumers.GameConsumer),
]