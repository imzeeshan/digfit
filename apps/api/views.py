from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from apps.dashboard.meal_plan_llm import (
    compare_meal_plan_to_logged_meals,
    resolve_meal_plan_for_user_comparison,
)
from apps.dashboard.models import Intervention, MealPlan, SubscriptionPlan, UserMeal, UserSettings, Weight
from apps.subscriptions.models import StripeCustomer

from .serializers import (
    InterventionSerializer,
    MealPlanSerializer,
    StripeCustomerSerializer,
    SubscriptionPlanSerializer,
    UserMealSerializer,
    UserProfileUpdateSerializer,
    UserSerializer,
    UserSettingsSerializer,
    WeightSerializer,
)

User = get_user_model()


def _meal_plan_compare_response(plan, *, extra=None):
    """Run LLM compare and return a DRF Response (503 on Ollama failure)."""
    extra = extra or {}
    try:
        analysis, ctx = compare_meal_plan_to_logged_meals(plan)
    except Exception as exc:
        return Response(
            {'detail': str(exc), 'error': 'llm_compare_failed', **extra},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    stats = ctx.get('stats', {})
    mp = ctx.get('meal_plan', {})
    return Response(
        {
            'meal_plan_id': plan.pk,
            'meal_plan_title': mp.get('title'),
            'analysis': analysis,
            'date_range': {'start': mp.get('start_date'), 'end': mp.get('end_date')},
            **stats,
            **extra,
        }
    )


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """Users — admin can list all; regular users see only themselves."""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return User.objects.all().order_by('-date_joined')
        return User.objects.filter(pk=self.request.user.pk)

    @action(detail=False, methods=['get', 'patch'], url_path='me')
    def me(self, request):
        user = request.user
        if request.method == 'PATCH':
            serializer = UserProfileUpdateSerializer(user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(UserSerializer(user).data)
        return Response(UserSerializer(user).data)


class SubscriptionPlanViewSet(viewsets.ModelViewSet):
    """Subscription plans — read-only for users, full CRUD for admins."""
    serializer_class = SubscriptionPlanSerializer
    lookup_field = 'slug'

    def get_queryset(self):
        if self.request.user.is_staff:
            return SubscriptionPlan.objects.all().order_by('-created_at')
        return SubscriptionPlan.objects.filter(is_active=True).order_by('price')

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        return [IsAdminUser()]


class UserSettingsViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """Current user's settings (notifications). Admin sees all."""
    serializer_class = UserSettingsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return UserSettings.objects.select_related('subscription_plan').all()
        return UserSettings.objects.select_related('subscription_plan').filter(
            user=self.request.user,
        )

    @action(detail=False, methods=['get', 'patch'], url_path='me')
    def me(self, request):
        settings_obj, _ = UserSettings.objects.get_or_create(user=request.user)
        if request.method == 'PATCH':
            serializer = self.get_serializer(settings_obj, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return Response(self.get_serializer(settings_obj).data)


class StripeCustomerViewSet(viewsets.ReadOnlyModelViewSet):
    """Stripe customer records — admin only."""
    serializer_class = StripeCustomerSerializer
    permission_classes = [IsAdminUser]
    queryset = StripeCustomer.objects.select_related('user').all()


class WeightViewSet(viewsets.ModelViewSet):
    """Weight entries — admin sees all; regular users see only their own."""
    serializer_class = WeightSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Weight.objects.select_related('user')
        if self.request.user.is_staff:
            return qs.all()
        return qs.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'], url_path='reminder')
    def reminder(self, request):
        """Check if the current user's weight log is overdue."""
        us, _ = UserSettings.objects.get_or_create(user=request.user)
        reminder = us.get_weight_reminder()
        if reminder:
            reminder['last_logged'] = (
                reminder['last_logged'].isoformat() if reminder['last_logged'] else None
            )
        return Response(reminder or {'overdue': False})


class UserMealViewSet(viewsets.ModelViewSet):
    """User meals (actual meals taken) — admin sees all; regular users see only their own."""
    serializer_class = UserMealSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = UserMeal.objects.select_related('user')
        if self.request.user.is_staff:
            return qs.all()
        return qs.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class MealPlanViewSet(viewsets.ModelViewSet):
    """Meal plans — admin sees all; regular users see only their own.

    Filtering (admin only):
        GET /api/meal-plans/?user=<user_id>

    Lookup by user (admin only):
        GET /api/meal-plans/by-user/<user_id>/

    Compare plan vs logged meals by user (staff: any user; others: own user_id only):
        POST /api/meal-plans/by-user/<user_id>/compare-meals/
        Picks the plan whose dates include today, else the most recent plan by start_date.
    """
    serializer_class = MealPlanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = MealPlan.objects.select_related('user').prefetch_related('entries')
        if self.request.user.is_staff:
            user_id = self.request.query_params.get('user')
            if user_id:
                qs = qs.filter(user_id=user_id)
            return qs
        return qs.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(
        detail=False,
        methods=['post'],
        url_path=r'by-user/(?P<user_id>\d+)/compare-meals',
        permission_classes=[IsAuthenticated],
    )
    def compare_meals_by_user(self, request, user_id=None):
        """Compare the user's resolved meal plan to their UserMeals (same LLM as compare-meals on a plan)."""
        if not request.user.is_staff and str(request.user.pk) != str(user_id):
            return Response(
                {'detail': 'You may only run this comparison for your own user id.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        target = get_object_or_404(User, pk=user_id)
        plan, selection = resolve_meal_plan_for_user_comparison(target)
        if plan is None:
            return Response(
                {
                    'detail': 'No meal plan found for this user.',
                    'error': 'no_meal_plan',
                    'user_id': int(user_id),
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        return _meal_plan_compare_response(
            plan,
            extra={'user_id': int(user_id), 'meal_plan_selection': selection},
        )

    @action(detail=False, methods=['get'], url_path=r'by-user/(?P<user_id>\d+)',
            permission_classes=[IsAdminUser])
    def by_user(self, request, user_id=None):
        """Return all meal plans for a specific user (admin only)."""
        plans = MealPlan.objects.for_user(user_id)
        serializer = self.get_serializer(plans, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='compare-meals')
    def compare_meals(self, request, pk=None):
        """Compare planned meal entries with UserMeals logged in the plan date window (Ollama)."""
        plan = self.get_object()
        return _meal_plan_compare_response(plan)


class InterventionViewSet(viewsets.ModelViewSet):
    """Interventions — admin sees all; regular users see only their own."""
    serializer_class = InterventionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Intervention.objects.select_related('user')
        if self.request.user.is_staff:
            return qs.all()
        return qs.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
