from django.shortcuts import render,redirect
from django.http import HttpResponseRedirect,HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import auth,messages
from django.core.cache import cache
from django.db.models import Q,Count,Sum,functions

from reuser.models import ReUser
from qtrading.models import Qtrading,Order,Trade,CancelStandbyOrders
from currencies.models import Asset,DepositDetails,SymbolInfo,AccountInfo

from django.conf import settings
from django.core.mail import EmailMessage

from binance.client import Client
from binance.exceptions import BinanceAPIException

from reuser.models import ReUser
import finance.utils as utils
from finance.utils import AssistFun
import re

def login(request):
    errors =[]
    username = None
    password = None
    if request.method == "POST":
        if not request.POST.get('username'):
            errors.append('用户名不能为空')
        else:
            username = request.POST.get('username')

        if not request.POST.get('password'):
            errors = request.POST.get('密码不能为空!')
        else:
            password = request.POST.get('password')

        if username is not None and password is not None:
            user = auth.authenticate(username=username,password=password)
            if user :
                auth.login(request,user)
                next_ = request.GET.get('next','/')
                return HttpResponseRedirect(next_)
            else:
                try:
                    ReUser.objects.get(username=username)
                    messages.warning(request,'未激活用户!')
                except:
                    messages.warning(request,'用户名或密码错误!')

    print(request.path)
    return render(request,'login.html',)

def logout(request):
    auth.logout(request)
    return HttpResponseRedirect('/currencies')

def register(request):
    errors = []
    if request.method == 'POST':
        print(request.POST)

        email = request.POST.get('email')
        if len(email)>4 and re.search(r'^[A-Za-z0-9_@.-]+$', email): 
            try:
                ReUser.objects.get(username=email)
                errors.append('邮箱存在，请更换邮箱注册。') 
            except : 
                pass
        else:
            errors.append('用户名有问题，不能注册。字符太少或含用奇怪字符!') 

        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        if password != password2:
            errors.append('两次输入密码不一致！')

        api_key = request.POST.get('api_key')
        secret = request.POST.get('secret')

        if not errors:   
            user = ReUser.objects.create_user(username=email,password=password,is_active=False)
            user.email = email
            user.apikey = api_key
            user.Secret = secret
            user.save()

            random_str = utils.random_str()
            #cache.set(user.id, random_str, 1*60*60)

            #发送验证邮件---------------------------
            subject, from_email, to_email = '用户激活-伟年科技', settings.DEFAULT_FROM_EMAIL,email
            html_content = utils.activation_html_content(user.id,random_str)

            msg = EmailMessage(subject, html_content, from_email, [to_email])
            msg.content_subtype = "html"  # Main content is now text/html
            msg.send()

            messages.warning(request,'登录您的邮箱，点击激活账号链接！')
            return redirect('reuser:login')

    return render(request,'register.html', {'errors': errors})

@csrf_exempt
def activation(request):
    userid = request.GET.get('userid','')
    random_str = request.GET.get('random_str','')
    if userid and random_str:
        reuser = ReUser.objects.get(id=userid)
        if reuser.is_active:
            messages.warning(request,'此账号已被激活，请登录！')
        else:
            reuser.is_active = True
            reuser.save()
            messages.warning(request,'账号激活完成，请登录！')
        return redirect('reuser:login')
    print(request.GET)


def userview(request):

    context = {}
    symbol_list = ['BNBUSDT','BTCUSDT']
    api_key = request.user.apikey
    api_secret = request.user.Secret

    #try:
    client = Client(api_key, api_secret)

    assf = AssistFun(request.user.id,client,symbol_list)
    #获取订单信息
    assf.all_orders()
    
    #保存存取记录
    assf.all_access()

    #获取交易信息
    assf.all_trading()

    #更新库存信息
    assf.Up_inventory()
   
    
    #更新库存汇总
    #context['undone_orders'] = undone_orders = assf.undone_orders()

    context['total_info'] = assf.totle_inventory()
    context['openoeders'] = Order.objects.filter(account=request.user).filter(Q(status='NEW')|Q(status="PARTIALLY_FILLED")).order_by('-time')
    context['ordering_strem'] = Trade.objects.filter(account=request.user).order_by('-time')[:40]
    context['canceled_orders'] = Order.objects.filter(account=request.user,status='CANCELED').order_by('-time')[:5]
    context['account_info'] = AccountInfo.objects.filter(account=request.user,total__gt=0).order_by('-market_value')


    return render(request,'userview.html',context)