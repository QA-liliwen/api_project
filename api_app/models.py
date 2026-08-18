from django.db import models


# 接口数据
class DB_Interface(models.Model):
    name = models.CharField('接口名称', max_length=200)
    url = models.CharField('请求URL', max_length=500)
    method = models.CharField('请求方法', max_length=10)
    headers = models.JSONField('请求头', default=dict, blank=True)
    params = models.JSONField('请求参数', default=dict, blank=True)
    description = models.TextField('描述', blank=True)
    is_del = models.BooleanField('是否删除', default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    sort = models.IntegerField('序号', null=True, blank=True, default=0)

    class Meta:
        verbose_name = '1_接口表'
        verbose_name_plural = '1_接口表'

    def __str__(self):
        return f"{self.id} {self.name} ({self.url})"


# 测试项
class DB_TestItem(models.Model):
    name = models.CharField('测试项名称', max_length=200, unique=True)
    second_tag = models.ForeignKey('DB_SecondTag', verbose_name='二级标签', on_delete=models.SET_NULL, null=True, blank=True)
    type = models.IntegerField('项目类型', choices=[(1, '单接口用例'), (2, '自定义脚本')], default=1)
    interface = models.ForeignKey('DB_Interface', verbose_name='关联接口', on_delete=models.SET_NULL, null=True, blank=True)
    cases = models.JSONField("用例数据", default=list, blank=True)
    script_content = models.TextField('脚本内容', blank=True, default='')
    script_filename = models.CharField('脚本文件名', max_length=255, blank=True, default='')
    description = models.TextField('描述', blank=True)
    is_del = models.BooleanField('是否删除', default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    sort = models.IntegerField("序号", null=True, blank=True)

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


# 一级标签
class DB_FirstTag(models.Model):
    name = models.CharField('一级标签名称', max_length=100, unique=True)
    is_del = models.BooleanField('是否删除', default=False)
    sort = models.IntegerField("序号", null=True, blank=True)

    class Meta:
        verbose_name = '4_一级标签'
        verbose_name_plural = '4_一级标签'

    def __str__(self):
        return f"{self.id} {self.name}"


# 二级标签
class DB_SecondTag(models.Model):
    first_tag = models.ForeignKey('DB_FirstTag', verbose_name='一级标签', on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField('二级标签名称', null=True, blank=True, max_length=100)
    is_del = models.BooleanField('是否删除', default=False)
    sort = models.IntegerField("序号", null=True, blank=True)

    class Meta:
        verbose_name = '5_二级标签'
        verbose_name_plural = '5_二级标签'

    def __str__(self):
        return f"{self.first_tag_id}_{self.id} {self.name}"


# 域名
class DB_Domain(models.Model):
    name = models.CharField('域名名称', null=True, blank=True, max_length=200, unique=True)
    domain = models.CharField('域名', null=True, blank=True, max_length=200, unique=True)
    is_del = models.BooleanField('是否删除', default=False)

    class Meta:
        verbose_name = '6_域名表'
        verbose_name_plural = '6_域名表'

    def __str__(self):
        return f"{self.name} {self.domain}"


# 环境
class DB_Env(models.Model):
    name = models.CharField('域名名称', null=True, blank=True, max_length=50, unique=True)
    env = models.CharField('环境', null=True, blank=True, max_length=200, unique=True)
    is_del = models.BooleanField('是否删除', default=False)

    class Meta:
        verbose_name = '7_环境表'
        verbose_name_plural = '7_环境表'

    def __str__(self):
        return f"{self.name} {self.env}"


# Token
class DB_Token(models.Model):
    name = models.CharField('Token名称', null=True, blank=True, max_length=100)
    token = models.TextField('Token值', null=True, blank=True)
    is_del = models.BooleanField('是否删除', default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '8_Token表'
        verbose_name_plural = '8_Token表'

    def __str__(self):
        return f"{self.name} {self.token}"


# 请求头模板
class DB_HeaderTemplate(models.Model):
    name = models.CharField('请求头模板名称', null=True, blank=True, max_length=100)
    headers = models.JSONField('请求头内容', default=dict, blank=True)
    is_del = models.BooleanField('是否删除', default=False)

    class Meta:
        verbose_name = '9_请求头模板表'
        verbose_name_plural = '9_请求头模板表'

    def __str__(self):
        return f"{self.name}"
