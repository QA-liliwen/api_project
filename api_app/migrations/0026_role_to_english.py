from django.db import migrations


# 角色值从中文改为英文（存储与脚本统一英文，前端展示时映射回中文）
# 智慧->zhihui、机构->org、学生->student、托管->afterschool；exam/content 原本即英文
ROLE_MAP = {'智慧': 'zhihui', '机构': 'org', '学生': 'student', '托管': 'afterschool'}


def to_english(apps, schema_editor):
    DB_TestItem = apps.get_model('api_app', 'DB_TestItem')
    DB_TestAccount = apps.get_model('api_app', 'DB_TestAccount')
    for old, new in ROLE_MAP.items():
        DB_TestItem.objects.filter(role=old).update(role=new)
        DB_TestAccount.objects.filter(role=old).update(role=new)


def to_chinese(apps, schema_editor):
    DB_TestItem = apps.get_model('api_app', 'DB_TestItem')
    DB_TestAccount = apps.get_model('api_app', 'DB_TestAccount')
    for old, new in ROLE_MAP.items():
        DB_TestItem.objects.filter(role=new).update(role=old)
        DB_TestAccount.objects.filter(role=new).update(role=old)


class Migration(migrations.Migration):

    dependencies = [
        ('api_app', '0025_role_based_test_accounts'),
    ]

    operations = [
        migrations.RunPython(to_english, to_chinese),
    ]
