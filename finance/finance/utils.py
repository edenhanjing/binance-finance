import random

#from reuser.models import ReUser
from qtrading.models import Qtrading,Order,Trade
from currencies.models import Asset,DepositDetails,SymbolInfo,AccountInfo

from django.utils import timezone
import datetime,time

def random_str(arg='',num=21):
    random_str_ = ''.join(random.choice('1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ') for i in range(num))+'QTRADE'+str(arg)
    return random_str_

def activation_html_content(user,random_str):
    html_content = '''<div style="margin: auto;width: 500px;border: 1px solid #3c484e;border-radius: 5px;"> 
                <div style="padding: 5px;background: #3c484e;color: #fff;">
                    <img src="http://18.218.225.58/static/favicon.jpeg" style="width:30px;height:30px;margin:0px 10px">
                    <span>欢迎您的加入！点击以下链接激活您的账户！</span>
                </div>
                <div style="padding: 10px;">
                    <a href="{0}">{0}</a>
                </div></div>'''.format('http://finance.quantyi.com/reuser/activation/?userid='+str(user)+'&random_str='+random_str)
    return html_content

def page_fun(queryset_list,paginator):
    p_n = queryset_list.number
    page_range = list(range(max(p_n -2,1),p_n))+\
        list(range(p_n,min(p_n + 2, paginator.num_pages)+1))
    if page_range[0] != 1:
        page_range.insert(0,1)
        if p_n - 1 > 3:
            page_range.insert(1,'...')
    if page_range[-1] != paginator.num_pages:
        if paginator.num_pages - p_n >3:
            page_range.insert(paginator.num_pages-2,'...')
        page_range.append(paginator.num_pages)
    return page_range
    

