from django.db import models
from reuser.models import ReUser
# Create your models here.

#币种信息
class Asset(models.Model):
	name = models.CharField(max_length=100,primary_key=True)
	full_name = models.CharField(max_length=100)
	price = models.FloatField()
	change_24h = models.FloatField(null=True, blank=True) #价格涨幅
	market_cap = models.FloatField() #总市值
	#total_issued = models.CharField(max_length=100) #总发行
	#quantity_of_circulation  = models.CharField(max_length=100) #市场流通量
	#issue_price = models.FloatField(null=True, blank=True) #发行价格
	#issue_priceChangePercent = models.FloatField(null=True, blank=True)  #发行价格变动百分比
	#issue_date = models.DateTimeField(null=True, blank=True) #发行日期
	#website = models.URLField(null=True) #网址
	#introduce = models.TextField() 
	logo = models.ImageField(upload_to='AssetLogo',blank=True,default='AssetLogo/default/default.png') 
	data_update_time = models.DateTimeField(auto_now=True)
	def __str__(self):
		return self.asset_name

#充值提取明细
class DepositDetails(models.Model):
	account = models.ForeignKey(ReUser,null=True,on_delete=models.CASCADE)
	amount = models.FloatField() #量
	address = models.CharField(max_length=100) #地址
	addressTag = models.CharField(null=True,max_length=100)
	txId = models.CharField(max_length=100,primary_key=True)
	asset = models.ForeignKey(Asset,null=True,on_delete=models.CASCADE)
	status = models.BooleanField(default=False)
	insertTime = models.DateTimeField(auto_now_add=True)

#市场信息
class SymbolInfo(models.Model):
	symbol = models.CharField(max_length=100,primary_key=True)
	baseAssetPrecision = models.SmallIntegerField()
	quotePrecision = models.SmallIntegerField()
	
	baseAsset = models.CharField(max_length=100)
	quoteAsset = models.CharField(max_length=100)
	
	minPrice = models.FloatField()
	maxPrice = models.FloatField()
	tickSize = models.FloatField() #价格最小步数
	minQty = models.FloatField()
	maxQty = models.FloatField()
	stepSize =models.FloatField() #数量最小步数

	status = models.CharField(max_length=100)
	#serverTime = models.DateTimeField()
	#price = models.FloatField(null=True)
	#volatility = models.FloatField(null=True,default=0)
	data_update_time = models.DateTimeField(auto_now=True)

#用户资产情况
class AccountInfo(models.Model):
	account = models.ForeignKey(ReUser,null=True,on_delete=models.CASCADE)
	asset = models.ForeignKey(Asset,null=True,on_delete=models.CASCADE) 
	total = models.FloatField(null=True) #总持有量
	free = models.FloatField(null=True)	#可使用
	locked = models.FloatField(null=True) #冻结
	
	cost_price = models.FloatField(null=True,default=0) #成本单价
	cost  = models.FloatField(null=True,default=0) #成本
	market_value = models.FloatField(null=True,default=0) #当前市值
	profit_and_loss = models.FloatField(null=True,default=0) #变动
	p_a_l_percent = models.FloatField(null=True,default=0) #变动百分百
	
	data_update_time = models.DateTimeField(auto_now=True)	

class Ticker24(models.Model):
	symbol = models.CharField(max_length=10,null=True)
	askPrice = models.FloatField()
	bidPrice = models.FloatField()
	askQty = models.FloatField()
	bidQty = models.FloatField()
	lastQty = models.FloatField()

	firstId = models.CharField(max_length=10)
	lastId = models.CharField(max_length=10)
	
	openPrice = models.FloatField()
	lowPrice = models.FloatField()
	highPrice = models.FloatField()
	lastPrice = models.FloatField()

	volume = models.FloatField()
	quoteVolume = models.FloatField()

	priceChange = models.FloatField()
	priceChangePercent = models.FloatField()

	count = models.FloatField()
	prevClosePrice = models.FloatField()
	weightedAvgPrice = models.FloatField() #加权平均价格

	openTime = models.DateTimeField()
	closeTime = models.DateTimeField()


