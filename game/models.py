from django.db import models
from django.contrib.auth.models import User


# Create your models here.

# Representa una partida en memoria
class GameKey(models.Model):
    key = models.CharField(max_length = 100)
    name = models.CharField(max_length = 200)
    users = models.ManyToManyField(User)
    max_users = models.PositiveSmallIntegerField()
    current_users = models.PositiveSmallIntegerField()
    ai_count = models.PositiveSmallIntegerField()

class FeedbackMail(models.Model):
    email = models.CharField(max_length = 1000)
    subject = models.CharField(max_length = 1000)
    body = models.CharField(max_length = 10000)
    sent = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null = True)