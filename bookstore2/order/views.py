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
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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

from alipay import AliPay

def order_pay(request):
    '''订单支付'''
    # 用户登录判断
    if not request.session.has_key('islogin'):
        return JsonResponse({'res':0,'errmsg':'用户未登录'})

    # 接收订单id
    order_id = request.POST.get('order_id')

    # 数据校验
    print('0101010001101010',order_id)
    if not order_id:
        return JsonResponse({'res':1,'errmsg':'订单不存在'})
    try:
        order = OrderInfo.objects.get(order_id=order_id,
                                      status=1,
                                      pay_method=3)
        print('333333333333333444', order)
    except OrderInfo.DoesNotExist:
        print('4444444444444444')
        return JsonResponse({'res':2,'errmsg':'订单信息出错'})
    print('3333333333333333',order)
    # app_private_key_string = "uOsbCjCSzaFzPeBlV7ftXe5DAkW1UlusMhyWR0dRA93Fv3MzpmBIooyHPIpgs5mWfPZVjnz1GyW75zuSgBWNa3BaDoCpUsIZQbudxGJxSynnvWcgALPjAGXS6gWw7Z7fMUrGxbZzwWFVivsOOVsHCQOR9mBqCbxq1uYQnUr6Jh5Yhha92qWrlUr2qviPvPOzv0ukV+Zcd+lv/E36DhCi5MfMEpxcwypuEMQx/fkCgYEA1+UauT9e05Ma4UVd9jo3bIYBSjk9ac1I0ExooqS9bB+KEPWoCI8XUxpB9LYZklFJx33A7E2P8xMnICaL68n4qvPcNoCtomlcDbsgMxXkHO6uz30jpwA6IjQp2f3wPWEupEWYx+IzE3tA+XMFTJyBIeisZrXN6w34JHw9Nuv/R20CgYEAs4ujhBPFcWE4Z8Xh+gnlhNC9QlPppWD6EUNfdGsua5Krx+xyayDZL2sEyARqwNPNUxTKKPbIkUWVx8iBfTygnGtcLltVoPPvp9kIr9ZiPtgtEItsw1kkyMInKUC+Ufo8loevf6LID2TIZ55gcWMMa/4rLHLG8+ueO6Wg8TmzXdcCgYAqTgCAkERanRbFUbxpxVqa719NVg4Mr2c3OeG/DRz5FO0PCbQViUR+ykRmWVCFdVxJtQCazVAJx5UBHcyJNZh+ly5tl6Vuj8qz/hj/Kaj7amHi0pir3sWFckdJKhNrU6G6GtEnSdHMXXiL6Nf+/SPoqxktPy7Mgn4/WAD+xBvPuQKBgBd2Q+PagY6TWb+VyDXYXTnB3TlxpbKKvaLL3wljiClefTwe1cTSAg+EOJe6nAiepNIagWBg/0ycfzogJWusJIDMNruIC+SAe+y/G7d+mFAGB72Fuqy8VWY2mM93OmeT/57cFD7lkqcQUG/Z7lhizRi/mfyw8vak74Rz3FgpZhr5AoGBAJE/5mrm1iXYQpRdFI5MAQVPvQeT/YieRGaqGe26Sw2ARAOaCZdkrGB0B+FbfFDQuL1fGRPPfwfoz+yakGzgGLZrKWLwo5wLo32rKOPwpxGcEI/dYpjnmYcrqCuICoOATirH+rioi1sT6D0KYFe+tjANSB8TrmWw/8T12/oQDQNe"
    #
    # alipay_public_key_string = "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAl2r0+0y29TI4tTKHaTbcbL8vOdEOAhqgSjAjTJsXoxzZpj0NKD9953ToAPVwUuhbskjH/+29qFGwVVopOA4tr5Xn0LAmJZA9nm7S34HfG/4WMn+esaeQa3fUxynrxS7qznIGhDN0ggW4YHFuU75E3i7LGc8UgLm0gWquu8EqVIiPvQAWcRiTcsGPiAdVUfom0XRbwg/Xin0fzecZ4bY3ln7/mix4BMu1/HU4fJQ5gEIx/yQqPoz94WyQjWV/n9YIFNc+fEJgkHiRu0C78VmD481JmyJyzBIRjLPp/s8mZS5thUEXfdTqx1TsX0WxE8c7jjo1Lo21FqCuvpTfJo6ViwIDAQAB"

    # 支付宝进行交互
    print('0000000000000')

    # 将app_private_key.pem和app_public_key.pem拷贝到order文件夹下。
    app_private_key_path = os.path.join(BASE_DIR, 'order/app_private_key.pem')
    alipay_public_key_path = os.path.join(BASE_DIR, 'order/app_public_key.pem')
    print('1111111111112')
    app_private_key_string = open(app_private_key_path).read()
    alipay_public_key_string = open(alipay_public_key_path).read()

    print('111111111111')
    # 和支付宝进行交互
    alipay = AliPay(
        appid="2016091100486793",  # 应用id
        app_notify_url=None,  # 默认回调url
        app_private_key_string=app_private_key_string,
        alipay_public_key_string=alipay_public_key_string,  # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
        sign_type="RSA2",  # RSA 或者 RSA2
        debug=True,  # 默认False
    )
    print('12222222222222222')
    # 电脑网站支付，需要跳转到https://openapi.alipaydev.com/gateway.do? + order_string
    total_pay = order.total_price + order.transit_price  # decimal
    order_string = alipay.api_alipay_trade_page_pay(
        out_trade_no=order_id,  # 订单id
        total_amount=str(total_pay),  # Json传递，需要将浮点转换为字符串
        subject='尚硅谷书城%s' % order_id,
        return_url=None,
        notify_url=None  # 可选, 不填则使用默认notify url
    )

    pay_url = settings.ALIPAY_URL + '?' + order_string
    print('server12121212121221',pay_url)
    return JsonResponse({'res': 3, 'pay_url': pay_url, 'message': 'OK'})

