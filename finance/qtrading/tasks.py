# Create your tasks here
#celery
from __future__ import absolute_import, unicode_literals
from celery import shared_task

import datetime,time,re,random

#日志
import logging
log_file = "./log/finance-{}.log".format(time.strftime("%Y-%m-%d",time.localtime(time.time())))
log_level = logging.DEBUG
logger = logging.getLogger("loggingmodule.NomalLogger")
handler = logging.FileHandler(log_file)
formatter = logging.Formatter("\n[%(asctime)s][%(levelname)s][%(funcName)s]\n%(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(log_level)

#binance-python
from binance.client import Client
from binance.websockets import BinanceSocketManager
from binance.exceptions import BinanceAPIException

from requests.exceptions import ConnectionError
from django.db import connection 
from django.utils import timezone
from django.db.models import Q,Count,Sum

from reuser.models import ReUser
from qtrading.models import Qtrading,Order,Trade,CancelStandbyOrders
from currencies.models import Asset,DepositDetails,SymbolInfo,AccountInfo,Ticker24

from django.core.mail import send_mail
from django.conf import settings
from django.core.cache import cache

'''
#定时任务，获取市场合理的波段收益
@shared_task
def volatility_update():
    super_user = ReUser.objects.get(id=1)
    api_key = super_user.apikey
    api_secret = super_user.Secret
    try:
        client = Client(api_key, api_secret)
        symbol_list=['BNBUSDT','BTCUSDT']
        for each in symbol_list:
            hl=[]
            ifo=client.get_historical_klines(each, Client.KLINE_INTERVAL_5MINUTE, "60 minutes ago UTC")
            al = [ifo[:4]]+[ifo[4:8]]+[ifo[8:12]]
            for key,value in enumerate(al):
                rate = (float(max([i[2] for i in value]))/float(min([i[3] for i in value]))-1)*0.7+sum([float(i[2])/float(i[3])-1 for i in value])/40*3
                hl.append((key+3)*rate/12)
            cursor = SymbolInfo.objects.get(symbol=each)
            cursor.volatility=sum(hl)
            cursor.save()
    except:
        logger.info('最优波动价格更新失败！')
'''

@shared_task
def get_ticker24():
    api_key = "vmPUZE6mv9SD5VNHk4HlWFsOr6aKE2zvsw0MuIgwCIPy6utIco14y7Ju91duEh8A"
    api_secret = "NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0j"

    client = Client(api_key, api_secret)
    ifo=client.get_ticker()
    Ticker24.objects.all().delete()
    for each in ifo:
        closeTime = timezone.make_aware(timezone.datetime.fromtimestamp(float(each['closeTime'])/1000))
        openTime = timezone.make_aware(timezone.datetime.fromtimestamp(float(each['openTime'])/1000))

        ticker24 = Ticker24(
            askPrice=float(each['askPrice']),
            priceChangePercent=float(each['priceChangePercent']),
            volume=float(each['volume']),
            openPrice=float(each['openPrice']),
            quoteVolume=float(each['quoteVolume']),
            lowPrice=float(each['lowPrice']),
            priceChange=float(each['priceChange']),
            count=float(each['count']),
            bidQty=float(each['bidQty']),
            symbol=each['symbol'],
            prevClosePrice=float(each['prevClosePrice']),
            highPrice=float(each['highPrice']),
            lastPrice=float(each['lastPrice']),
            firstId=float(each['firstId']),
            askQty=float(each['askQty']),
            lastQty=float(each['lastQty']),
            bidPrice=float(each['bidPrice']),
            weightedAvgPrice=float(each['weightedAvgPrice']),
            lastId=float(each['lastId']),
            closeTime=closeTime,
            openTime=openTime)
        ticker24.save()
    logger.info('24hticker 更新成功！')

    #except:
    #    logger.info('24ticker数据更新失败！')

#发送邮件
@shared_task
def send_mail_(receiver,msg):
    '''
    if msg['X']:
        n_time=time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(float(msg['E'])/1000))
        #邮件的正文内容
        mail_content = "信息类型:{0}.\n\n交易对:{1}.\n订单id:{2}.\n买卖方:{3}.\n订单价格:{4}.\n订单数量:{5}.\n\n事件发生时间:{6}.\n订单状态:{7}.\n\n详细信息:\
        ".format(msg['e'],msg['s'],msg['i'],msg['S'],msg['p'],msg['q'],n_time,msg['X'])+str(msg)

        mail_title = msg['s']+'市场有新的操作!(您的币安量化交易程序)'
    '''
    mail_title='【warning】!!!!(您的币安量化交易程序)'
    mail_content=msg
    '''
    if not cache.get(receiver):
        cache.set(receiver, msg, 60*10)
    '''
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = receiver
    send_mail(mail_title,mail_content, from_email,[to_email,],fail_silently=False)

#保存下单信息
@shared_task
def save_ifo(ifo,account_id,symbol_id,qtrade_id,parent_order):
    time = timezone.make_aware(timezone.datetime.fromtimestamp(ifo['transactTime']/1000))
    order_price = float(ifo['price']) * float(ifo['origQty'])

    Order(account_id=account_id,symbol_id=symbol_id,orderId=ifo['orderId'],clientOrderId=ifo['clientOrderId'],
        price=ifo['price'],origQty=ifo['origQty'],executedQty=ifo['executedQty'],status=ifo['status'],
        order_type=ifo['type'],side=ifo['side'],order_price=order_price,time=time,parent_order=parent_order,
        q_trading_id=qtrade_id).save()

#取消、重新下单
@shared_task
def _cancel_open_order(qtrade_id,msg,client):
    q_t = Qtrading.objects.get(id=qtrade_id)
    #q_income = SymbolInfo.objects.get(symbol=msg['s']).volatility
    q_income=0.006
    _count2 = Order.objects.filter(q_trading=q_t,status='NEW').filter(Q(price__lt=(1-q_income)*float(msg['p']))|Q(price__gt=(1+q_income)*float(msg['p'])))
    if _count2:
        for each in _count2:
            try:
                client.cancel_order(symbol=msg['s'],orderId=each.orderId)
                each.status = 'CANCELED'
                each.save()
                logger.info(str(each.orderId) + '  订单被取消！')
                CancelStandbyOrders(orderid_id=each.orderId).save()
            except BinanceAPIException:
                ifo = client.get_order(symbol=msg['s'],orderId=each.orderId)
                each.status = ifo['status']
                each.save()
                logger.info(['存入过渡数据库失败',each.orderId,"当前该订单状态为",each.status,])

    _count3 = CancelStandbyOrders.objects.filter(orderid__q_trading=q_t).filter(
        Q(orderid__price__gte=(1-q_income/3)*float(msg['p']))&Q(orderid__price__lte=(1+q_income/3)*float(msg['p'])))
    if _count3:
        for each in _count3:
            try:
                re_num_ = re.findall(r'QTRADE\d+N(\d+)',msg['c']) 
                if re_num_:
                    re_num = int(re_num_[0])
                    re_num +=1
                else:
                    re_num = 2
                newClientOrderId = str(each.orderId)+'QTRADE'+str(qtrade_id)+'N'+str(re_num)

                if each.orderid.side == 'BUY':
                    ifo = client.order_limit_buy(symbol=msg['s'],quantity=each.orderid.origQty,price=each.orderid.price,newClientOrderId=newClientOrderId)
                    
                elif each.orderid.side == 'SELL':
                    ifo =  client.order_limit_sell(symbol=msg['s'],quantity=each.orderid.origQty,price=each.orderid.price,newClientOrderId=newClientOrderId)
                each.delete()
                logger.info(str(msg['i'])+'完成，'+str(each.orderid.orderId) + '  订单被重启！=>' + str(ifo['orderId']))
                save_ifo.delay(ifo,q_t.account.id,msg['s'],q_t.id,each.orderid.parent_order)
                    
            except:
                logger.info(['恢复订单失败',each.orderid.orderId])

def random_str(num=20,arg=''):
    random_str_ = ''.join(random.choice('1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ') for i in range(num))+'QTRADE'+str(arg)
    return random_str_

class QtradingStart():
    def __init__(self,user_id,q_id,msg,client,is_q):
        now_user = ReUser.objects.get(id=user_id)
        self.client = client
        self.q_id = q_id
        #self.q_t = Qtrading.objects.get(account_id=user_id,id=q_id)
        self.msg = msg
        self.user_id = user_id
        self.is_q = is_q

    #下新的子订单
    def p_orders(self):
        symbolinfo = SymbolInfo.objects.get(symbol=self.msg['s'])
        tickSize = symbolinfo.tickSize*1
        stepSize = symbolinfo.stepSize*1

        q_income = float(self.q_t.q_income)
        #q_income = SymbolInfo.objects.get(symbol=self.msg['s']).volatility
        q_amount = float(self.q_t.q_amount)
        h_price  = float(self.q_t.h_price)
        l_price  = float(self.q_t.l_price)
        
        price_s = (float(self.msg['p'])*pow((1+q_income),0.5))//tickSize * tickSize
        price_b = (float(self.msg['p'])/pow((1+q_income),0.5))//tickSize * tickSize

        quantity_s =(q_amount/price_s)//stepSize * stepSize
        quantity_b =(q_amount/price_b)//stepSize * stepSize

        cout1 =Order.objects.filter(account_id=self.user_id,q_trading_id=self.q_t.id,status='NEW')
        max_ = self.q_t.amount-self.q_t.q_amount
        b_ = cout1.filter(side='BUY').aggregate(Sum('order_price'))['order_price__sum']
        s_ = cout1.filter(side='SELL').aggregate(Sum('order_price'))['order_price__sum']
        
        #判断单边new是否限制在总投入内
        if not b_ or not s_ or ( b_ < max_ and s_ < max_):
            try:
                #判断当前单是否为新高、新低
                if float(self.msg['p']) > h_price:
                    n_p = (float(self.msg['p'])/(1+q_income)) //tickSize * tickSize
                    n_q = (q_amount/n_p)//stepSize * stepSize
                    ifo = self.client.order_limit_buy(symbol=self.msg['s'],quantity=n_q,price=n_p)
                    parent_order = Order.objects.get(account_id=self.user_id,orderId=self.msg['i']).parent_order
                    save_ifo.delay(ifo,self.user_id,self.msg['s'],self.q_t.id,parent_order)

                elif float(self.msg['p']) < l_price:
                    n_p = (float(self.msg['p'])/(1+q_income))//tickSize * tickSize
                    n_q = (q_amount/n_p)//stepSize * stepSize
                    ifo = self.client.order_limit_sell(symbol=self.msg['s'],quantity=n_q,price=n_p)
                    parent_order = Order.objects.get(account_id=self.user_id,orderId=self.msg['i']).parent_order
                    save_ifo.delay(ifo,self.user_id,self.msg['s'],self.q_t.id,parent_order)

                else:
                    parent_order = self.msg['i']
                    #判断新高、新低
                    if price_s > h_price:
                        ifo = self.client.order_limit_sell(symbol=self.msg['s'],quantity=quantity_s,price=price_s,newClientOrderId=random_str(arg=self.q_t.id))

                    elif price_b < l_price:
                        ifo = self.client.order_limit_buy(symbol=self.msg['s'],quantity=quantity_b,price=price_b,newClientOrderId=random_str(arg=self.q_t.id))

                    else:
                        ifo2 = self.client.order_limit_buy(symbol=self.msg['s'],quantity=quantity_b,price=price_b,newClientOrderId=random_str(arg=self.q_t.id))
                        save_ifo.delay(ifo2,self.user_id,self.msg['s'],self.q_t.id,parent_order)
                        ifo = self.client.order_limit_sell(symbol=self.msg['s'],quantity=quantity_s,price=price_s,newClientOrderId=random_str(arg=self.q_t.id))
                
                    save_ifo.delay(ifo,self.user_id,self.msg['s'],self.q_t.id,parent_order)

            except BinanceAPIException:
                logger.warn(str(self.msg['i'])+'在触发新时。'+self.q_t.q_name + "  库存不足!!")
                receiver=self.q_t.account.email
                send_mail_(receiver,str(self.msg['i'])+'在触发新时。'+self.q_t.q_name + "  库存不足！！！将无法触发。")
                
        else:
            logger.warn(str(self.msg['i'])+'在触发新时。买卖订单单边总金额将超过'+str(self.q_t.amount)+'!')


    #判断已完成单，触发新单的方法。更新订单状态
    def place_orders(self,target_order): 
        _count = Order.objects.filter(q_trading_id=self.q_id)
        self.q_t = Qtrading.objects.get(account_id=self.user_id,id=self.q_id)
        if self.q_t.method == '方法一':
            self.p_orders()
        if self.q_t.method == '波段捕手':             
            #判断兄弟订单是否完成
            parent_order = target_order.parent_order
            _count2 = _count.exclude(parent_order='Start').filter(parent_order=parent_order,status='FILLED')
            
            if _count2.count() >1:
                _count3 = _count2.order_by('alter_time')
                first_filled_order = _count3.first().orderId
                if first_filled_order == self.msg['i'] :
                    self.p_orders()
                    _cancel_open_order.delay(self.q_id,self.msg,self.client)
                elif not _count.filter(parent_order=first_filled_order):
                    self.p_orders()
                    _cancel_open_order.delay(self.q_id,self.msg,self.client)

            else:
                self.p_orders()
                _cancel_open_order.delay(self.q_id,self.msg,self.client)


    def trad_save(self):
        isbuyer = True if self.msg['S'] == 'BUY' else False
        time_trade = timezone.make_aware(timezone.datetime.fromtimestamp(self.msg['T']/1000))
        executed_price = float(self.msg['p'])*float(self.msg['l'])        
        try:
            Trade(trade_id=self.msg['t'],account_id=self.user_id,order_id=self.msg['i'],price=self.msg['p'],
                qty=self.msg['l'],commission=self.msg['n'],commissionAsset=self.msg['N'],isbuyer=isbuyer,
                time=time_trade,isMaker=True,isBestMatch=True,executed_price=executed_price,
                q_trading_id=self.q_id).save() 
        except:
            logger.info([self.msg['i'],self.msg['c'],'无法保存此交易信息！'])

        #修改订单状态   
        target_order = Order.objects.filter(orderId=self.msg['i']).first()
        if not target_order :
            logger.info([self.msg['i'],'未找到，等候5s。'])
            time.sleep(5)
            target_order = Order.objects.filter(orderId=self.msg['i']).first()
        if target_order:
            target_order.status = self.msg['X']
            target_order.executedQty = self.msg['z']
            target_order.save()
            #判断是否触发量化
            if self.is_q:
                self.place_orders(target_order)
            else:
                logger.info([self.msg['i'],self.msg['c'],'不满足条件 不进入触发新环节！']) 
        else:
            logger.info([self.msg['i'],'未找到此订单在数据库的数据！'])


        
#币安返回的数据保存    
@shared_task
def _trad_save(user_id,q_id,msg,client,is_q):
    QtradingStart(user_id,q_id,msg,client,is_q).trad_save()
        

class GetMsg():
    def __init__ (self,user_id):
        self.user = ReUser.objects.get(id=user_id)
        self.api_key = self.user.apikey
        self.api_secret = self.user.Secret


    #websocket数据处理
    def process_message(self,msg):
        #防止长时间未操作断开mysql------------------------
        try:  
            connection.connection.ping()  
        except:  
            connection.close()

        q_trade = Qtrading.objects.filter(account_id=self.user.id,iswork=1).values_list('id',flat=True)
        if q_trade:
            if msg['e'] == 'error':
                logger.info(self.user.username + "    Disconnect!!")
                self.binance_start()
            elif (msg['e'] == 'executionReport' ) :
                logger.info([self.user.username,msg['s'],msg['X'],msg['S'],msg['i'],msg['t'],msg['p'],msg['q'],msg['l']])
                #收件人邮箱receiver '188740210@qq.com','416243035@qq.com'
                if (msg['x'] == 'TRADE') and (msg['X'] == 'FILLED'): 
                    qid = re.findall(r'QTRADE(\d+)',msg['c'])   
                    is_q = False             
                    if qid:
                        q_id = int(qid[0]) 
                        is_q = True if (q_id in q_trade) else False
                    else:
                        q_id = ''
                        
                    _trad_save.delay(self.user.id,q_id,msg,self.client,is_q)
                    #logger.info([msg['i'],msg['c'],'不是我们网站下的订单！'])
                         
        else:
            self.bm.stop_socket(self.conn_key)
            #self.bm.close()
            logger.info(self.user.username +"    Close!!!!!")

     #开始websocket
    def binance_start(self):
        try:
            self.client = Client(self.api_key,self.api_secret)
            self.bm = BinanceSocketManager(self.client)
            self.conn_key = self.bm.start_user_socket(self.process_message)
            self.bm.start()
            logger.info(self.user.username + "    Establish connection!!")
        except ConnectionError as e:
            logger.info(self.user.username + "    Disconnect!!")

            time.sleep(20)
            self.binance_start()

@shared_task
def q_start_(user_id):
    GetMsg(user_id).binance_start()


