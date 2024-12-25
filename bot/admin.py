from django.contrib import admin
from .models import User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('telegram_id', 'username', 'full_name', 'games_played', 'highest_score', 'date_joined')
    search_fields = ('telegram_id', 'username', 'full_name')
