from django.shortcuts import render
from django.http import JsonResponse

from api_app.models import *


# Create your views here.

# 进入首页
def api_list(request):
    Interface = DB_Interface.objects.filter(is_del=False).order_by('id')
    TestItem = DB_TestItem.objects.filter(is_del=False).order_by("id")
    res = {"Interface": Interface, "TestItem": TestItem}
    return render(request, 'api_list.html', res)
