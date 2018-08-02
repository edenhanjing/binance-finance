from django.shortcuts import render
from django.http import HttpResponseRedirect,HttpResponse,JsonResponse
from django.utils import timezone
from django.contrib import auth,messages
from reuser.models import ReUser
from qtrading.models import Qtrading,Order,Trade,CancelStandbyOrders
from currencies.models import Asset,DepositDetails,SymbolInfo,AccountInfo
from django.core.paginator import Paginator 
# Create your views here.
from binance.client import Client
from binance.exceptions import BinanceAPIException

from django.db.models import Q,Count,Sum,functions
from django.contrib.auth.decorators import login_required 
from django.views.decorators.csrf import csrf_exempt

import datetime
import qtrading.tasks as bias
from finance.utils import AssistFun,page_fun

@login_required
def qtrading(request):
    context ={}
    context['qtradings'] = Qtrading.objects.filter(account=request.user).order_by('-create_time')[:10]
    return render(request,'qtrading/qtrading.html',context)

@login_required
@csrf_exempt
def create_qtrading(request):
    context={}
    errors=[]
    symbol_list=['BTCUSDT','BNBUSDT']
    
    if request.method == 'POST':
        
        q_name=request.POST.get('q_name')
        method=request.POST.get('method')
        symbol=request.POST.get('symbol')
        #start_price=float(request.POST.get('start_price'))
        amount=float(request.POST.get('amount'))
        q_income=float(request.POST.get('q_income'))
        q_amount=float(request.POST.get('q_amount'))
        h_price = request.POST.get('h_price')
        l_price = request.POST.get('l_price')
        
        if Qtrading.objects.filter(account=request.user).filter(Q(symbol_id=symbol,iswork=True)|Q(q_name=q_name)):
            messages.warning(request,'此类量化交易实例已经建立(一个市场只能建立一个实例，且不可重名！)')

        else:
            s_list = ['BNBUSDT']
            s_list.append(symbol)
            symbol_list = list(set(s_list))

            api_key = request.user.apikey
            api_secret = request.user.Secret
            client = Client(api_key, api_secret)
            assf = AssistFun(request.user.id,client,symbol_list)
            assf.Up_inventory()
            account_info = AccountInfo.objects.filter(account=request.user,total__gt=0)
            total_account = account_info.aggregate(Sum('market_value'))['market_value__sum']
            
            ifo = client.get_symbol_ticker(symbol=symbol)
            this_price = float(ifo['price'])

            q_t = Qtrading(account=request.user,q_name=q_name,method=method,symbol_id=symbol,
                amount=amount,q_income=q_income,q_amount=q_amount,h_price=h_price,l_price=l_price,
                this_price=this_price,total_account=total_account).save()
        
            #q_t=Qtrading.objects.get(id=10)
            if Qtrading.objects.filter(account=request.user,iswork=1).count() == 1:
                bias.q_start_.delay(request.user.id)
            return HttpResponseRedirect('/qtrading/')

    context['symbol_list'] = symbol_list
    return render(request,'qtrading/create_qtrading.html',context)

