from django.contrib import admin
from .models import Message

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'recipient', 'subject', 'sent_at', 'read_at')
    list_filter = ('sender', 'recipient')
    search_fields = ('subject', 'body')
    autocomplete_fields = ('sender', 'recipient')
    readonly_fields = ('sent_at',)