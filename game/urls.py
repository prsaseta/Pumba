from django.urls import path, include
from game.views import match_list3, join_match, create_match, feedback

urlpatterns = [
    path('matchmaking/', match_list3, name="matchmaking"),
    path('join/', join_match, name="join_match"),
    path('create/', create_match, name="create_match"),
    path('feedback/', feedback, name="feedback")
]
