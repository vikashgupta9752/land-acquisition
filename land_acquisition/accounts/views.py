from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from land_records.models import Landowner, LandRecord
from objections.models import Objection
from projects.models import AcquisitionProject, Department
from surveys.models import SurveyAssignment
from .decorators import get_user_role, log_audit, role_required
from .forms import AdminUserCreateForm, AdminUserEditForm, CitizenRegistrationForm
from .models import AuditLog, UserProfile


def login_view(request):
    """Authenticate user and redirect to their role-specific dashboard."""
    if request.user.is_authenticated:
        return redirect('accounts:dashboard_redirect')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if not user.is_active:
                messages.error(request, 'Your account has been deactivated. Contact the administrator.')
            else:
                login(request, user)
                log_audit(request, 'USER_LOGIN', 'User', user.id, f'{user.username} logged in')
                return redirect('accounts:dashboard_redirect')
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'accounts/login.html')


@login_required
def logout_view(request):
    """Log out user and record audit event."""
    log_audit(request, 'USER_LOGOUT', 'User', request.user.id, f'{request.user.username} logged out')
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('accounts:login')


def register_view(request):
    """Public registration for landowners / citizens."""
    if request.user.is_authenticated:
        return redirect('accounts:dashboard_redirect')

    if request.method == 'POST':
        form = CitizenRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            log_audit(request, 'CITIZEN_REGISTERED', 'User', user.id, f'Citizen {user.username} registered')
            messages.success(request, 'Registration successful! You can now log in.')
            return redirect('accounts:login')
    else:
        form = CitizenRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


@login_required
def dashboard_redirect(request):
    """Route each authenticated user to their role-specific panel."""
    role = get_user_role(request.user)
    if role == 'ADMIN':
        return redirect('accounts:admin_dashboard')
    if role == 'OFFICER':
        return redirect('projects:officer_dashboard')
    if role == 'SURVEYOR':
        return redirect('surveys:surveyor_dashboard')
    if role == 'MONITORING':
        return redirect('monitoring:dashboard')
    return redirect('land_records:landowner_dashboard')


@role_required('ADMIN')
def admin_dashboard(request):
    """Panel 1: System-wide administration dashboard."""
    context = {
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
        'total_officers': UserProfile.objects.filter(role='OFFICER').count(),
        'total_surveyors': UserProfile.objects.filter(role='SURVEYOR').count(),
        'total_landowners': Landowner.objects.count(),
        'total_projects': AcquisitionProject.objects.count(),
        'total_land_records': LandRecord.objects.count(),
        'total_area_required': AcquisitionProject.objects.aggregate(s=Sum('required_area_acres'))['s'] or 0,
        'total_objections': Objection.objects.count(),
        'pending_objections': Objection.objects.filter(status__in=['SUBMITTED', 'UNDER_REVIEW']).count(),
        'total_departments': Department.objects.count(),
        'recent_projects': AcquisitionProject.objects.select_related('department', 'assigned_officer')[:6],
        'recent_logs': AuditLog.objects.select_related('user')[:10],
        'recent_objections': Objection.objects.select_related('project', 'landowner')[:5],
    }
    return render(request, 'accounts/admin_dashboard.html', context)


@role_required('ADMIN')
def user_list(request):
    """List and filter all users by role or search query."""
    role_filter = request.GET.get('role', '')
    q = request.GET.get('q', '').strip()
    profiles = UserProfile.objects.select_related('user', 'department').order_by('-created_at')
    if role_filter:
        profiles = profiles.filter(role=role_filter)
    if q:
        profiles = profiles.filter(user__username__icontains=q) | profiles.filter(user__first_name__icontains=q)
    return render(request, 'accounts/user_list.html', {
        'profiles': profiles,
        'role_filter': role_filter,
        'q': q,
    })


