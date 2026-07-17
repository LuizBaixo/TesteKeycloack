import calendar
from datetime import date
from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from .forms import AppointmentForm
from .models import Appointment

def role_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(request, *args, **kwargs):
            if request.user.groups.filter(name__in=roles).exists():
                return view(request, *args, **kwargs)
            raise PermissionDenied("Você não tem acesso à Agenda.")
        return wrapped
    return decorator

def home(request):
    if not request.user.is_authenticated:
        return render(request, "core/landing.html")
    if not request.user.groups.filter(name__in=["admin", "agenda_user"]).exists():
        raise PermissionDenied("Você não tem acesso à Agenda.")
    try:
        displayed_month = date.fromisoformat(f"{request.GET.get('month')}-01")
    except (TypeError, ValueError):
        displayed_month = timezone.localdate().replace(day=1)

    month_start = displayed_month.replace(day=1)
    if month_start.month == 12:
        next_month = month_start.replace(year=month_start.year + 1, month=1)
    else:
        next_month = month_start.replace(month=month_start.month + 1)
    if month_start.month == 1:
        previous_month = month_start.replace(year=month_start.year - 1, month=12)
    else:
        previous_month = month_start.replace(month=month_start.month - 1)

    appointments = list(Appointment.objects.filter(owner=request.user, scheduled_at__date__gte=month_start, scheduled_at__date__lt=next_month))
    appointments_by_day = {}
    for appointment in appointments:
        appointments_by_day.setdefault(timezone.localtime(appointment.scheduled_at).date(), []).append(appointment)
    calendar_weeks = [[{
        "date": day,
        "in_month": day.month == month_start.month,
        "appointments": appointments_by_day.get(day, []),
    } for day in week] for week in calendar.Calendar(firstweekday=0).monthdatescalendar(month_start.year, month_start.month)]
    return render(request, "core/home.html", {
        "appointments": appointments,
        "calendar_weeks": calendar_weeks,
        "displayed_month": month_start,
        "previous_month": previous_month,
        "next_month": next_month,
        "form": AppointmentForm(),
    })


@require_POST
@role_required("admin", "agenda_user")
def create_appointment(request):
    form = AppointmentForm(request.POST)
    if form.is_valid():
        appointment = form.save(commit=False)
        appointment.owner = request.user
        appointment.save()
    return redirect("home")


@require_POST
@role_required("admin", "agenda_user")
def delete_appointment(request, pk):
    get_object_or_404(Appointment, pk=pk, owner=request.user).delete()
    return redirect("home")


def error_403(request, exception=None):
    return render(request, "core/403.html", status=403)
