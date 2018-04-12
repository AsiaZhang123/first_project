from django.shortcuts import render,redirect
from books.models import Books
from django.conf import settings
from utils.decorators import login_required
from django.http import JsonResponse
from django.core.urlresolvers import reverse
from users.models import Address
from django_redis import get_redis_connection
from django.db import transaction
from order.models import OrderInfo, OrderGoods
from datetime import datetime
import time
import os


@login_required
def order_place(request):
    '''显示提交订单页面'''
    #接受数据
    books_ids = request.POST.getlist('books_ids')

    #校验数据
    if not all(books_ids):
        # 跳转回购物车页面
        return redirect(reverse('cart:show'))

    # 用户收货地址
    passport_id = request.session.get('passport_id')
    addr = Address.objects.get_default_address(passport_id=passport_id)

    # 用户要购买商品的信息
    books_li =[]
    # 商品的总数目和总金额
    total_count = 0
    total_price = 0

    conn = get_redis_connection('default')
    cart_key = 'cart_%d' % passport_id

    for id in books_ids:
        # 根据id 获取商品的信息
        books = Books.objects.get_books_by_id(books_id=id)
        # 从redis中获取要购买的商品的数目
        count = conn.hget(cart_key,id)
        books.count = count
        #计算商品的小计
        amount = int(count)*books.price
        books.amount =amount
        books_li.append(books)

        # 累计计算商品的总数目和总金额
        total_count += int(count)
        total_price += amount

    # 商品收费和实付款
    transit_price = 10
    total_pay = total_price + transit_price

    # 1,2,3
    books_ids = ','.join(books_ids)
    #组织模板上下文
    context = {
        'addr':addr,
        'books_li':books_li,
        'total_count':total_count,
        'total_price':total_price,
        'transit_price':transit_price,
        'total_pay':total_pay,
        'books_ids':books_ids,
    }

    return render(request,'order/place_order.html',context)


# order/views.py
# 提交订单，需要向两张表中添加信息
# s_order_info ：订单信息表 添加一条
# s-order-books: 订单商品表，订单中买了几件商品，添加几条记录
# 前段需要提交过来的数据： 地址 支付方式 购买的商品id

# 1 向订单表中添加一条信息
# 2 遍历向订单商品表中添加信息
    # 2.1 添加订单商品信息之后，增加商品销量，减少库存
    #2.2 累计计算订单商品的总数目和总金额
# 3 更新订单商品的总数目和总金额
# 4 清除购物车对应的信息

# 事物：原子性：一组sql操作，要么都成功，要么都失败
# 开启事务：begin
# 回滚事务：rollback
# 提交事务：commit
# 设置保存点：savepoint 保存格式
# 回滚到保存点： rollback to 保存点

@transaction.atomic
def order_commit(request):
    '''生成订单'''
    # 验证用户是否登录
    if not request.session.has_key('islogin'):
        return JsonResponse({'res':0,'errmsg':'用户未登录'})
    # print('1111111111111')
    # 接受数据
    addr_id = request.POST.get('addr_id')
    pay_method = request.POST.get('pay_method')
    books_ids = request.POST.get('books_ids')
    print('222222222222',addr_id,pay_method,books_ids)
    # 进行数据校验
    if not all([addr_id,pay_method,books_ids]):
        return JsonResponse({'res':1,'errmsg':'数据不完整'})
    # print('22222222222222223333333333333333')
    try:
        addr = Address.objects.get(id=addr_id)
    except Exception:
        return JsonResponse({'res':2,'errmsg':"地址信息错误"})
    # print('2222222222244444444444')
    if int(pay_method) not in OrderInfo.PAY_METHODS_ENUM.values():
        return JsonResponse({'res':3,'errmsg':'不支持的支付方式'})

    # 订单创建
    # 组织订单信息
    # print('232323232323')
    passport_id = request.session.get('passport_id')
    # 订单id ：20171029110830+ 用户id
    order_id = datetime.now().strftime('%Y%m%d%H%M%S') + str(passport_id)

    # 运费
    transit_price = 10
    # 订单商品总数和总金额
    total_count = 0
    total_price = 0
    print('333333333',order_id)
    # 创建一个保存点
    sid = transaction.savepoint()
    # print('00000000000000000')
    try:
    # 向订单信息表中添加一条数据
        order = OrderInfo.objects.create(
            order_id=order_id,
            passport_id=passport_id,
            addr_id=addr_id,
            total_count=total_count,
            total_price=total_price,
            transit_price=transit_price,
            pay_method=pay_method
        )
        # print('66666666666666')
        # 向订单商品表中添加订单商品的记录
        books_ids = books_ids.split(',')
        conn = get_redis_connection('default')
        cart_key = 'cart_%d'% passport_id
        # print('77777777777',books_ids)
        #  遍历获取用户购买的商品信息
        for id in books_ids:
            book = Books.objects.get_books_by_id(books_id=id)
            if book is None:
                transaction.savepoint_rollback(sid)
                return JsonResponse({'res':4,'errmsg':'商品信息错误'})

            # 获取用户购买的商品数目
            count = conn.hget(cart_key,id)

            # 判断商品的库存
            if int(count) > book.stock:
                transaction.savepoint_rollback(sid)
                return JsonResponse({'res':5,'errmsg':'商品库存不足'})
            # print('8888888888888')
            # 创建一条订单商品的记录
            OrderGoods.objects.create(
                order_id = order_id,
                books_id = id,
                count = count,
                price = book.price,
            )

            # 增加商品的销量，较少商品的库存
            book.sales += int(count)
            book.stock += int(count)
            book.save()
            # print('999999999999')
            #累计计算商品的总数目和总价
            total_count += int(count)
            total_price += int(count)*book.price

        # 更新订单商品总数和总价
        order.total_count = total_count
        order.total_price = total_price
        order.save()
        # print('444444444444444')
    except Exception:
        # 操作数据库任意一步出错，进行回滚操作
        # print('55555555555555555')
        transaction.savepoint_rollback(sid)
        return JsonResponse({'res':7,'errmsg':'服务器错误'})

    # 清除购物车对应的记录
    print('66666666666666')
    conn.hdel(cart_key,*books_ids)
    # 提交事务
    transaction.savepoint_commit(sid)
    return  JsonResponse({'res':6})


