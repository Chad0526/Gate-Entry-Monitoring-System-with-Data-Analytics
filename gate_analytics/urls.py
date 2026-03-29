"""Gate Analytics URL Configuration

Gate Entry Monitoring & Data Analytics - City College of Bayawan.
For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.contrib.staticfiles.urls import static, staticfiles_urlpatterns

from .views import (
    dashboard,
    dashboard_stats_api,
    login_page,
    login_probe,
    ngrok_tunnel_help,
    logout_page,
    register_page,
    user_list,
    profile_edit,
    staff_personnel_complete_profile,
    account_settings,
    preferences_view,
    privacy_policy,
    terms_and_conditions,
    health_check,
)
from . import settings
from .forms import PasswordResetFormEmailMustExist

admin.site.site_header = "Gate Entry Monitoring & Data Analytics - Admin"
admin.site.site_title = "CCB Gate & Attendance Analytics"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check),
    path('ping/', health_check),
    path('login-probe/', login_probe, name='login-probe'),
    path('ngrok-help/', ngrok_tunnel_help, name='ngrok-tunnel-help'),
    # Login at / and /login/ (single name 'login' → /login/ for reverse() and LOGIN_URL)
    path('', login_page),
    path('login/', login_page, name='login'),
    path('dashboard/', dashboard, name='dashboard'),
    path('dashboard/stats/', dashboard_stats_api, name='dashboard-stats-api'),
    path('register/', register_page, name='register'),
    path('logout/', logout_page, name='logout'),
    path('users/', user_list, name='user-list'),
    path('profile/', profile_edit, name='profile-edit'),
    path('profile/account/', account_settings, name='account-settings'),
    path('profile/preferences/', preferences_view, name='preferences'),
    path('profile/complete/', staff_personnel_complete_profile, name='staff-personnel-complete-profile'),
    path('privacy/', privacy_policy, name='privacy-policy'),
    path('terms/', terms_and_conditions, name='terms'),
    path('gate/', include('gate.gate_urls')),
    path('gate/', include('gate.urls')),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path('captcha/', include('captcha.urls')),
    # Password reset / change (do not include django.contrib.auth.urls — it duplicates login/logout
    # and overwrites the 'login' name with Django's LoginView, which breaks our custom login page)
    path(
        'password_reset/',
        auth_views.PasswordResetView.as_view(form_class=PasswordResetFormEmailMustExist),
        name='password_reset',
    ),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('password_change/', auth_views.PasswordChangeView.as_view(), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(), name='password_change_done'),
]

urlpatterns += staticfiles_urlpatterns()
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Custom error pages (set DEBUG=False in production to see these)
handler404 = 'gate_analytics.views.custom_page_not_found_view'
handler500 = 'gate_analytics.views.custom_server_error_view'