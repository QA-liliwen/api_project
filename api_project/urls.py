"""
URL configuration for api_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from api_app.views_test_item import *

urlpatterns = [
    path('admin/', admin.site.urls),
    path('update_run_result/', update_run_result),
    path('get_top_menu/', get_top_menu),    # 顶部一级标签行
    path('get_second_tags/', get_second_tags),  # 左侧二级标签行
    path('get_grouped_test_items/', get_grouped_test_items),

    path('upload_case/', upload_case),  # 上传用例xlsx
    path('upload_script/', upload_script),  # 上传多接口脚本.py
    path('download_script/', download_script),  # 下载脚本文件
    path('get_run_config/', get_run_config),    # 获取执行配置下拉数据
    path('execute_run/', execute_run),  # 执行测试（本地/Jenkins，由 run_mode 区分）
    path('get_test_item_detail/', get_test_item_detail),  # 获取测试项详情（编辑回填）
    path('get_interfaces/', get_interfaces),    # 获取接口列表（编辑下拉）
    path('get_interface_list/', get_interface_list),  # 接口列表页
    path('get_interface_detail/', get_interface_detail),  # 接口详情
    path('update_interface/', update_interface),  # 更新接口
    path('delete_interface/', delete_interface),  # 软删除接口
    path('get_run_result_list/', get_run_result_list),  # 测试结果列表页
    path('download_log/', download_log),  # 下载日志文件
    path('update_test_item/', update_test_item),  # 更新测试项
]
