from django.urls import path
from . import views

app_name = 'compensation'

urlpatterns = [
    path('', views.compensation_list, name='list'),
    path('calculate/', views.compensation_calculate, name='calculate'),
    path('<int:pk>/', views.compensation_detail, name='detail'),
    path('<int:pk>/approve/', views.compensation_approve, name='approve'),
    path('<int:comp_pk>/payment/', views.payment_record, name='payment_record'),
]
