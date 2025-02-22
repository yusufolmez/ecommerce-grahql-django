from django.contrib import admin
from .models import CustomPermission,CustomRole,CustomUser,EmailVerification

admin.site.register(CustomPermission)
admin.site.register(CustomRole)
admin.site.register(CustomUser)
admin.site.register(EmailVerification)