from alipay import AliPay
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
        order = OrderInfo.objects.get(order_id=order_id,
                                      passport_id=passport_id,
                                      pay_method=3)
    except OrderInfo.DoesNotExist:
        return JsonResponse({'res': 2, 'errmsg': '订单信息出错'})
    print('server0000000000000000')
    app_private_key_path = os.path.join(BASE_DIR, 'order/app_private_key.pem')
    alipay_public_key_path = os.path.join(BASE_DIR, 'order/app_public_key.pem')

    app_private_key_string = open(app_private_key_path).read()
    alipay_public_key_string = open(alipay_public_key_path).read()
    print('server11111111111111111111')
    # 和支付宝进行交互
    alipay = AliPay(
        appid="2016091100486793", # 应用id
        app_notify_url=None,  # 默认回调url
        app_private_key_string=app_private_key_string,
        alipay_public_key_string=alipay_public_key_string,  # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
        sign_type = "RSA2",  # RSA 或者 RSA2
        debug = True,  # 默认False
    )
    print('server22222222222222222')
    while True:
        # 进行支付结果查询
        print('server22222',order_id,alipay.api_alipay_trade_query)
        result = alipay.api_alipay_trade_query(trade_no=order_id)
        print('server22222', result)
        code = result.get('code')
        print('server22222222333333333333',result,code)
        if code == '10000' and result.get('trade_status') == 'TRADE_SUCCESS':
            # 用户支付成功
            # 改变订单支付状态
            print('server333333333333')
            order.status = 2 # 待发货
            # 填写支付宝交易号
            order.trade_id = result.get('trade_no')
            order.save()
            # 返回数据
            return JsonResponse({'res':3, 'message':'支付成功'})
        elif code == '40004' or (code == '10000' and result.get('trade_status') == 'WAIT_BUYER_PAY'):
            # 支付订单还未生成，继续查询
            # 用户还未完成支付，继续查询
            print('server4444444444444444')
            time.sleep(5)
            continue
        else:
            # 支付出错
            print('server555555555555555')
            return JsonResponse({'res':4, 'errmsg':'支付出错'})