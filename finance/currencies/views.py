from django.shortcuts import render
from currencies.models import Asset,DepositDetails,SymbolInfo,AccountInfo,Ticker24
from qtrading.models import Qtrading,Order,Trade
# Create your views here.
from binance.client import Client
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required 
import json

def home(request):
    context ={}
    context['Ticker24'] = Ticker24.objects.all().order_by('-priceChangePercent')
    return render(request,'home.html',context) 
    

def asset_home(request):
    context ={}

    context['assets'] = Asset.objects.all().order_by('-market_cap')
    return render(request,'asset/asset_home.html',context)
    
def asset(request):
    pass
    

def symbol_home(request):
    context = {}

    context['symbols'] = SymbolInfo.objects.all().order_by('-quoteAsset')
    return render(request,'symbol/symbol_home.html',context)

@csrf_exempt
def symbol(request,slug):
    context = {}
    api_key = "vmPUZE6mv9SD5VNHk4HlWFsOr6aKE2zvsw0MuIgwCIPy6utIco14y7Ju91duEh8A"
    api_secret = "NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0j"
    client = Client(api_key, api_secret)
 
    ifo = client.get_historical_klines(slug, Client.KLINE_INTERVAL_1DAY, "60 day ago UTC")
    context['ifo'] = json.dumps(ifo)
    context['symbol'] = SymbolInfo.objects.get(symbol=slug)
    if request.user.is_authenticated:
        context['q_trading_list'] = Qtrading.objects.filter(account=request.user,symbol_id=slug,iswork=True)
    return render(request,'symbol/symbol.html',context)



'''
    #保存exchan_info----------------
    api_key = 'fkcX35mJZoBwEEKgAT7hFd9R3bnD4iw6WSUJJijKC27RaO94b6IIuvU15WIP1R3R'
    api_secret = '6FnpYJluhtZn2YpJRyBK9INmokG0mv8XgNgqcMFUBLLmm40B2N9PjYppcVDbV2UX'

    client = Client(api_key, api_secret)
    exchangeinfo = client.get_exchange_info()
    for each in exchangeinfo['symbols']:
        symbol=each['symbol']
        baseAssetPrecision = each['baseAssetPrecision']
        quotePrecision =each['quotePrecision']
        status=each['status']
        baseAsset =each['baseAsset']
        quoteAsset = each['quoteAsset']
        minPrice = each['filters'][0]['minPrice']
        maxPrice = each['filters'][0]['maxPrice']
        tickSize =each['filters'][0]['tickSize']
        maxQty = each['filters'][1]['maxQty']
        minQty = each['filters'][1]['minQty']
        stepSize= each['filters'][1]['stepSize']

        exifo=SymbolInfo(symbol=symbol,baseAssetPrecision=baseAssetPrecision,quotePrecision=quotePrecision,
            status=status,baseAsset=baseAsset,quoteAsset=quoteAsset,minPrice=minPrice,maxPrice=maxPrice,
            tickSize=tickSize,maxQty=maxQty,minQty=minQty,stepSize=stepSize)
        exifo.save()
    #--------------------------------
'''