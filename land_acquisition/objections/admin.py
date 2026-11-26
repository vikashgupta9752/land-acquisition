from django.contrib import admin
from .models import Objection


@admin.register(Objection)
class ObjectionAdmin(admin.ModelAdmin):
    list_display = ('id', 'subject', 'landowner', 'project', 'category', 'status', 'created_at')
    list_filter = ('status', 'category', 'project')
