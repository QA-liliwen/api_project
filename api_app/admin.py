from django.contrib import admin
from .models import *

admin.site.register(DB_Interface)
admin.site.register(DB_TestItem)
admin.site.register(DB_FirstTag)
admin.site.register(DB_SecondTag)
admin.site.register(DB_Domain)
admin.site.register(DB_Env)
admin.site.register(DB_Token)
admin.site.register(DB_HeaderTemplate)

@admin.register(DB_run_result)
class DBRunResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'test_items', 'description', 'started_at', 'finished_at', 'status', 'total', 'passed', 'failed')
