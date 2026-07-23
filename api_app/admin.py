from django.contrib import admin
from .models import *

admin.site.register(DB_Interface)
admin.site.register(DB_TestItem)

@admin.register(DB_run_result)
class DBRunResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'test_items', 'description', 'started_at', 'finished_at', 'status', 'total', 'passed', 'failed')
