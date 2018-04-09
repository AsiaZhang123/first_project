from django.shortcuts import render,redirect
from django.core.urlresolvers import reverse
from users.models import Passport,Address
from django.http import JsonResponse
import re
from utils.decorators import login_required
# Create your views here.


def register(request):

    return render(request,'users/register.html')

def register_handle(request):

    username = request.POST.get('user_name')
    password = request.POST.get('pwd')
    email = request.POST.get('email')

    if not all([username,password,email]):

        return render(request,'users/register.html',{'errmsg':'参数不能为空！'})
    if not re.match(r'^[0-9a-z][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}',email):
        return render(request,'users/register.html',{'errmsg':'邮箱格式不合法！'})
    try:
        user = Passport.objects.get(username=username)
        return render(request, 'users/register.html', {'errmsg': '用户名已被注册！'})
    except Exception as e:
        passport = Passport.objects.add_one_passport(username=username, password=password, email=email)
        return redirect(reverse('books:index'))

def login(request):

    return render(request,'users/login.html')

def login_check(request):
    ''' 进行用户登录校验'''
    # 1.获取数据
    username = request.POST.get('username')
    password = request.POST.get('password')
    remember = request.POST.get('remember')

    #2.数据校验
    print('11111111111111',username,password,remember)
    if not all([username,password,remember]):
        return JsonResponse({'res':2})

    #3.进行处理：根据用户名和密码查找账户信息
    passport = Passport.objects.get_one_passport(username=username,password=password)
    print('2222222222',passport)
    if passport:
        # 用户名密码正确
        print('0000000000000')
        next_url = reverse('books:index')
        jres = JsonResponse({'res':1,'next_url':next_url})

        #判断是否需要记住用户名
        if remember == "ture":
            # 记住用户名
            jres.set_cookie('username',username,max_age = 7*24*3600)
        else:
            # 不要记住用户名
            jres.delete_cookie('username')

        # 记住用户的登录状态
        request.session['islogin'] = True
        request.session['username']=username
        request.session['passport_id']=passport.id

        return jres
    else:
        # 用户名或者密码错误
        return JsonResponse({'res':0})

def logout(request):
    '''用户退出登录'''
    #  清空用户的session信息
    print('55555555555555')
    request.session.flush()
    # 跳转到首页
    return redirect(reverse('books:index'))

@login_required
def user(request):
    '''用户中心-信息页'''
    passport_id = request.session.get('passport_id')
    # 获取用户的基本信息
    addr = Address.objects.get_default_address(passport_id=passport_id)

    books_li = []

    context = {
        'addr': addr,
        'page': 'user',
        'books_li':books_li
    }
    return render(request,'users/user_center_info.html',context)