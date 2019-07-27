from django.db import models
from django.contrib.auth.models import User
from cloudinary.models import CloudinaryField
from django.core.exceptions import ObjectDoesNotExist

# Create your models here.

# Representa una partida en memoria
class GameKey(models.Model):
    STATUSES = (
        ("WAITING", "WAITING"),
        ("PLAYING", "PLAYING"),
        ("ENDING", "ENDING")
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

class UserProfilePicture(models.Model):
    picture = CloudinaryField('profpicture')
    profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE)

def getUserProfile(user):
    try:
        user2 = User.objects.get(id = user.id)
        profile = UserProfile.objects.get(user = user2)
    except ObjectDoesNotExist:
        profile = UserProfile(user = user2)
        profile.save()
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