from django.contrib import admin
from django.urls import path
from gscrag import views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('ask/', views.ask, name='ask'),
    path('problem-solver/', views.problem_solver, name='problem_solver'),
    path('workflows/', views.workflows, name='workflows'),
    path('learning/', views.learning, name='learning'),
    path('practice-lab/', views.practice_lab, name='practice_lab'),
    path('resources/', views.resources, name='resources'),
]
