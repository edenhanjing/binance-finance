from django.urls import path
from . import views

app_name = 'currencies'
urlpatterns = [
    path('',views.home,name='home'),
    
    path('asset/',views.asset_home,name='asset_home'),
    path('asset/<slug:slug>/',views.asset,name='asset'),

    path('symbol/',views.symbol_home,name='symbol_home'),
    path('symbol/<slug:slug>/',views.symbol,name='symbol'),

]