from django.urls import path
from . import views

app_name = 'surveys'

urlpatterns = [
    path('dashboard/', views.surveyor_dashboard, name='surveyor_dashboard'),
    path('', views.survey_list, name='list'),
    path('assign/', views.survey_assign, name='assign'),
    path('<int:pk>/', views.survey_detail, name='detail'),
]
