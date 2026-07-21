from django.contrib import admin
from .models import DB_Interface, DB_TestItem

admin.site.register(DB_Interface)
admin.site.register(DB_TestItem)
