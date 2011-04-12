from django.contrib import admin

from mailer.models import Message, DontSendEntry, MessageLog


class MessageAdmin(admin.ModelAdmin):
    list_display = ["id", "account", "to_addresses", "subject", "when_added", "priority"]
    
    readonly_fields = ['subject', 'to_addresses', 'body']
    
    def body(self, obj):
        email = obj.email
        if email is not None:
            return email.body.replace('\n', '<br>')
        return ""
    body.allow_tags = True
    

class DontSendEntryAdmin(admin.ModelAdmin):
    list_display = ["to_address", "when_added"]


class MessageLogAdmin(admin.ModelAdmin):
    list_display = ["id", "account", "to_addresses", "subject", "when_attempted", "result"]
    readonly_fields = ['subject', 'to_addresses', 'body']
    
    def body(self, obj):
        email = obj.email
        if email is not None:
            return email.body.replace('\n', '<br>')
        return ""
    body.allow_tags = True

admin.site.register(Message, MessageAdmin)
admin.site.register(DontSendEntry, DontSendEntryAdmin)
admin.site.register(MessageLog, MessageLogAdmin)