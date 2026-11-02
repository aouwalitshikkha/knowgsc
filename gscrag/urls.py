from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from core import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("ckeditor/", include("ckeditor_uploader.urls")),
    path("", views.home, name="home"),
    path("ask/", views.ask, name="ask"),
    path("ask/answer/", views.ask_answer, name="ask_answer"),
    path("problem-solver/", views.problem_solver, name="problem_solver"),
    path(
        "problem-solver/report/<uuid:token>/",
        views.diagnostic_report,
        name="diagnostic_report",
    ),
    path("workflows/", views.workflows, name="workflows"),
    path(
        "workflows/<slug:slug>/",
        views.workflow_detail,
        name="workflow_detail",
    ),
    path("learning/", views.learning, name="learning"),
    path("learning/<slug:slug>/", views.lesson_detail, name="lesson_detail"),
    path("practice-lab/", views.practice_lab, name="practice_lab"),
    path(
        "practice-lab/<slug:slug>/",
        views.practice_scenario_detail,
        name="practice_scenario_detail",
    ),
    path("resources/", views.resources, name="resources"),
    path("api/sessions/", views.session_create, name="session_create"),
    path("api/sessions/<uuid:token>/", views.session_update, name="session_update"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
