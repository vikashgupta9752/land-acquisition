from django.urls import path
from . import views

app_name = 'objections'

urlpatterns = [
    path('', views.objection_list, name='list'),
    path('submit/', views.objection_submit, name='submit'),
    path('<int:pk>/', views.objection_detail, name='detail'),
]
