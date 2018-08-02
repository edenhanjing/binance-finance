from django.db import models
from currencies.models import SymbolInfo
from reuser.models import ReUser
# Create your models here.

#量化交易实例
class Qtrading(models.Model):
	account = models.ForeignKey(ReUser,null=True,on_delete=models.CASCADE)
	q_name = models.CharField(max_length=100)
	method = models.CharField(max_length=100)
	symbol = models.ForeignKey(SymbolInfo,null=True,on_delete=models.CASCADE)

	#start_price = models.FloatField(null=True) 
	amount = models.FloatField() #总投入
	q_income = models.FloatField() #波段收益率
	q_amount = models.FloatField() #单笔投入金额
	h_price = models.FloatField() #预估波段高价
	l_price = models.FloatField() #预估波段低价
	iswork = models.BooleanField(default=True) #是否运行
	
	total_account = models.FloatField() #开始时账户市值
	this_price = models.FloatField() #开始时价格
	#this_baseAsset_q = models.FloatField() #开始时基准币的持有量

	simulation_full = models.FloatField(null=True) #模拟计算全仓状态下的收入
	relatively_empty = models.FloatField(null=True) #模拟空仓状态下的收入
	quantitative_i = models.FloatField(null=True) #量化收入
	actual_i = models.FloatField(null=True) #实际收入

	create_time = models.DateTimeField(auto_now_add=True)

#所有订单
class Order(models.Model):
	account = models.ForeignKey(ReUser,null=True,on_delete=models.CASCADE)
	symbol = models.ForeignKey(SymbolInfo,null=True,on_delete=models.CASCADE)
	orderId = models.IntegerField(primary_key=True)
	clientOrderId = models.CharField(max_length=100) #自定义订单id
	price = models.FloatField() #叫价单价
	origQty = models.FloatField() #数量
	executedQty = models.FloatField() #成交数量
	status = models.CharField(max_length=100)
	order_type = models.CharField(max_length=100,default='') #订单类型
	side = models.CharField(max_length=100) #卖卖方
	time = models.DateTimeField() #下单时间
	isWorking =models.BooleanField(default=True)
	order_price = models.FloatField(default=0) #总价（price × origQty）

	q_trading = models.ForeignKey(Qtrading,null=True,on_delete=models.CASCADE)
	parent_order = models.CharField(max_length=100,null=True)
	alter_time = models.DateTimeField(auto_now=True)
class CancelStandbyOrders(models.Model):
	orderid = models.ForeignKey(Order,on_delete=models.CASCADE)


#所有交易
class Trade(models.Model):
	trade_id = models.IntegerField(primary_key=True) #交易id
	account = models.ForeignKey(ReUser,null=True,on_delete=models.CASCADE)
	order = models.ForeignKey(Order,on_delete=models.CASCADE) 
	price = models.FloatField() #交易价格
	qty = models.FloatField() #交易数量
	#bass_usdt_price = models.FloatField()
	commission = models.FloatField() #手续费币消耗数量
	commissionAsset = models.CharField(max_length=100,) #手续费币种
	#bass_commission_price = models.FloatField(null=True,default=0)
	#executed_commission_price = models.FloatField(null=True,default=0)
	time = models.DateTimeField() #交易时间
	isbuyer = models.BooleanField() #是否为买方
	isMaker = models.BooleanField(default=True)
	isBestMatch = models.BooleanField(default=True)
	executed_price = models.FloatField() #交易总价（= price × qty）
	q_trading = models.ForeignKey(Qtrading,null=True,on_delete=models.CASCADE)
