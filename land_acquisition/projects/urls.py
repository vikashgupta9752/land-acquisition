from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    path('officer-dashboard/', views.officer_dashboard, name='officer_dashboard'),
    path('', views.project_list, name='project_list'),
    path('create/', views.project_create, name='project_create'),
    path('<int:pk>/', views.project_detail, name='project_detail'),
    path('<int:pk>/edit/', views.project_edit, name='project_edit'),
    path('<int:pk>/status/', views.project_update_status, name='project_update_status'),
    path('<int:pk>/upload-document/', views.project_upload_document, name='project_upload_document'),
    path('<int:pk>/publish-notification/', views.publish_notification, name='publish_notification'),
    path('departments/', views.department_list, name='department_list'),
]
