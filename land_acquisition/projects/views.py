import json
from django.contrib import messages
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from accounts.decorators import get_user_role, log_audit, role_required
from compensation.models import Compensation, Payment
from land_records.models import LandRecord
from notifications.utils import create_notification, record_status_change
from objections.models import Objection
from surveys.models import SurveyAssignment
from .forms import (
    AcquisitionProjectForm,
    DepartmentForm,
    DocumentUploadForm,
    OfficialNotificationForm,
    ProjectStatusExceptionForm,
)
from .models import AcquisitionProject, Department, Document


@role_required('OFFICER', 'ADMIN')
def officer_dashboard(request):
    """Panel 2: Government Officer Dashboard."""
    role = get_user_role(request.user)
    if role == 'ADMIN':
        projects_qs = AcquisitionProject.objects.all()
    else:
        projects_qs = AcquisitionProject.objects.filter(
            Q(assigned_officer=request.user) | Q(created_by=request.user)
        )

    land_qs = LandRecord.objects.filter(project__in=projects_qs)
    survey_qs = SurveyAssignment.objects.filter(project__in=projects_qs)
    objection_qs = Objection.objects.filter(project__in=projects_qs)
    comp_qs = Compensation.objects.filter(project__in=projects_qs)

    context = {
        'total_projects': projects_qs.count(),
        'total_land_records': land_qs.count(),
        'pending_surveys': survey_qs.filter(status__in=['PENDING', 'ASSIGNED', 'IN_PROGRESS']).count(),
        'submitted_surveys': survey_qs.filter(status='SUBMITTED').count(),
        'pending_objections': objection_qs.filter(status__in=['SUBMITTED', 'UNDER_REVIEW']).count(),
        'total_proposed_comp': comp_qs.aggregate(s=Sum('proposed_compensation'))['s'] or 0,
        'projects': projects_qs.select_related('department', 'assigned_officer')[:8],
        'recent_surveys': survey_qs.select_related('land_record', 'surveyor').filter(status='SUBMITTED')[:5],
        'recent_objections': objection_qs.select_related('land_record', 'landowner').filter(
            status__in=['SUBMITTED', 'UNDER_REVIEW']
        )[:5],
    }
    return render(request, 'projects/officer_dashboard.html', context)


@role_required('ADMIN', 'OFFICER', 'MONITORING')
def project_list(request):
    """Searchable and filterable list of acquisition projects."""
    role = get_user_role(request.user)
    projects_qs = AcquisitionProject.objects.select_related('department', 'assigned_officer')
    if role == 'OFFICER':
        projects_qs = projects_qs.filter(Q(assigned_officer=request.user) | Q(created_by=request.user))

    q = request.GET.get('q', '').strip()
    district = request.GET.get('district', '').strip()
    status = request.GET.get('status', '').strip()
    department_id = request.GET.get('department', '').strip()

    if q:
        projects_qs = projects_qs.filter(
            Q(project_code__icontains=q) | Q(name__icontains=q) | Q(village__icontains=q)
        )
    if district:
        projects_qs = projects_qs.filter(district__icontains=district)
    if status:
        projects_qs = projects_qs.filter(status=status)
    if department_id:
        projects_qs = projects_qs.filter(department_id=department_id)

    return render(request, 'projects/project_list.html', {
        'projects': projects_qs,
        'departments': Department.objects.all(),
        'q': q,
        'district': district,
        'status': status,
        'department_id': department_id,
    })


@role_required('ADMIN', 'OFFICER')
def project_create(request):
    """Step 1: Create a new land acquisition project."""
    if request.method == 'POST':
        form = AcquisitionProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.created_by = request.user
            if not project.assigned_officer and get_user_role(request.user) == 'OFFICER':
                project.assigned_officer = request.user
            project.save()
            record_status_change(
                project=project,
                new_status='PROJECT_CREATED',
                updated_by=request.user,
                remarks='Acquisition project initialized.',
            )
            log_audit(request, 'PROJECT_CREATED', 'AcquisitionProject', project.id, project.project_code)
            messages.success(request, f'Project "{project.name}" created successfully.')
            return redirect('projects:project_detail', pk=project.pk)
    else:
        initial = {}
        if get_user_role(request.user) == 'OFFICER':
            initial['assigned_officer'] = request.user
        form = AcquisitionProjectForm(initial=initial)

    return render(request, 'projects/project_form.html', {'form': form, 'title': 'Create Acquisition Project'})


@role_required('ADMIN', 'OFFICER')
def project_edit(request, pk):
    """Edit an existing acquisition project."""
    project = get_object_or_404(AcquisitionProject, pk=pk)
    if request.method == 'POST':
        form = AcquisitionProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            log_audit(request, 'PROJECT_UPDATED', 'AcquisitionProject', project.id, project.project_code)
            messages.success(request, f'Project "{project.name}" updated.')
            return redirect('projects:project_detail', pk=project.pk)
    else:
        form = AcquisitionProjectForm(instance=project)
    return render(request, 'projects/project_form.html', {
        'form': form,
        'title': f'Edit Project: {project.project_code}',
        'project': project,
    })


