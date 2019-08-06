from django.db import models
from django.contrib.auth.models import User
from cloudinary.models import CloudinaryField
from django.core.exceptions import ObjectDoesNotExist
import json
from django.utils.translation import gettext_lazy as _

# Create your models here.

# Representa una partida en memoria
class GameKey(models.Model):
    STATUSES = (
        ("WAITING", _("WAITING")),
        ("PLAYING", _("PLAYING")),
        ("ENDING", _("ENDING"))
    )
    key = models.CharField(max_length = 100)
    name = models.CharField(max_length = 200)
    users = models.ManyToManyField(User)
    max_users = models.PositiveSmallIntegerField()
    current_users = models.PositiveSmallIntegerField()
    ai_count = models.PositiveSmallIntegerField()
    status = models.CharField(max_length = 20, choices = STATUSES)
    # Esto se rellena a mano, y es max_users - ai_count
    # Sirve básicamente para la lista de matchmaking
    capacity = models.PositiveSmallIntegerField()

class FeedbackMail(models.Model):
    email = models.CharField(max_length = 1000)
    subject = models.CharField(max_length = 1000)
    body = models.CharField(max_length = 10000)
    sent = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null = True)

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

class UserProfileGameBackground(models.Model):
    profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE)
    BACKGROUNDS = (
        ("blue", _("Blue")),
        ("deepcyan", _("Deep cyan")),
        ("gray", _("Gray")),
        ("green", _("Green")),
        ("violet", _("Violet"))
    )
    background = models.CharField(max_length = 100, default="blue", choices = BACKGROUNDS)

class UserProfilePicture(models.Model):
    picture = CloudinaryField('profpicture')
    profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE)

def getUserProfile(user):
    try:
        user2 = User.objects.get(id = user.id)
        profile = UserProfile.objects.get(user = user2)
        try:
            profile.userprofilegamebackground
        except:
            UserProfileGameBackground(profile = profile).save()
    except ObjectDoesNotExist:
        profile = UserProfile(user = user2)
        profile.save()
        background = UserProfileGameBackground(profile = profile)
        background.save()
    return profile

def getUserProfilePictureUrl(user):
    pf = getUserProfile(user)
    # Salta una excepción si se intenta coger el pfp y no tiene el objeto creado
    try:
        if pf.userprofilepicture == None:
            return "/static/default-prof-picture.png"
        else:
            return pf.userprofilepicture.picture.url
    except:
        return "/static/default-prof-picture.png"

def getBackgroundsAsJson():
    tups = UserProfileGameBackground.BACKGROUNDS
    backgrounds = []
    for i in range(len(tups)):
        backgrounds.append(tups[i][0])

    return json.dumps(backgrounds)