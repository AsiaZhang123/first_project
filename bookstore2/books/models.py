from django.db import models
from books.enums import *
from tinymce.models import HTMLField
from db.base_model import BaseModel
from db.manager import BooksManager
from django.core.files.storage import FileSystemStorage

# fs = FileSystemStorage(location='/root/zyz/first_project/bookstore2/collect_static')

# Create your models here.

class Books(BaseModel):
    '''商品模型类'''
    books_type_choices = ((k,v) for k,v in BOOKS_TYPE.items())
    status_choices = ((k,v) for k,v in STATUS_CHOICE.items())
    type_id = models.SmallIntegerField(default=PYTHON,choices=books_type_choices,verbose_name='商品种类')
    name = models.CharField(max_length=20,verbose_name='商品名称')
    desc = models.CharField(max_length=128,verbose_name='商品简介')
    price = models.DecimalField(max_digits=10,decimal_places=2,verbose_name='商品价格')
    unite = models.CharField(max_length=20,verbose_name='商品单位')
    stock = models.IntegerField(default=1,verbose_name='商品库存')
    sales = models.IntegerField(default=0,verbose_name='商品销量')
    detail = HTMLField(verbose_name='商品详情')
    image = models.ImageField(upload_to='books',verbose_name='商品图片')
    # image = models.ImageField(storage=fs, upload_to='books', verbose_name='商品图片')
    status = models.SmallIntegerField(default=ONLINE,choices=status_choices,verbose_name='商品状态')

    objects = BooksManager()

    class Meta:
        db_table = 's_books'
        verbose_name = '书籍'
        verbose_name_plural = verbose_name
    def __str__(self):
        return self.name