from django.contrib import admin
from authentication.models import CustomUser, OTP

admin.site.register(CustomUser)
admin.site.register(OTP)