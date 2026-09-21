from django.db import models


# 测试角色清单（存储/脚本用英文；前端展示时映射回中文，固定 6 角色 × 3 环境 = 18 条）
TEST_ROLES = ['zhihui', 'exam', 'content', 'org', 'student', 'afterschool']


# 接口数据
class DB_Interface(models.Model):
    name = models.CharField('接口名称', max_length=200)
    tag = models.ForeignKey('DB_FirstTag', verbose_name='一级标签', on_delete=models.SET_NULL, null=True, blank=True)
    url = models.CharField('请求URL', max_length=500)
    method = models.CharField('请求方法', max_length=10)
    headers = models.JSONField('请求头', default=dict, blank=True)
    params = models.JSONField('请求参数', default=dict, blank=True)
    description = models.TextField('描述', blank=True)
    is_del = models.BooleanField('是否删除', default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    sort = models.IntegerField('序号', null=True, blank=True, default=0)

    class Meta:
        verbose_name = '01_接口表'
        verbose_name_plural = '01_接口表'

    def __str__(self):
        return f"{self.id} {self.name} ({self.url})"


# 测试项
class DB_TestItem(models.Model):
    name = models.CharField('测试项名称', max_length=200, unique=True)
    second_tag = models.ForeignKey('DB_SecondTag', verbose_name='二级标签', on_delete=models.SET_NULL, null=True, blank=True)
    type = models.IntegerField('项目类型', choices=[(1, '单接口用例'), (2, '多接口脚本')], default=1)
    interface = models.ForeignKey('DB_Interface', verbose_name='关联接口', on_delete=models.SET_NULL, null=True, blank=True)
    cases = models.JSONField("用例数据", default=list, blank=True)
    script_content = models.TextField('脚本内容', blank=True, default='')
    script_filename = models.CharField('脚本文件名', max_length=255, blank=True, default='')
    doc_link = models.CharField('文档链接', max_length=500, blank=True, default='')
    sql_database = models.CharField('SQL库名', max_length=200, blank=True, default='')
    role = models.CharField('测试角色', max_length=50, blank=True, default='')
    system = models.CharField('测试端', max_length=10, blank=True, default='')
    description = models.TextField('描述', blank=True)
    is_del = models.BooleanField('是否删除', default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    sort = models.IntegerField("序号", null=True, blank=True)

    class Meta:
        verbose_name = '02_测试项表'
        verbose_name_plural = '02_测试项表'

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
        verbose_name = '03_测试记录表'
        verbose_name_plural = '03_测试记录表'

    def __str__(self):
        return f"{self.id} {self.description} {self.test_items}"


# 一级标签
class DB_FirstTag(models.Model):
    name = models.CharField('一级标签名称', max_length=100, unique=True)
    is_del = models.BooleanField('是否删除', default=False)
    sort = models.IntegerField("序号", null=True, blank=True)

    class Meta:
        verbose_name = '04_一级标签'
        verbose_name_plural = '04_一级标签'

    def __str__(self):
        return f"{self.id} {self.name}"


# 二级标签
class DB_SecondTag(models.Model):
    first_tag = models.ForeignKey('DB_FirstTag', verbose_name='一级标签', on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField('二级标签名称', null=True, blank=True, max_length=100)
    is_del = models.BooleanField('是否删除', default=False)
    sort = models.IntegerField("序号", null=True, blank=True)

    class Meta:
        verbose_name = '05_二级标签'
        verbose_name_plural = '05_二级标签'

    def __str__(self):
        return f"{self.first_tag_id}_{self.id} {self.name}"


# 域名
class DB_Domain(models.Model):
    name = models.CharField('域名名称', null=True, blank=True, max_length=200, unique=True)
    domain = models.CharField('域名', null=True, blank=True, max_length=200, unique=True)
    app_server = models.CharField('App登录域名', null=True, blank=True, max_length=200)
    is_default = models.BooleanField('默认项', default=False)
    is_del = models.BooleanField('是否删除', default=False)

    class Meta:
        verbose_name = '06_域名表'
        verbose_name_plural = '06_域名表'

    def __str__(self):
        return f"{self.name} {self.domain}"


# 环境
class DB_Env(models.Model):
    name = models.CharField('域名名称', null=True, blank=True, max_length=50, unique=True)
    env = models.CharField('环境', null=True, blank=True, max_length=200, unique=True)
    is_default = models.BooleanField('默认项', default=False)
    is_del = models.BooleanField('是否删除', default=False)

    class Meta:
        verbose_name = '07_环境表'
        verbose_name_plural = '07_环境表'

    def __str__(self):
        return f"{self.name} {self.env}"


# 请求头模板
class DB_HeaderTemplate(models.Model):
    name = models.CharField('请求头模板名称', null=True, blank=True, max_length=100)
    system = models.CharField('系统类型', max_length=10, blank=True, default='')
    headers = models.JSONField('请求头内容', default=dict, blank=True)
    is_del = models.BooleanField('是否删除', default=False)

    class Meta:
        verbose_name = '09_请求头模板表'
        verbose_name_plural = '09_请求头模板表'

    def __str__(self):
        return f"{self.name}"


# SQL 连接配置
class DB_SqlEnv(models.Model):
    env_name = models.CharField('环境名称', max_length=50, unique=True)  # 与 DB_Domain.domain 对应，如 devapi1.lingshi.com
    host = models.CharField('主机', max_length=200)
    port = models.IntegerField('端口', default=3306)
    user = models.CharField('账号', max_length=100)
    password = models.CharField('密码', max_length=200)
    is_del = models.BooleanField('是否删除', default=False)

    class Meta:
        verbose_name = '10_SQL连接表'
        verbose_name_plural = '10_SQL连接表'

    def __str__(self):
        return f"{self.env_name} {self.host}:{self.port}"


# 工具箱
# tool_key 同时作为前端组件映射 key 与后端注册表 key，上线后不得修改
class DB_Tool(models.Model):
    name = models.CharField('工具名称', max_length=100)
    tool_key = models.CharField('工具标识', max_length=50, unique=True)
    category = models.CharField('分类', max_length=50, null=True, blank=True)
    description = models.TextField('工具说明', null=True, blank=True)
    is_del = models.BooleanField('是否删除', default=False)
    sort = models.IntegerField('序号', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '11_工具表'
        verbose_name_plural = '11_工具表'

    def __str__(self):
        return f"{self.id} {self.name} ({self.tool_key})"


# 测试账号（按 环境+角色 维护映射；执行时按 环境+角色 解析用户名，批量获取 token）
class DB_TestAccount(models.Model):
    env = models.ForeignKey('DB_Env', verbose_name='测试环境', on_delete=models.SET_NULL, null=True, blank=True)
    role = models.CharField('角色', max_length=50, default='')
    username = models.CharField('测试用户名', max_length=100)
    is_del = models.BooleanField('是否删除', default=False)

    class Meta:
        verbose_name = '12_测试账号表'
        verbose_name_plural = '12_测试账号表'
        unique_together = ('env', 'role')

    def __str__(self):
        return f"{self.env_id}_{self.role}_{self.username}"
