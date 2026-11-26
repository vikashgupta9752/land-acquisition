from django.urls import path
from . import views

app_name = 'monitoring'

urlpatterns = [
    path('dashboard/', views.monitoring_dashboard, name='dashboard'),
    path('reports/', views.reports_hub, name='reports_hub'),
    path('reports/<str:report_type>/<str:fmt>/', views.export_report, name='export_report'),
]
