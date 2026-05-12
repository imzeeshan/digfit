from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('users', views.UserViewSet, basename='user')
router.register('plans', views.SubscriptionPlanViewSet, basename='plan')
router.register('settings', views.UserSettingsViewSet, basename='settings')
router.register('stripe-customers', views.StripeCustomerViewSet, basename='stripe-customer')
router.register('weights', views.WeightViewSet, basename='weight')
router.register('meal-plans', views.MealPlanViewSet, basename='meal-plan')
router.register('user-meals', views.UserMealViewSet, basename='user-meal')
router.register('interventions', views.InterventionViewSet, basename='intervention')

urlpatterns = router.urls
