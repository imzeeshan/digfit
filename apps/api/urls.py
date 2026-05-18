from django.urls import path
from rest_framework.routers import DefaultRouter

from . import auth_views, views


class DigFitRouter(DefaultRouter):
    APIRootView = views.DigFitAPIRootView


router = DigFitRouter()
router.register('users', views.UserViewSet, basename='user')
router.register('plans', views.SubscriptionPlanViewSet, basename='plan')
router.register('settings', views.UserSettingsViewSet, basename='settings')
router.register('stripe-customers', views.StripeCustomerViewSet, basename='stripe-customer')
router.register('notifications', views.NotificationViewSet, basename='notification')
router.register('weights', views.WeightViewSet, basename='weight')
router.register('meal-plans', views.MealPlanViewSet, basename='meal-plan')
router.register('user-meals', views.UserMealViewSet, basename='user-meal')
router.register('interventions', views.InterventionViewSet, basename='intervention')

urlpatterns = [
    path('auth/login/', auth_views.LoginView.as_view(), name='api-auth-login'),
    path('auth/logout/', auth_views.LogoutView.as_view(), name='api-auth-logout'),
] + router.urls
