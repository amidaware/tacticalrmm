from django.urls import path

from . import views

urlpatterns = [
    # Firewall settings
    path("settings/", views.GetEditFirewallSettings.as_view()),
    # IP rules
    path("ip-rules/", views.GetAddFirewallIPRules.as_view()),
    path("ip-rules/<int:pk>/", views.UpdateDeleteFirewallIPRule.as_view()),
    path("ip-rules/<int:pk>/toggle/", views.ToggleFirewallIPRule.as_view()),
    # Country rules
    path("country-rules/", views.GetAddFirewallCountryRules.as_view()),
    path("country-rules/<int:pk>/", views.UpdateDeleteFirewallCountryRule.as_view()),
    path(
        "country-rules/<int:pk>/toggle/", views.ToggleFirewallCountryRule.as_view()
    ),
    path("countries/", views.common_countries),
    # GeoIP lookup
    path("geoip/lookup/", views.geoip_lookup),
    # Firewall logs
    path("logs/", views.GetFirewallLogs.as_view()),
    path("logs/analytics/", views.firewall_log_analytics),
    # Fail2Ban
    path("fail2ban/status/", views.Fail2BanStatus.as_view()),
    path("fail2ban/unban/", views.fail2ban_unban_ip),
    path("fail2ban/unban-all/", views.fail2ban_unban_all),
    path("fail2ban/check-ip/", views.fail2ban_check_ip),
    path("fail2ban/start/", views.fail2ban_start),
    path("fail2ban/install/", views.fail2ban_install),
]
