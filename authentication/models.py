from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class PreRegister(models.Model):
    username = models.CharField(max_length = 100)
    password = models.CharField(max_length = 100)
    email = models.CharField(max_length = 500)
    verification = models.CharField(max_length = 100)

class RecoverPassword(models.Model):
    user = models.ForeignKey(User, on_delete = models.CASCADE, blank = False, null=False)
    key = models.CharField(max_length = 100, unique = True)