@role_required('ADMIN', 'OFFICER', 'MONITORING', 'SURVEYOR')
def project_detail(request, pk):
    """Detailed view of a project with map markers, land parcels, status history, and documents."""
    project = get_object_or_404(
        AcquisitionProject.objects.select_related('department', 'assigned_officer'), pk=pk
    )
    land_records = project.land_records.select_related('landowner')
    status_history = project.status_history.select_related('updated_by', 'land_record')[:25]
    documents = project.documents.select_related('uploaded_by')
    notifications = project.notifications.filter(is_official_notice=True)

    # Prepare map markers JSON for Leaflet
    parcel_markers = []
    for lr in land_records:
        if lr.latitude is not None and lr.longitude is not None:
            if lr.is_acquired:
                category = 'acquired'
            elif lr.acquisition_status in ('SURVEY_COMPLETED', 'SURVEY_VERIFIED', 'COMPENSATION_PROPOSED', 'COMPENSATION_APPROVED'):
                category = 'surveyed'
            else:
                category = 'pending'
            parcel_markers.append({
                'id': lr.id,
                'survey_number': lr.survey_number,
                'plot_number': lr.plot_number,
                'village': lr.village,
                'district': lr.district,
                'area_acres': float(lr.area_acres),
                'owner': lr.landowner.full_name,
                'status': lr.get_acquisition_status_display(),
                'category': category,
                'lat': float(lr.latitude),
                'lng': float(lr.longitude),
                'geojson': lr.boundary_geojson or '',
            })

    status_form = ProjectStatusExceptionForm(initial={'status': project.status})
    doc_form = DocumentUploadForm()

    return render(request, 'projects/project_detail.html', {
        'project': project,
        'land_records': land_records,
        'status_history': status_history,
        'documents': documents,
        'official_notices': notifications,
        'parcel_markers_json': json.dumps(parcel_markers),
        'status_form': status_form,
        'doc_form': doc_form,
    })


@role_required('ADMIN', 'OFFICER')
def project_update_status(request, pk):
    """Update project status or log an authorized workflow exception."""
    project = get_object_or_404(AcquisitionProject, pk=pk)
    if request.method == 'POST':
        form = ProjectStatusExceptionForm(request.POST)
        if form.is_valid():
            new_status = form.cleaned_data['status']
            remarks = form.cleaned_data['remarks']
            is_exception = form.cleaned_data['is_exception']
            exception_reason = form.cleaned_data['exception_reason']
            record_status_change(
                project=project,
                new_status=new_status,
                updated_by=request.user,
                remarks=remarks,
                is_exception=is_exception,
                exception_reason=exception_reason,
            )
            log_audit(request, 'PROJECT_STATUS_UPDATED', 'AcquisitionProject', project.id, f'Status -> {new_status}')
            messages.success(request, f'Project status updated to {project.get_status_display()}.')
    return redirect('projects:project_detail', pk=project.pk)


@role_required('ADMIN', 'OFFICER')
def project_upload_document(request, pk):
    """Attach an official document to a project."""
    project = get_object_or_404(AcquisitionProject, pk=pk)
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.project = project
            doc.uploaded_by = request.user
            doc.save()
            log_audit(request, 'DOCUMENT_UPLOADED', 'Document', doc.id, f'{doc.title} on {project.project_code}')
            messages.success(request, 'Document uploaded successfully.')
        else:
            messages.error(request, f'Upload failed: {form.errors.as_text()}')
    return redirect('projects:project_detail', pk=project.pk)


@role_required('ADMIN', 'OFFICER')
def publish_notification(request, pk):
    """Step 7: Publish an official acquisition notification to all affected landowners."""
    project = get_object_or_404(AcquisitionProject, pk=pk)
    if request.method == 'POST':
        form = OfficialNotificationForm(request.POST, request.FILES)
        if form.is_valid():
            base_notice = form.save(commit=False)
            affected_landowners = (
                project.land_records.select_related('landowner__user')
                .values_list('landowner__user', flat=True)
                .distinct()
            )
            count = 0
            # Always create a project-level official notice record
            create_notification(
                recipient=None,
                title=base_notice.title,
                message=base_notice.message,
                notification_type='OFFICIAL_NOTICE',
                project=project,
                is_official_notice=True,
                notice_number=base_notice.notice_number,
                attachment=base_notice.attachment,
                created_by=request.user,
            )
            for user_id in affected_landowners:
                if user_id:
                    from django.contrib.auth.models import User
                    recipient = User.objects.filter(pk=user_id).first()
                    if recipient:
                        create_notification(
                            recipient=recipient,
                            title=f"[{project.project_code}] {base_notice.title}",
                            message=base_notice.message,
                            notification_type='OFFICIAL_NOTICE',
                            project=project,
                            is_official_notice=True,
                            notice_number=base_notice.notice_number,
                            attachment=base_notice.attachment,
                            created_by=request.user,
                        )
                        count += 1

            for lr in project.land_records.all():
                record_status_change(
                    project=project,
                    new_status='NOTIFICATION_PUBLISHED',
                    updated_by=request.user,
                    land_record=lr,
                    remarks=f'Official notice {base_notice.notice_number} published.',
                )
            project.status = 'NOTIFICATION_PUBLISHED'
            project.save(update_fields=['status', 'updated_at'])
            log_audit(request, 'NOTIFICATION_PUBLISHED', 'AcquisitionProject', project.id, f'Notice {base_notice.notice_number} sent to {count} landowners')
            messages.success(request, f'Official notification published ({count} registered landowners notified).')
            return redirect('projects:project_detail', pk=project.pk)
    else:
        form = OfficialNotificationForm()
    return render(request, 'projects/publish_notification.html', {'form': form, 'project': project})


@role_required('ADMIN')
def department_list(request):
    """Manage government departments (Admin only)."""
    departments = Department.objects.all()
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            dept = form.save()
            log_audit(request, 'DEPARTMENT_CREATED', 'Department', dept.id, dept.name)
            messages.success(request, f'Department "{dept.name}" created.')
            return redirect('projects:department_list')
    else:
        form = DepartmentForm()
    return render(request, 'projects/department_list.html', {'departments': departments, 'form': form})