# order/views.py
# 前端需要发过来的参数:order_id
# post
from alipay import Alipay

def order_pay(request):
    '''订单支付'''
    # 用户登录判断
    if not request.session.has_key('islogin'):
        return JsonResponse({'res':0,'errmsg':'用户未登录'})

    # 接收订单id
    order_id = request.POST.get('order_id')

    # 数据校验
    if not order_id:
        return JsonResponse({'res':1,'errmsg':'订单不存在'})
    try:
        order = OrderInfo.objects.get(
            order_id=order_id,
            status=1,
            pay_method=3
        )
    except OrderInfo.DoesNotExist:
        return JsonResponse({'res':2,'errmsg':'订单信息出错'})


    # 支付宝进行交互
    alipay = Alipay(
        appid = "2016090800464054",# 应用id
        app_notify_url=None, # 默认回调url
        app_private_key_path=os.path.join(settings.BASE_DIR,'order/app_private_key.pem'),
        alipay_public_key_path =os.path.join(settings.BASE_DIR,'order/alipay_private_key.pem'),# 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
        sign_type = "RAS2",
        debug=True,
    )

    total_pay = order.total_price + order.transit_price
    order_string = alipay.api_alipay_trade_page_pay(
        out_trade_no = order_id,
        total_amount = str(total_pay),
        return_url = None,
        notify_url = None
    )

    pay_url = settings.ALIPAY_URL + '?' + order_string
    return JsonResponse({'res':3,'pay_url':pay_url,'message':'OK'})


def check_pay(request):
    '''获取用户支付的结果'''
    # 用户登录判断
    if not request.session.has_key('islogin'):
        return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

    passport_id = request.session.get('passport_id')
    # 接收订单id
    order_id = request.POST.get('order_id')

    # 数据校验
    if not order_id:
        return JsonResponse({'res': 1, 'errmsg': '订单不存在'})

    try:
        order = OrderInfo.objects.get(
            order_id = order_id,
            passport_id=passport_id,
            pay_method=3
        )
    except OrderInfo.DoesNotExist:
        return JsonResponse({'res':2,'errmsg':'订单信息出错'})
    # 和支付宝进行交互

    alipay = Alipay(
        appid="2016090800464054",  # 应用id
        app_notify_url=None,  # 默认回调url
        app_private_key_path=os.path.join(settings.BASE_DIR, 'df_order/app_private_key.pem'),
        alipay_public_key_path=os.path.join(settings.BASE_DIR, 'df_order/alipay_public_key.pem'),
        # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
        sign_type="RSA2",  # RSA 或者 RSA2
        debug=True,  # 默认False
    )
    while True:
        # 进行支付结果查询
        result = alipay.api_alipay_trade_query(order_id)
        code = result.get('code')
        if code == '10000' and result.get('trade_status') == "TRADE_SUCCESS":
            # 用户支付成功
            # 改变订单状态
            order.status = 2 # 代发货
            # 填写支付宝交易号
            order.trade_id = result.get('trade_no')
            order.save()

            return JsonResponse({"res":3,'message':'支付成功'})
        elif code=='40004' or (code == '10000' and result.get('trade_status')=='WAIT_BUYER_PAY'):
            # 支付订单还未生成，继续查询
            # 用户还未完成支付，继续查询
            time.sleep(5)
            continue
        else:
            # 支付出错
            return JsonResponse({'res': 4, 'errmsg': '支付出错'})