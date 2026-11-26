from django.contrib import messages
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from accounts.decorators import get_user_role, log_audit, role_required
from compensation.models import Compensation, Payment
from notifications.models import Notification
from notifications.utils import create_notification, record_status_change
from objections.models import Objection
from projects.models import AcquisitionProject
from .forms import LandownerForm, LandRecordForm, PossessionRecordForm
from .models import Landowner, LandRecord, PossessionRecord


@role_required('LANDOWNER')
def landowner_dashboard(request):
    """Panel 4: Landowner / Citizen Dashboard scoped strictly to the logged-in landowner."""
    landowner = Landowner.objects.filter(user=request.user).first()
    if not landowner:
        landowner = Landowner.objects.create(
            user=request.user,
            full_name=request.user.get_full_name() or request.user.username,
            phone=getattr(getattr(request.user, 'profile', None), 'phone', '') or 'N/A',
            email=request.user.email,
            address=getattr(getattr(request.user, 'profile', None), 'address', '') or 'N/A',
            village='N/A',
            district='N/A',
        )

    land_records = LandRecord.objects.filter(landowner=landowner).select_related('project')
    project_ids = land_records.values_list('project_id', flat=True).distinct()
    official_notices = Notification.objects.filter(
        project_id__in=project_ids,
        is_official_notice=True,
        recipient__isnull=True,
    )
    compensations = Compensation.objects.filter(land_record__in=land_records).select_related('land_record')
    payments = Payment.objects.filter(landowner=landowner).select_related('compensation__land_record')
    objections = Objection.objects.filter(landowner=landowner).select_related('land_record', 'project')

    context = {
        'landowner': landowner,
        'land_records': land_records,
        'official_notices': official_notices,
        'compensations': compensations,
        'payments': payments,
        'objections': objections,
        'total_area': land_records.aggregate(s=Sum('area_acres'))['s'] or 0,
        'total_proposed': compensations.aggregate(s=Sum('proposed_compensation'))['s'] or 0,
        'total_approved': compensations.aggregate(s=Sum('approved_compensation'))['s'] or 0,
        'total_paid': payments.filter(status='PAID').aggregate(s=Sum('amount'))['s'] or 0,
    }
    return render(request, 'land_records/landowner_dashboard.html', context)


@role_required('ADMIN', 'OFFICER', 'MONITORING')
def land_record_list(request):
    """List and filter all registered land parcels."""
    role = get_user_role(request.user)
    records = LandRecord.objects.select_related('project', 'landowner')
    if role == 'OFFICER':
        records = records.filter(Q(project__assigned_officer=request.user) | Q(project__created_by=request.user))

    q = request.GET.get('q', '').strip()
    project_id = request.GET.get('project', '').strip()
    status = request.GET.get('status', '').strip()

    if q:
        records = records.filter(
            Q(survey_number__icontains=q)
            | Q(plot_number__icontains=q)
            | Q(village__icontains=q)
            | Q(landowner__full_name__icontains=q)
        )
    if project_id:
        records = records.filter(project_id=project_id)
    if status:
        records = records.filter(acquisition_status=status)

    return render(request, 'land_records/land_record_list.html', {
        'records': records,
        'projects': AcquisitionProject.objects.all(),
        'q': q,
        'project_id': project_id,
        'status': status,
    })


@role_required('ADMIN', 'OFFICER')
def land_record_create(request):
    """Step 2: Register a new land parcel and connect it with a landowner."""
    project_id = request.GET.get('project')
    initial = {}
    if project_id:
        initial['project'] = project_id
        proj = AcquisitionProject.objects.filter(pk=project_id).first()
        if proj:
            initial['village'] = proj.village
            initial['district'] = proj.district
            initial['taluka'] = proj.taluka
            initial['latitude'] = proj.latitude
            initial['longitude'] = proj.longitude

    if request.method == 'POST':
        form = LandRecordForm(request.POST)
        if form.is_valid():
            lr = form.save(commit=False)
            lr.created_by = request.user
            lr.save()
            record_status_change(
                project=lr.project,
                new_status='LAND_REGISTERED',
                updated_by=request.user,
                land_record=lr,
                remarks=f'Land parcel Survey {lr.survey_number}/Plot {lr.plot_number} registered.',
            )
            if lr.landowner.user:
                create_notification(
                    recipient=lr.landowner.user,
                    title=f'Land Registered under {lr.project.name}',
                    message=(
                        f'Your land parcel (Survey {lr.survey_number}, Plot {lr.plot_number}, '
                        f'{lr.area_acres} acres in {lr.village}) has been registered under project '
                        f'{lr.project.project_code}.'
                    ),
                    notification_type='PROJECT_UPDATE',
                    project=lr.project,
                    created_by=request.user,
                )
            log_audit(request, 'LAND_RECORD_CREATED', 'LandRecord', lr.id, str(lr))
            messages.success(request, f'Land record {lr} registered successfully.')
            return redirect('land_records:detail', pk=lr.pk)
    else:
        form = LandRecordForm(initial=initial)

    return render(request, 'land_records/land_record_form.html', {
        'form': form,
        'title': 'Register Land Record',
    })


