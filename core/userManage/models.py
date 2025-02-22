from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from datetime import timedelta
from django.utils import timezone

class EmailVerification(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='email_verification')
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=15)

    def __str__(self):
        return f"{self.user.email} - {self.code}"

class CustomPermission(models.Model):
    name = models.CharField(max_length=50)
    codename = models.CharField(max_length=150)
    description = models.CharField(max_length=150)

    def __str__(self):
        return self.name
    
class CustomRole(models.Model):
    name = models.CharField(max_length=50)
    permissions = models.ManyToManyField(CustomPermission, blank=True)
    description = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)
    

    def get_permission(self):
        return [perm.codename for perm in self.permissions.all()]

    def __str__(self):
        return self.name

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=11)
    role = models.ForeignKey(CustomRole, on_delete=models.CASCADE, null=True,blank=True)

    is_verified = models.BooleanField(default=False)

    def has_permission(self, perm):
        if self.role:
            return perm in self.role.get_permission()
        return False

    def __str__(self):
        return self.email
    