class AssistFun(object):
    """docstring for AssistFun"""
    def __init__(self,user_id,client,symbol_list):
        super(AssistFun, self).__init__()
        self.user_id = user_id
        self.client = client
        self.symbol_list = symbol_list
    #所有未完成委托
    def undone_orders(self):
        return self.client.get_open_orders()

    #所有委托 
    def all_orders(self):
        for i in self.symbol_list:
            my_orders = self.client.get_all_orders(symbol=i)
            sql_orderid_dict = dict(Order.objects.filter(account_id=self.user_id).values_list('orderId','status'))
            for o in my_orders:
                #保保存委托信息
                if o['orderId'] not in sql_orderid_dict.keys():
                    time = datetime.datetime.fromtimestamp(eval(str(o['time'])[:-3]+'.'+str(o['time'])[-3:]),timezone.utc)
                    order_price = float(o['price']) * float(o['origQty'])

                    inco = Order(account_id=self.user_id ,symbol=SymbolInfo.objects.get(symbol=o['symbol']),
                        orderId=o['orderId'],clientOrderId=o['clientOrderId'],price=o['price'],origQty=o['origQty'],
                        executedQty=o['executedQty'],status=o['status'],order_type=o['type'],side=o['side'],
                        time=time,order_price=order_price)
                    inco.save()
                #修改委托信息
                elif (sql_orderid_dict[o['orderId']] != o['status']):
                    target_order = Order.objects.get(account_id=self.user_id,orderId=o['orderId'])
                    target_order.status = o['status']
                    target_order.executedQty = o['executedQty']
                    target_order.save()

    #所有交易
    def all_trading(self):
        for i in self.symbol_list:
            my_trades = self.client.get_my_trades(symbol=i)
            sql_trades_list = list(Trade.objects.filter(account_id=self.user_id).values_list('trade_id',flat=True))
            for o in my_trades:
                if o['id'] not in sql_trades_list:         
                    time_trade = datetime.datetime.fromtimestamp(eval(str(o['time'])[:-3]+'.'+str(o['time'])[-3:]),timezone.utc)

                    executed_price = float(o['price'])*float(o['qty'])
                    try:
                        trad = Trade(trade_id=o['id'],account_id=self.user_id,order_id=o['orderId'],price=o['price'],qty=o['qty'],
                            commission=o['commission'],commissionAsset=o['commissionAsset'],isbuyer=o['isBuyer'],time=time_trade,
                            isMaker=o['isMaker'],isBestMatch=o['isBestMatch'],executed_price=executed_price)
                        trad.save()

                    except:
                        pass

    #所有存取记录
    def all_access(self):
        deposit_history = self.client.get_deposit_history()

        deposit_history_list = list(DepositDetails.objects.filter(account_id=self.user_id).values_list('txId',flat=True))
        for i in deposit_history['depositList']:
            if i['txId'] not in deposit_history_list:
                insertTime = datetime.datetime.fromtimestamp(eval(str(i['insertTime'])[:-3]+'.'+str(i['insertTime'])[-3:]),timezone.utc)
                DepositDetails(account_id=self.user_id,insertTime=insertTime,amount=i['amount'],
                    address=i['address'],addressTag=i['addressTag'],txId=i['txId'],asset_id=i['asset'],
                    status=i['status']).save()

                count4 = AccountInfo.objects.filter(account_id=self.user_id,asset_id=i['asset'])
                if count4:
                    count4=count4[0]
                else:
                    count4 = AccountInfo(account_id=self.user_id,asset_id=i['asset'])
                count4.cost =  float(count4.cost)+float(i['amount'])
                count4.save()

    #更新某些币的价格
    def Up_asset_price(self,asset_list):
        asset_list = asset_list
        asset_list.remove('USDT')

        all_price = self.client.get_symbol_ticker()
        [i for i in self.client.get_symbol_ticker() if  i['symbol']in asset_list]
        for each in asset_list:
            count9=SymbolInfo.objects.get(baseAsset=each,quoteAsset='USDT')
            if count9:
                count10 = Asset.objects.get(name=each)
                count10.price = float([i['price'] for i in all_price if  i['symbol']==count9.symbol][0])
                count10.save()
            else:
                count11 = SymbolInfo.objects.get(baseAsset=each,quoteAsset='BTC')
                count10 = Asset.objects.get(name=each)
                count10.price = float([i['price'] for i in all_price if  i['symbol']==count11.symbol][0])*float(
                    self.client.get_symbol_ticker(symbol='BTCUSDT')['price'])
                count10.save()        

    #更新库存信息  
    def Up_inventory(self):
        inventory = [i for i in self.client.get_account()['balances'] if float(i['locked'])>0 or float(i['free'])>0]
        asset_list = [i['asset'] for i in inventory]
        self.Up_asset_price(asset_list)

        accc_list = AccountInfo.objects.filter(account_id=self.user_id,total__gt=0).values_list('asset_id',flat=True)
        for each in set(accc_list)-set(asset_list):
            AccountInfo.objects.get(account_id=self.user_id,asset_id=each).delete()

        for i in inventory:

            acc = AccountInfo.objects.filter(account_id=self.user_id,asset_id=i['asset']).first()
            if not acc:
                acc = AccountInfo(account_id=self.user_id,asset_id=i['asset'])

            acc.free=i['free']
            acc.locked=i['locked']
            acc.total=float(i['free'])+float(i['locked'])
            try:
                acc.cost_price = float(acc.cost)/acc.total
            except:
                acc.cost_price = 0
            acc.market_value = float(acc.asset.price)*acc.total
            acc.profit_and_loss= float(acc.asset.price)*acc.total-float(acc.cost)
            if acc.cost<=0:
                acc.p_a_l_percent = None
            else:
                acc.p_a_l_percent = (acc.profit_and_loss/float(acc.cost))*100
            acc.save()  
        
        


    #更新库存汇总
    def totle_inventory(self):
        total_info = {}
        accountinfo_=AccountInfo.objects.filter(account_id=self.user_id,total__gt=0).order_by('-market_value')
        
        total_info['cost'] =sum(DepositDetails.objects.filter(account_id=self.user_id).values_list('amount',flat=True))
        total_info['market_value'] =sum(accountinfo_.values_list('market_value',flat=True))
        total_info['profit_and_loss'] =total_info['market_value']-total_info['cost']
        total_info['pl_percent']=(total_info['profit_and_loss']/total_info['cost'])*100
        total_info['exclude_usdt'] = total_info['market_value'] - float(accountinfo_.get(asset_id='USDT').total)
        return(total_info)