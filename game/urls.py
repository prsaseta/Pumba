from django.urls import path, include
from game.views import match_list3, join_match, create_match, feedback, profile, profile_picture_upload, profile_picture_delete

urlpatterns = [
    path('matchmaking/', match_list3, name="matchmaking"),
    path('join/', join_match, name="join_match"),
    path('create/', create_match, name="create_match"),
    path('feedback/', feedback, name="feedback"),
    path('profile/', profile, name="profile"),
    path('upload_profile_picture/', profile_picture_upload, name="upload_profile_picture"),
    path('delete_profile_picture/', profile_picture_delete, name="delete_profile_picture")
]
