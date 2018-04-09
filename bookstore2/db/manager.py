from django.db import models
from utils.hash import get_hash

class PassportManager(models.Manager):
    def add_one_passport(self,username,password,email):

        passport = self.create(username=username,password=get_hash(password),email=email)

        return passport

    def get_one_passport(self,username,password):
        try:
            passport = self.get(username=username,password=get_hash(password))
        except Exception:
            passport = None
        return passport


class AddressManager(models.Manager):
    '''地址模型管理类'''
    def get_default_address(self,passport_id):
        '''查询指定用户的默认收货地址'''
        try:
            addr = self.get(passport_id=passport_id,is_default=True)
        except self.model.DoesNotExist:
            # 没有默认收货地址
            addr = None
        return addr

    def add_one_address(self,passport_id,recipient_name,recipient_addr,zip_code,recipient_phone):
        '''添加收货地址'''
        #判断用户是否有默认收货地址
        addr = self.get_default_address(passport_id=passport_id)

        if addr:
            #存在默认地址
            is_default = False
        else:
            is_default = True

        # 添加一个地址
        addr = self.create(
            passport_id = passport_id,
            recipient_name = recipient_name,
            recipient_addr=recipient_addr,
            zip_code=zip_code,
            recipient_phone = recipient_phone,
            is_default = is_default

        )
        return addr


class BooksManager(models.Manager):
    '''商品模型管理类'''
    # sort = 'new' 按照创建时间进行排序
    # sort = 'hot' 按照商品销量进行排序
    # sort = 'price' 按照商品的价格进行排序
    # sort = 'default' 按照默认顺序排序

    def get_books_by_type(self,type_id,limit=None,sort='default'):

        if sort == 'new':
            order_by =('-create_time',)
        elif sort =='hot':
            order_by = ('-sales',)
        elif sort == 'price':
            order_by = ('price',)
        else:
            order_by = ('-pk',)

        books_li = self.filter(type_id=type_id).order_by(*order_by)

        if limit:
            books_li = books_li[:limit]

        return books_li

    def get_books_by_id(self,books_id):
        try:
            book = self.get(id=books_id)
        except self.model.DoesNotExist:
            book = None
        return book
