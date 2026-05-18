from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='home'),
    path('profile/', views.profile, name='profile'),
    path('settings/', views.settings, name='settings'),
    path('notifications/<int:pk>/dismiss/', views.notification_dismiss, name='notification_dismiss'),
    path('settings/generate-api-key/', views.generate_api_key, name='generate_api_key'),
    path('subscription/plans/', views.subscription_plans, name='subscription_plans'),
    path('subscription/plans/<slug:plan_slug>/subscribe/', views.subscribe_to_plan, name='subscribe_to_plan'),
    path('subscription/cancel/', views.cancel_subscription, name='cancel_subscription'),
    path('subscription/trial/', views.start_trial, name='start_trial'),
    path('profile/upload-pic/', views.upload_profile_pic, name='upload_profile_pic'),
    path('profile/remove-pic/', views.remove_profile_pic, name='remove_profile_pic'),
    # Weight (own entries for regular users; staff see all)
    path('weight/', views.weight_list, name='weight_list'),
    path('weight/new/', views.weight_create, name='weight_create'),
    path('weight/<int:pk>/', views.weight_detail, name='weight_detail'),
    path('weight/<int:pk>/edit/', views.weight_edit, name='weight_edit'),
    path('weight/<int:pk>/delete/', views.weight_delete, name='weight_delete'),
    # User Management CRUD (admin only)
    path('users/', views.user_list, name='user_list'),
    path('users/new/', views.user_create, name='user_create'),
    path('users/<int:pk>/', views.user_detail, name='user_detail'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),
    # Meal Plan CRUD (admin only)
    path('meals/', views.meal_list, name='meal_list'),
    path('meals/new/', views.meal_create, name='meal_create'),
    path('meals/<int:pk>/', views.meal_detail, name='meal_detail'),
    path('meals/<int:pk>/edit/', views.meal_edit, name='meal_edit'),
    path('meals/<int:pk>/delete/', views.meal_delete, name='meal_delete'),
    # Meal Entry CRUD (admin only)
    path('meals/<int:meal_pk>/entries/new/', views.entry_create, name='entry_create'),
    path('meals/entries/<int:pk>/edit/', views.entry_edit, name='entry_edit'),
    path('meals/entries/<int:pk>/delete/', views.entry_delete, name='entry_delete'),
    # User Meal CRUD (own meals for regular users; staff see all)
    path('user-meals/', views.usermeal_list, name='usermeal_list'),
    path('user-meals/new/', views.usermeal_create, name='usermeal_create'),
    path('user-meals/<int:pk>/', views.usermeal_detail, name='usermeal_detail'),
    path('user-meals/<int:pk>/edit/', views.usermeal_edit, name='usermeal_edit'),
    path('user-meals/<int:pk>/delete/', views.usermeal_delete, name='usermeal_delete'),
    # Audit Logs (admin only)
    path('audit-logs/', views.audit_log_list, name='audit_log_list'),
    # Intervention CRUD (admin only)
    path('interventions/', views.intervention_list, name='intervention_list'),
    path('interventions/new/', views.intervention_create, name='intervention_create'),
    path('interventions/<int:pk>/', views.intervention_detail, name='intervention_detail'),
    path('interventions/<int:pk>/edit/', views.intervention_edit, name='intervention_edit'),
    path('interventions/<int:pk>/delete/', views.intervention_delete, name='intervention_delete'),
]
