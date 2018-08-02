from django.urls import path
from . import views

app_name = 'qtrading'
urlpatterns = [
    path('',views.qtrading,name='qtrading'),
    path('create_qtrading/',views.create_qtrading,name='create_qtrading'),
    path('qtrading_info/<slug:slug>/',views.qtrading_info,name='qtrading_info'),

    path('trade/',views.trade,name='trade'),

    path('buy_or_sell/',views.buy_or_sell,name='buy_or_sell'),
    path('cancel_order/',views.cancel_order,name='cancel_order'),
    path('ceshi/',views.ceshi,name='ceshi'),
] 