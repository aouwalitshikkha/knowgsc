from django.shortcuts import render


def home(request):
    return render(request, 'home.html')


def ask(request):
    return render(request, 'ask.html')


def problem_solver(request):
    return render(request, 'problem-solver.html')


def workflows(request):
    return render(request, 'workflows.html')


def learning(request):
    return render(request, 'learning.html')


def practice_lab(request):
    return render(request, 'practice-lab.html')


def resources(request):
    return render(request, 'resources.html')
