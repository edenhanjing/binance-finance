from django.urls import path
from . import views

app_name = 'reuser'
urlpatterns = [
    path('login/',views.login,name='login'),
    path('logout/',views.logout,name='logout'),
    path('register/',views.register,name='register'),
    path('activation/',views.activation,name='activation'),
    path('userview/',views.userview,name='userview'),
]