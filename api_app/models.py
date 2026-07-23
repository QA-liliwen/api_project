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
        verbose_name = '1_接口表'
        verbose_name_plural = '1_接口表'

    def __str__(self):
        return f"{self.id} {self.name} ({self.url})"


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
        verbose_name = '2_测试项表'
        verbose_name_plural = '2_测试项表'

    def __str__(self):
        return f"{self.id} {self.name}"


# 测试记录表
class DB_run_result(models.Model):
    test_items = models.CharField("测试项ID列表", max_length=500, blank=True, default="")
    description = models.TextField('描述', blank=True)
    status = models.CharField("状态", max_length=20, default="running")
    total = models.IntegerField("总用例数", null=True, blank=True)
    passed = models.IntegerField("通过", null=True, blank=True)
    failed = models.IntegerField("失败", null=True, blank=True)
    skipped = models.IntegerField("跳过", null=True, blank=True)
    jenkins_build_url = models.CharField("Jenkins构建链接", max_length=500, blank=True, null=True, default="")

    started_at = models.DateTimeField("开始时间", null=True, blank=True)
    finished_at = models.DateTimeField("结束时间", null=True, blank=True)
    duration_seconds = models.FloatField("执行耗时(秒)", null=True, blank=True)

    executor = models.CharField("执行人", max_length=100, blank=True, default="")
    trigger_source = models.CharField("触发来源", max_length=50, blank=True, default="web")
    env = models.CharField("执行环境", max_length=50, blank=True, default="")

    cases_json_file = models.CharField("用例JSON文件名", max_length=255, blank=True, null=True, default="")
    log_file = models.CharField("日志文件名", max_length=255, blank=True, null=True, default="")
    report_file = models.CharField("测试报告文件名", max_length=255, blank=True, null=True, default="")

    class Meta:
        verbose_name = '3_测试记录表'
        verbose_name_plural = '3_测试记录表'

    def __str__(self):
        return f"{self.id} {self.description} {self.test_items}"
