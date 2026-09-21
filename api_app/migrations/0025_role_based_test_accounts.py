from django.db import migrations, models


# 账号体系从"测试项绑账号"改为"测试项绑角色"
# 1. 测试项: account_name -> role
# 2. 账号表: 唯一约束从 (env, username) 改为 (env, role)，旧数据清空待弹窗重录（6角色×3环境=18条）


def clear_old_accounts(apps, schema_editor):
    # 旧账号按 环境+用户名 维护，与新的 环境+角色 唯一约束不兼容，先清空
    DB_TestAccount = apps.get_model('api_app', 'DB_TestAccount')
    DB_TestAccount.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('api_app', '0024_db_testaccount_delete_db_token_and_more'),
    ]

    operations = [
        migrations.RunPython(clear_old_accounts, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='db_testitem',
            name='account_name',
        ),
        migrations.AddField(
            model_name='db_testitem',
            name='role',
            field=models.CharField(blank=True, default='', max_length=50, verbose_name='测试角色'),
        ),
        migrations.AddField(
            model_name='db_testaccount',
            name='role',
            field=models.CharField(default='', max_length=50, verbose_name='角色'),
        ),
        migrations.AlterUniqueTogether(
            name='db_testaccount',
            unique_together={('env', 'role')},
        ),
    ]