@login_required
@csrf_exempt
def qtrading_info(request,slug):
    context = {}
    api_key = request.user.apikey
    api_secret = request.user.Secret
    client = Client(api_key, api_secret)
    q_trading = Qtrading.objects.get(account=request.user,id=slug)

    #关闭实例---------------------
    if request.method == 'POST':
        slug_q_t = q_trading
        slug_q_t.iswork = False
        slug_q_t.save()
        CancelStandbyOrders.objects.filter(orderid__q_trading_id=slug).delete()
        try:
            ifo = client.order_limit_buy(symbol='BNBUSDT',quantity=2,price='5')
            ifo_= client.cancel_order(symbol='BNBUSDT',orderId=ifo["orderId"])
        except:
            pass
        return HttpResponseRedirect('/qtrading/')

    trading_stream = Trade.objects.filter(account=request.user,q_trading_id=slug)
    all_orders  = Order.objects.filter(q_trading__id=slug)

    s_list = ['BNBUSDT']
    s_list.append(q_trading.symbol_id)
    symbol_list = list(set(s_list))
    
    

    assf = AssistFun(request.user.id,client,symbol_list)
    #assf.all_orders()

    #计算交易完成对数--------------------------------------------------
    assf.Up_inventory()
    assf.all_access()
    context['total_info'] = assf.totle_inventory()
    account_info = AccountInfo.objects.filter(account=request.user,total__gt=0)

    context['account_info'] = account_info.order_by('-market_value')

    if q_trading.iswork:
        actual_i = account_info.aggregate(Sum('market_value'))['market_value__sum']-q_trading.total_account

        asset_price = Asset.objects.get(name=q_trading.symbol.baseAsset).price
        price_fluncuation = (float(asset_price)-q_trading.this_price)

        simulation_i = price_fluncuation*(q_trading.amount/q_trading.this_price)

        #quantitative_i2 = actual_i - price_fluncuation*q_trading.this_baseAsset_q

        commission = trading_stream.values('commissionAsset').annotate(Sum("commission"))
        commission_cost = sum([each['commission__sum']*Asset.objects.get(name=each['commissionAsset']).price for each in commission])

        #print(quantitative_i2,'----------',commission_cost)
        t_c = trading_stream.filter(isbuyer=True).aggregate(Sum("executed_price"))['executed_price__sum']
        if not t_c:t_c = 0
        f_c = trading_stream.filter(isbuyer=False).aggregate(Sum("executed_price"))['executed_price__sum']
        if not f_c:f_c = 0
        buy_qty__sum = trading_stream.filter(isbuyer=True).aggregate(Sum("qty"))['qty__sum']
        if not buy_qty__sum:buy_qty__sum = 0
        sell_qty__sum = trading_stream.filter(isbuyer=False).aggregate(Sum("qty"))['qty__sum']
        if not sell_qty__sum:sell_qty__sum = 0

        quantitative_i =(f_c-t_c)+float(asset_price)*(buy_qty__sum-sell_qty__sum)-commission_cost
        #context['quantitative_i2']=quantitative_i2


        q_trading.relatively_empty = price_fluncuation*(buy_qty__sum-sell_qty__sum)-commission_cost  #相较于空仓
        q_trading.quantitative_i = quantitative_i  #量化收益
        q_trading.simulation_full = quantitative_i-simulation_i #相较于满仓
        q_trading.actual_i = actual_i  #实际收益
        q_trading.save() 

    f_pair={} 
    filled      = all_orders.filter(status='FILLED').values('parent_order').annotate(o_count=Count('parent_order'))
    filled_pair = filled.filter(o_count=2).count()
    f_pair['filled_pair']        = filled_pair
    f_pair['filled_pair_amount'] = filled_pair*q_trading.q_amount
    f_pair['buy_pair']           = all_orders.filter(status='NEW',side='BUY').count()
    f_pair['sell_pair']          = all_orders.filter(status='NEW',side='SELL').count()
    f_pair['buy_pair_amount']    = all_orders.filter(status='NEW',side='BUY').aggregate(Sum('order_price'))['order_price__sum']
    f_pair['sell_pair_amount']   = all_orders.filter(status='NEW',side='sell').aggregate(Sum('origQty'))['origQty__sum']
    f_pair['actual_i']           = q_trading.actual_i
    f_pair['relatively_empty']   = q_trading.relatively_empty
    f_pair['simulation_full']       = q_trading.simulation_full
    f_pair['quantitative_i']     = q_trading.quantitative_i
    f_pair['complete_new']       = all_orders.filter(status='NEW').values('parent_order').annotate(o_count=Count('parent_order')).filter(o_count=2).count()
    
    context['f_pair']            = f_pair
    
    #当前委托（NEW）深度图,数据
    chartdate1 = {}
    new_orders = all_orders.filter(status='NEW').values_list('price').annotate(volume=Sum('order_price'))
    chartdate1['bids'] = [list(i) for i in new_orders.filter(side='BUY')]
    chartdate1['asks'] = [list(i) for i in new_orders.filter(side='SELL')]
    context['chartdate1']        = chartdate1

    #买卖成交（/5min），数据
    chartdate3=[] 
    now_time = timezone.datetime.utcnow().replace(tzinfo=timezone.utc)
    start_time = now_time-datetime.timedelta(minutes=185)
    if start_time < q_trading.create_time:
        start_time = q_trading.create_time

    time_count = round((now_time - start_time )/datetime.timedelta(minutes=5),0)
    all_orders2 = Order.objects.filter(q_trading__id=slug).exclude(parent_order='Start').select_related()
    for i in range(int(time_count)):
        chartdate3_={}
        start_time += datetime.timedelta(minutes=5)
        chartdate3_['date'] = (start_time+datetime.timedelta(hours=8)).strftime("%H:%M")
        all_orders_filled = all_orders2.filter(alter_time__lte=start_time,status='FILLED')
        chartdate3_['filled_pair'] = all_orders_filled.values('parent_order').annotate(o_count=Count('parent_order')).filter(o_count=2).count()
        if i !=0:
            chartdate3_['filled_pair_each'] = chartdate3_['filled_pair'] -  chartdate3[-1]['filled_pair'] 
        else:
            chartdate3_['filled_pair_each'] = chartdate3_['filled_pair']
        chartdate3_["filled_buy_"] = all_orders_filled.filter(side='BUY').count()
        if i !=0:
            chartdate3_['filled_buy'] = chartdate3_['filled_buy_'] - chartdate3[-1]['filled_buy_'] 
        else:
            chartdate3_['filled_buy'] = chartdate3_['filled_buy_']
        chartdate3_["filled_sell_"] = all_orders_filled.filter(side='SELL').count()
        if i !=0:
            chartdate3_['filled_sell'] = chartdate3_['filled_sell_'] -  chartdate3[-1]['filled_sell_'] 
        else:
            chartdate3_['filled_sell'] = chartdate3_['filled_sell_']
        if i == (int(time_count)-1):
            chartdate3_["bulletClass"]= "lastBullet"
        all_orders_new = all_orders2.filter(time__lte=start_time).exclude(status='CANCELED')
        chartdate3_['new_buy'] = all_orders_new.filter(side='BUY').count() -chartdate3_['filled_buy_']
        chartdate3_['new_sell'] = all_orders_new.filter(side='SELL').count() -chartdate3_['filled_sell_']
        chartdate3.append(chartdate3_)


    context['chartdate3'] = chartdate3[-36:]


    context['all_orders']        = all_orders.order_by('-parent_order','-time')[:100]
    context['openoeders']        = all_orders.filter(Q(status='NEW')|Q(status="PARTIALLY_FILLED")).order_by('-parent_order')
    context['canceled_orders']   = all_orders.filter(status='CANCELED')
    context['q_trading']         = q_trading

    return render(request,'qtrading/qtrading_info.html',context)

