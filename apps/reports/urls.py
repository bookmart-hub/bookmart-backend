from django.urls import path

from apps.reports.views import ReportDetailView, ReportListView, ReportMyListView

urlpatterns = [
    # User: POST /reports/  |  Admin: GET /reports/
    path("reports/", ReportListView.as_view(), name="report-list"),
    # User: GET /reports/me/
    path("reports/me/", ReportMyListView.as_view(), name="report-my-list"),
    # Admin: GET/PATCH /reports/{id}/
    path("reports/<int:pk>/", ReportDetailView.as_view(), name="report-detail"),
]

