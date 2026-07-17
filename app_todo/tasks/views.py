from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .forms import TaskForm
from .models import Task

def role_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(request, *args, **kwargs):
            if request.user.groups.filter(name__in=roles).exists():
                return view(request, *args, **kwargs)
            raise PermissionDenied("Você não tem acesso ao To-Do List.")
        return wrapped
    return decorator

def home(request):
    if not request.user.is_authenticated:
        return render(request, "tasks/landing.html")
    if not request.user.groups.filter(name__in=["admin", "todo_user"]).exists():
        raise PermissionDenied("Você não tem acesso ao To-Do List.")
    tasks = Task.objects.filter(owner=request.user)
    return render(request, "tasks/home.html", {"tasks": tasks, "form": TaskForm()})


@require_POST
@role_required("admin", "todo_user")
def create_task(request):
    form = TaskForm(request.POST)
    if form.is_valid():
        task = form.save(commit=False)
        task.owner = request.user
        task.save()
    return redirect("home")


@require_POST
@role_required("admin", "todo_user")
def toggle_task(request, pk):
    task = get_object_or_404(Task, pk=pk, owner=request.user)
    task.completed = not task.completed
    task.save(update_fields=["completed"])
    return redirect("home")


@require_POST
@role_required("admin", "todo_user")
def delete_task(request, pk):
    get_object_or_404(Task, pk=pk, owner=request.user).delete()
    return redirect("home")


def error_403(request, exception=None):
    return render(request, "tasks/403.html", status=403)
