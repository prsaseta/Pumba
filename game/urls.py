from django.urls import path, include
from game.views import match_list
urlpatterns = [
    path('matchmaking/', match_list, name="matchmaking")
]
