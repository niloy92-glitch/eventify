from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django.http import HttpRequest, HttpResponse
from .models import Service, ApprovalRequest
from .forms import ServiceForm
from users.services import vendor_base_context, client_base_context


@login_required(login_url="users:login")
@require_GET
def vendor_service_list(request: HttpRequest) -> HttpResponse:
    if getattr(request.user, "role", None) != "vendor":
        return redirect("users:login")

    context = vendor_base_context(request, "services")
    services = Service.objects.filter(vendor=request.user)
    context.update({"services": services, "page_name": "Services"})
    return render(request, "services/vendor/list.html", context)


@login_required(login_url="users:login")
@require_http_methods(["GET", "POST"])
def vendor_service_create(request: HttpRequest) -> HttpResponse:
    if getattr(request.user, "role", None) != "vendor":
        return redirect("users:login")

    if request.method == "POST":
        form = ServiceForm(request.POST)
        if form.is_valid():
            service = form.save(commit=False)
            service.vendor = request.user
            service.is_approved = False
            service.save()
            # create an approval request for admin
            ApprovalRequest.objects.create(request_type="service", service=service, vendor=request.user)
            return redirect(reverse("services:vendor_services"))
    else:
        form = ServiceForm()

    context = vendor_base_context(request, "services")
    context.update({"form": form, "page_name": "Create Service"})
    return render(request, "services/vendor/form.html", context)


@login_required(login_url="users:login")
@require_http_methods(["GET", "POST"])
def vendor_service_edit(request: HttpRequest, pk: int) -> HttpResponse:
    service = get_object_or_404(Service, pk=pk, vendor=request.user)
    if request.method == "POST":
        form = ServiceForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            return redirect(reverse("services:vendor_services"))
    else:
        form = ServiceForm(instance=service)

    context = vendor_base_context(request, "services")
    context.update({"form": form, "service": service, "page_name": "Edit Service"})
    return render(request, "services/vendor/form.html", context)


@login_required(login_url="users:login")
@require_POST
def vendor_service_delete(request: HttpRequest, pk: int) -> HttpResponse:
    service = get_object_or_404(Service, pk=pk, vendor=request.user)
    service.delete()
    return redirect(reverse("services:vendor_services"))


@login_required(login_url="users:login")
@require_GET
def services_home(request: HttpRequest) -> HttpResponse:
    # show all approved services to clients
    context = client_base_context(request, "home")
    services = Service.objects.filter(is_approved=True)
    context.update({"services": services, "page_name": "Home"})
    return render(request, "services/client/home.html", context)
