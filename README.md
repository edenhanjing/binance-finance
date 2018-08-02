# binance-finance
对接币安，量化操作。
binance-finance 使用python-binance对接币安api接口，做量化交易。

ubuntu16 python3.5

# 启动 
virtualenv创建虚拟环境 启动虚拟环境，安装所需库 pip install -r requirements.txt mysql创建数据库，
修改settings.py的数据库配置，
同步数据库，创建用户（添加币安api秘钥、秘钥密码，
启动celery服务 celery -A finance worker -c5 启动django服务
