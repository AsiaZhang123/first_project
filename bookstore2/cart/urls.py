from django.conf.urls import url
from cart import views

urlpatterns =[
    url(r'^add/$',views.cart_add,name='add'),  # 添加购物车数据
    url(r'^count/$',views.cart_count,name='count'),  # 获取用户购物车中商品的数量
    url(r'^show/$',views.cart_show,name='show'),  # 展示用户购物车中商品的数量
    url(r'^del/$',views.cart_del,name='del'),  # 购物车商品记录删除
    url(r'^update/$',views.cart_update,name='update')
]