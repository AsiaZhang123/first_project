# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_address'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='address',
            options={'verbose_name_plural': '收货地址', 'verbose_name': '收货地址'},
        ),
        migrations.AlterModelOptions(
            name='passport',
            options={'verbose_name_plural': '登记用户', 'verbose_name': '登记用户'},
        ),
    ]
