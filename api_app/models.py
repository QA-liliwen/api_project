from django.db import models


# 接口数据
class DB_Interface(models.Model):
    id = models.IntegerField('序号', default=0, primary_key=True)
    name = models.CharField('接口名称', max_length=200)
    url = models.CharField('请求URL', max_length=500)
    method = models.CharField('请求方法', max_length=10)
    headers = models.JSONField('请求头', default=dict, blank=True)
    params = models.JSONField('请求参数', default=dict, blank=True)
    description = models.TextField('描述', blank=True)
    is_del = models.BooleanField('是否删除', default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '接口'
        verbose_name_plural = '接口'

    def __str__(self):
        return f"{self.name} ({self.url})"

# 测试项
class DB_TestItem(models.Model):
    id = models.CharField('id', max_length=200, primary_key=True)
    name = models.CharField('测试项名称', max_length=200, unique=True)
    type = models.IntegerField('项目类型', choices=[(1, '单接口用例'), (2, '多接口编排'), (3, '自定义脚本')], default=1)
    interface = models.IntegerField('关联接口号', default=0)
    cases = models.JSONField("用例数据", default=list, blank=True)
    description = models.TextField('描述', blank=True)
    is_del = models.BooleanField('是否删除', default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '测试项'
        verbose_name_plural = '测试项'

    def __str__(self):
        return f"{self.name}"

class DB_TestRun(models.Model):
    test_items = models.CharField("测试项ID", max_length=500)
    description = models.TextField('描述', blank=True)
    status = models.CharField("状态", max_length=20, default="running")
    total = models.IntegerField("总用例数", null=True, blank=True)
    passed = models.IntegerField("通过", null=True, blank=True)
    failed = models.IntegerField("失败", null=True, blank=True)
    skipped = models.IntegerField("跳过", null=True, blank=True)
    jenkins_build_url = models.CharField("Jenkins构建链接", max_length=500)
    started_at = models.DateTimeField("开始时间", auto_now_add=True)
