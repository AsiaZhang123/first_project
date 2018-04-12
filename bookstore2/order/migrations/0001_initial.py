# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_auto_20180409_0900'),
        ('books', '0002_auto_20180409_0900'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrderGoods',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, verbose_name='ID', auto_created=True)),
                ('id_delete', models.BooleanField(default=False, verbose_name='删除标记')),
                ('create_time', models.DateTimeField(verbose_name='创建时间', auto_now_add=True)),
                ('update_time', models.DateTimeField(verbose_name='更新时间', auto_now=True)),
                ('count', models.IntegerField(default=1, verbose_name='商品数量')),
                ('price', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='商品价格')),
                ('books', models.ForeignKey(to='books.Books', verbose_name='订单商品')),
            ],
            options={
                'db_table': 's_order_books',
            },
        ),
        migrations.CreateModel(
            name='OrderInfo',
            fields=[
                ('id_delete', models.BooleanField(default=False, verbose_name='删除标记')),
                ('create_time', models.DateTimeField(verbose_name='创建时间', auto_now_add=True)),
                ('update_time', models.DateTimeField(verbose_name='更新时间', auto_now=True)),
                ('order_id', models.CharField(serialize=False, primary_key=True, verbose_name='订单编号', max_length=64)),
                ('total_count', models.IntegerField(default=1, verbose_name='商品总数')),
                ('total_price', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='商品总价')),
                ('transit_price', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='订单运费')),
                ('pay_method', models.SmallIntegerField(default=1, verbose_name='支付方式', choices=[(1, '货到付款'), (2, '微信支付'), (3, '支付宝'), (4, '银联支付')])),
                ('status', models.SmallIntegerField(default=1, verbose_name='订单状态', choices=[(1, '待支付'), (2, '代发货'), (3, '待收货'), (4, '待评价'), (5, '已完成')])),
                ('trade_id', models.CharField(blank=True, verbose_name='订单编号', unique=True, null=True, max_length=100)),
                ('addr', models.ForeignKey(to='users.Address', verbose_name='收货地址')),
                ('passport', models.ForeignKey(to='users.Passport', verbose_name='下单账户')),
            ],
            options={
                'db_table': 's_order_info',
            },
        ),
        migrations.AddField(
            model_name='ordergoods',
            name='order',
            field=models.ForeignKey(to='order.OrderInfo', verbose_name='所属订单'),
        ),
    ]
