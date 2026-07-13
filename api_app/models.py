from django.db import models


class Interface(models.Model):
    """接口元数据"""
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
        return f"{self.name} ({self.method} {self.url})"


class TestItem(models.Model):
    """测试项 - 关联接口 + 用例/脚本"""
    TYPE_CHOICES = [
        (1, '单接口用例'),
        (2, '多接口编排'),
        (3, '自定义脚本'),
    ]
    name = models.CharField('测试项名称', max_length=200, unique=True)
    type = models.IntegerField('项目类型', choices=TYPE_CHOICES, default=1)
    interface = models.ForeignKey(Interface, on_delete=models.CASCADE,
        related_name='test_items', verbose_name='关联接口')
    excel_file = models.FileField('Excel用例文件', upload_to='test_cases/', blank=True)
    description = models.TextField('描述', blank=True)
    is_del = models.BooleanField('是否删除', default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '测试项'
        verbose_name_plural = '测试项'

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"

