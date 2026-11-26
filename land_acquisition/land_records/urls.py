from django.urls import path
from . import views

app_name = 'land_records'

urlpatterns = [
    path('my-dashboard/', views.landowner_dashboard, name='landowner_dashboard'),
    path('', views.land_record_list, name='list'),
    path('create/', views.land_record_create, name='create'),
    path('<int:pk>/', views.land_record_detail, name='detail'),
    path('<int:pk>/edit/', views.land_record_edit, name='edit'),
    path('<int:pk>/possession/', views.record_possession, name='record_possession'),
    path('landowners/', views.landowner_list, name='landowner_list'),
    path('landowners/create/', views.landowner_create, name='landowner_create'),
]