@csrf_exempt
def buy_or_sell(request):
    if request.method == 'POST' and request.user.is_authenticated:
        symbol = request.POST.get("symbol")
        q_trading_id = request.POST.get("q_trading")

        symbolinfo = SymbolInfo.objects.get(symbol=symbol)
        tickSize = symbolinfo.tickSize*1
        stepSize = symbolinfo.stepSize*1

        api_key = request.user.apikey
        api_secret = request.user.Secret
        client = Client(api_key, api_secret)
        try:
            if request.POST.get("b_p"):
                b_p = float(request.POST.get("b_p"))//tickSize * tickSize
                b_q = (float(request.POST.get("b_t"))/b_p) //stepSize * stepSize
                ifo = client.order_limit_buy(symbol=symbol,quantity=b_q,price=b_p,newClientOrderId=bias.random_str(arg=q_trading_id))

            elif request.POST.get("s_p"):
                s_p =float(request.POST.get("s_p"))//tickSize * tickSize
                s_q = (float(request.POST.get("s_t"))/s_p)//stepSize * stepSize
                ifo = client.order_limit_sell(symbol=symbol,quantity=s_q,price=s_p,newClientOrderId=bias.random_str(arg=q_trading_id))

            if  ifo["orderId"] :
                response={'orderId':ifo["orderId"]}
                if q_trading_id:
                    bias.save_ifo(ifo,request.user.id,symbol,q_trading_id,'Start')
                else:
                    bias.save_ifo(ifo,request.user.id,symbol,None,None) 
        except:
            response = {'aa':"失败!"}

        return JsonResponse(response)

@csrf_exempt
def cancel_order(request):
    if request.method == 'POST':
        symbol = request.POST.get("symbol")
        order_id = request.POST.get("order_id")
        
        api_key = request.user.apikey
        api_secret = request.user.Secret
        client = Client(api_key, api_secret)

        cancel_order = Order.objects.get(orderId=order_id)
        try:
            ifo=client.cancel_order(symbol=symbol,orderId=order_id)
            if  ifo["orderId"]:
                cancel_order.status = 'CANCELED'
                response={'orderId':ifo["orderId"]}

        except BinanceAPIException:
            ifo = client.get_order(symbol=symbol,orderId=order_id)
            cancel_order.status = ifo['status']
            response = {'aa':"失败!","status":ifo['status']}

        cancel_order.save()
        return JsonResponse(response)

@login_required
@csrf_exempt
def trade(request):
    context={}
    trading_stream = Trade.objects.filter(account=request.user)
    if request.GET.get('search'):
        search = request.GET.get('search','')
        trading_stream = Trade.objects.filter(Q(account=request.user,order__orderId__contains=search)|Q(account=request.user,order__parent_order__contains=search))
        context['search'] = search
        
    paginator = Paginator(trading_stream,40)
    trading_list = paginator.get_page(request.GET.get('page',1))
    page_range = page_fun(trading_list,paginator)

    context['page_range'] = page_range
    context['trading_list'] = trading_list
    return render(request,'trade.html',context)

def ceshi(request):
    return render(request,'ceshi.html',)