from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from accounts.decorators import get_user_role, log_audit, role_required
from land_records.models import Landowner
from notifications.utils import create_notification, record_status_change
from .forms import ObjectionReviewForm, ObjectionSubmitForm
from .models import Objection


@role_required('ADMIN', 'OFFICER', 'LANDOWNER', 'MONITORING')
def objection_list(request):
    """List objections scoped by user role."""
    role = get_user_role(request.user)
    qs = Objection.objects.select_related('project', 'land_record', 'landowner', 'reviewed_by')
    if role == 'LANDOWNER':
        qs = qs.filter(landowner__user=request.user)
    elif role == 'OFFICER':
        qs = qs.filter(Q(project__assigned_officer=request.user) | Q(project__created_by=request.user))

    status = request.GET.get('status', '').strip()
    if status:
        qs = qs.filter(status=status)

    return render(request, 'objections/objection_list.html', {'objections': qs, 'status': status})


@role_required('LANDOWNER')
def objection_submit(request):
    """Step 8: Landowner submits an objection or complaint."""
    landowner = get_object_or_404(Landowner, user=request.user)
    land_id = request.GET.get('land_record')
    initial = {'land_record': land_id} if land_id else {}

    if request.method == 'POST':
        form = ObjectionSubmitForm(request.POST, request.FILES, landowner=landowner)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.landowner = landowner
            obj.project = obj.land_record.project
            obj.status = 'SUBMITTED'
            obj.save()

            record_status_change(
                project=obj.project,
                new_status='OBJECTION_SUBMITTED',
                updated_by=request.user,
                land_record=obj.land_record,
                remarks=f'Objection submitted: {obj.subject}',
            )
            if obj.project.assigned_officer:
                create_notification(
                    recipient=obj.project.assigned_officer,
                    title=f'New Objection Filed: {obj.land_record}',
                    message=f'{landowner.full_name} filed an objection: "{obj.subject}".',
                    notification_type='OBJECTION_UPDATE',
                    project=obj.project,
                    created_by=request.user,
                )
            log_audit(request, 'OBJECTION_SUBMITTED', 'Objection', obj.id, obj.subject)
            messages.success(request, 'Your objection has been submitted for review.')
            return redirect('objections:detail', pk=obj.pk)
    else:
        form = ObjectionSubmitForm(landowner=landowner, initial=initial)

    return render(request, 'objections/objection_form.html', {'form': form})


@role_required('ADMIN', 'OFFICER', 'LANDOWNER', 'MONITORING')
def objection_detail(request, pk):
    """View objection details and allow Officer/Admin to approve or reject."""
    obj = get_object_or_404(
        Objection.objects.select_related('project', 'land_record', 'landowner', 'reviewed_by'),
        pk=pk,
    )
    role = get_user_role(request.user)
    if role == 'LANDOWNER' and obj.landowner.user != request.user:
        messages.error(request, 'Access denied: you can only view your own objections.')
        return redirect('land_records:landowner_dashboard')

    if request.method == 'POST' and role in ('ADMIN', 'OFFICER'):
        form = ObjectionReviewForm(request.POST)
        if form.is_valid():
            obj.status = form.cleaned_data['status']
            obj.officer_remarks = form.cleaned_data['officer_remarks']
            obj.reviewed_by = request.user
            obj.reviewed_at = timezone.now()
            obj.save()

            if obj.status == 'UNDER_REVIEW':
                record_status_change(
                    project=obj.project,
                    new_status='OBJECTION_UNDER_REVIEW',
                    updated_by=request.user,
                    land_record=obj.land_record,
                    remarks=obj.officer_remarks,
                )

            if obj.landowner.user:
                create_notification(
                    recipient=obj.landowner.user,
                    title=f'Objection {obj.get_status_display()}: {obj.subject}',
                    message=f'Officer remarks: {obj.officer_remarks}',
                    notification_type='OBJECTION_UPDATE',
                    project=obj.project,
                    created_by=request.user,
                )
            log_audit(request, f'OBJECTION_{obj.status}', 'Objection', obj.id, obj.officer_remarks)
            messages.success(request, f'Objection marked as {obj.get_status_display()}.')
            return redirect('objections:detail', pk=obj.pk)
    else:
        form = ObjectionReviewForm(initial={
            'status': obj.status if obj.status != 'SUBMITTED' else 'UNDER_REVIEW',
            'officer_remarks': obj.officer_remarks,
        })

    return render(request, 'objections/objection_detail.html', {'obj': obj, 'form': form})