@role_required('ADMIN', 'OFFICER')
def land_record_edit(request, pk):
    """Edit land record details and map coordinates/boundary."""
    lr = get_object_or_404(LandRecord, pk=pk)
    if request.method == 'POST':
        form = LandRecordForm(request.POST, instance=lr)
        if form.is_valid():
            form.save()
            log_audit(request, 'LAND_RECORD_UPDATED', 'LandRecord', lr.id, str(lr))
            messages.success(request, 'Land record updated.')
            return redirect('land_records:detail', pk=lr.pk)
    else:
        form = LandRecordForm(instance=lr)
    return render(request, 'land_records/land_record_form.html', {
        'form': form,
        'title': f'Edit Land Record: {lr.survey_number}/{lr.plot_number}',
        'land_record': lr,
    })


@role_required('ADMIN', 'OFFICER', 'SURVEYOR', 'LANDOWNER', 'MONITORING')
def land_record_detail(request, pk):
    """Detailed view of a land parcel with strict landowner ownership check."""
    lr = get_object_or_404(
        LandRecord.objects.select_related('project', 'landowner'), pk=pk
    )
    role = get_user_role(request.user)
    if role == 'LANDOWNER' and lr.landowner.user != request.user:
        messages.error(request, 'Access denied: you can only view your own land records.')
        return redirect('land_records:landowner_dashboard')

    surveys = lr.survey_assignments.select_related('surveyor')
    objections = lr.objections.select_related('reviewed_by')
    compensation = getattr(lr, 'compensation', None)
    possession = getattr(lr, 'possession_record', None)
    history = lr.status_history.select_related('updated_by')
    documents = lr.documents.all()

    return render(request, 'land_records/land_record_detail.html', {
        'lr': lr,
        'surveys': surveys,
        'objections': objections,
        'compensation': compensation,
        'possession': possession,
        'history': history,
        'documents': documents,
    })


@role_required('ADMIN', 'OFFICER')
def landowner_list(request):
    """List and search registered landowners."""
    q = request.GET.get('q', '').strip()
    owners = Landowner.objects.all()
    if q:
        owners = owners.filter(
            Q(full_name__icontains=q) | Q(phone__icontains=q) | Q(village__icontains=q)
        )
    return render(request, 'land_records/landowner_list.html', {'owners': owners, 'q': q})


@role_required('ADMIN', 'OFFICER')
def landowner_create(request):
    """Register a new landowner."""
    if request.method == 'POST':
        form = LandownerForm(request.POST)
        if form.is_valid():
            owner = form.save()
            log_audit(request, 'LANDOWNER_CREATED', 'Landowner', owner.id, owner.full_name)
            messages.success(request, f'Landowner "{owner.full_name}" registered.')
            return redirect('land_records:landowner_list')
    else:
        form = LandownerForm()
    return render(request, 'land_records/landowner_form.html', {'form': form, 'title': 'Register Landowner'})


@role_required('ADMIN', 'OFFICER')
def record_possession(request, pk):
    """Step 11: Record formal land possession and update project acquired area."""
    lr = get_object_or_404(LandRecord, pk=pk)
    existing = getattr(lr, 'possession_record', None)
    if request.method == 'POST':
        form = PossessionRecordForm(request.POST, request.FILES, instance=existing)
        if form.is_valid():
            possession = form.save(commit=False)
            possession.land_record = lr
            possession.project = lr.project
            possession.handover_officer = request.user
            possession.status = 'COMPLETED'
            possession.save()

            lr.possession_status = 'TAKEN_OVER'
            lr.is_acquired = True
            lr.save(update_fields=['possession_status', 'is_acquired', 'updated_at'])

            new_status = (
                'ACQUISITION_COMPLETED'
                if form.cleaned_data.get('mark_acquisition_completed')
                else 'POSSESSION_COMPLETED'
            )
            record_status_change(
                project=lr.project,
                new_status=new_status,
                updated_by=request.user,
                land_record=lr,
                remarks=f'Possession recorded on {possession.possession_date}.',
            )

            # Recompute total acquired area on the project
            acquired_sum = (
                lr.project.land_records.filter(is_acquired=True).aggregate(s=Sum('area_acres'))['s'] or 0
            )
            lr.project.acquired_area_acres = acquired_sum
            lr.project.save(update_fields=['acquired_area_acres', 'updated_at'])

            if lr.landowner.user:
                create_notification(
                    recipient=lr.landowner.user,
                    title=f'Possession Recorded for Survey {lr.survey_number}',
                    message=(
                        f'Formal possession has been recorded for Survey {lr.survey_number} / '
                        f'Plot {lr.plot_number} on {possession.possession_date}.'
                    ),
                    notification_type='POSSESSION_UPDATE',
                    project=lr.project,
                    created_by=request.user,
                )

            log_audit(request, 'POSSESSION_RECORDED', 'PossessionRecord', possession.id, str(lr))
            messages.success(request, 'Land possession recorded and project acquired area updated.')
            return redirect('land_records:detail', pk=lr.pk)
    else:
        form = PossessionRecordForm(instance=existing)

    return render(request, 'land_records/possession_form.html', {'form': form, 'lr': lr})