@role_required('ADMIN')
def user_create(request):
    """Create a new user account with a specific role."""
    if request.method == 'POST':
        form = AdminUserCreateForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            user = User.objects.create_user(
                username=data['username'],
                email=data['email'],
                password=data['password'],
                first_name=data['first_name'],
                last_name=data['last_name'],
            )
            if data['role'] == 'ADMIN':
                user.is_staff = True
                user.save()
            UserProfile.objects.create(
                user=user,
                role=data['role'],
                phone=data['phone'],
                employee_id=data['employee_id'],
                designation=data['designation'],
                department=data['department'],
                address=data['address'],
            )
            if data['role'] == 'LANDOWNER':
                Landowner.objects.create(
                    user=user,
                    full_name=f"{data['first_name']} {data['last_name']}".strip() or data['username'],
                    phone=data['phone'] or 'N/A',
                    email=data['email'],
                    address=data['address'] or 'N/A',
                    village='N/A',
                    district='N/A',
                )
            log_audit(request, 'USER_CREATED', 'User', user.id, f'Created {user.username} with role {data["role"]}')
            messages.success(request, f'User "{user.username}" created successfully.')
            return redirect('accounts:user_list')
    else:
        form = AdminUserCreateForm()
    return render(request, 'accounts/user_form.html', {'form': form, 'title': 'Create User Account'})


@role_required('ADMIN')
def user_edit(request, user_id):
    """Edit an existing user account."""
    target_user = get_object_or_404(User, pk=user_id)
    profile, _ = UserProfile.objects.get_or_create(user=target_user)
    if request.method == 'POST':
        form = AdminUserEditForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            target_user.first_name = data['first_name']
            target_user.last_name = data['last_name']
            target_user.email = data['email']
            target_user.is_active = data['is_active']
            target_user.save()

            profile.role = data['role']
            profile.phone = data['phone']
            profile.employee_id = data['employee_id']
            profile.designation = data['designation']
            profile.department = data['department']
            profile.address = data['address']
            profile.save()
            log_audit(request, 'USER_UPDATED', 'User', target_user.id, f'Updated user {target_user.username}')
            messages.success(request, f'User "{target_user.username}" updated.')
            return redirect('accounts:user_list')
    else:
        form = AdminUserEditForm(initial={
            'first_name': target_user.first_name,
            'last_name': target_user.last_name,
            'email': target_user.email,
            'is_active': target_user.is_active,
            'role': profile.role,
            'phone': profile.phone,
            'employee_id': profile.employee_id,
            'designation': profile.designation,
            'department': profile.department,
            'address': profile.address,
        })
    return render(request, 'accounts/user_form.html', {
        'form': form,
        'title': f'Edit User: {target_user.username}',
    })


@role_required('ADMIN')
def user_toggle_active(request, user_id):
    """Activate or deactivate a user account."""
    if request.method == 'POST':
        target_user = get_object_or_404(User, pk=user_id)
        if target_user == request.user:
            messages.warning(request, 'You cannot deactivate your own account.')
        else:
            target_user.is_active = not target_user.is_active
            target_user.save()
            state = 'activated' if target_user.is_active else 'deactivated'
            log_audit(request, f'USER_{state.upper()}', 'User', target_user.id, f'{target_user.username} {state}')
            messages.success(request, f'User "{target_user.username}" has been {state}.')
    return redirect('accounts:user_list')


@role_required('ADMIN')
def user_delete(request, user_id):
    """Delete a user account (POST only)."""
    if request.method == 'POST':
        target_user = get_object_or_404(User, pk=user_id)
        if target_user == request.user:
            messages.warning(request, 'You cannot delete your own account.')
        else:
            username = target_user.username
            target_user.delete()
            log_audit(request, 'USER_DELETED', 'User', user_id, f'Deleted user {username}')
            messages.success(request, f'User "{username}" deleted.')
    return redirect('accounts:user_list')


@role_required('ADMIN')
def audit_logs(request):
    """View system-wide audit logs."""
    logs = AuditLog.objects.select_related('user')[:200]
    return render(request, 'accounts/audit_logs.html', {'logs': logs})
