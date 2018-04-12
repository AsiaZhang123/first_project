# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('books', '0002_auto_20180409_0900'),
        ('users', '0003_auto_20180409_0900'),
    ]

    operations = [
        migrations.CreateModel(
            name='Comments',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, auto_created=True, verbose_name='ID')),
                ('id_delete', models.BooleanField(verbose_name='删除标记', default=False)),
                ('create_time', models.DateTimeField(verbose_name='创建时间', auto_now_add=True)),
                ('update_time', models.DateTimeField(verbose_name='更新时间', auto_now=True)),
                ('disabled', models.BooleanField(verbose_name='禁用评论', default=False)),
                ('content', models.CharField(verbose_name='评论内容', max_length=1000)),
                ('book', models.ForeignKey(to='books.Books', verbose_name='书籍ID')),
                ('user', models.ForeignKey(to='users.Passport', verbose_name='用户ID')),
            ],
            options={
                'db_table': 's_comment_table',
            },
        ),
    ]
