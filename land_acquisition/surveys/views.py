from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from accounts.decorators import get_user_role, log_audit, role_required
from notifications.utils import create_notification, record_status_change
from .forms import SurveyAssignmentForm, SurveyReportForm
from .models import SurveyAssignment, SurveyReport


@role_required('SURVEYOR')
def surveyor_dashboard(request):
    """Panel 3: Surveyor Dashboard showing assigned and completed surveys."""
    assignments = SurveyAssignment.objects.filter(surveyor=request.user).select_related(
        'project', 'land_record', 'land_record__landowner'
    )
    context = {
        'total_assigned': assignments.count(),
        'pending_count': assignments.filter(status__in=['PENDING', 'ASSIGNED', 'IN_PROGRESS']).count(),
        'submitted_count': assignments.filter(status='SUBMITTED').count(),
        'verified_count': assignments.filter(status='VERIFIED').count(),
        'rejected_count': assignments.filter(status='REJECTED').count(),
        'active_surveys': assignments.filter(status__in=['PENDING', 'ASSIGNED', 'IN_PROGRESS', 'REJECTED']),
        'completed_surveys': assignments.filter(status__in=['SUBMITTED', 'VERIFIED']),
    }
    return render(request, 'surveys/surveyor_dashboard.html', context)


@role_required('ADMIN', 'OFFICER', 'SURVEYOR', 'MONITORING')
def survey_list(request):
    """List surveys scoped by user role."""
    role = get_user_role(request.user)
    assignments = SurveyAssignment.objects.select_related(
        'project', 'land_record', 'land_record__landowner', 'surveyor'
    )
    if role == 'SURVEYOR':
        assignments = assignments.filter(surveyor=request.user)
    elif role == 'OFFICER':
        assignments = assignments.filter(project__assigned_officer=request.user)

    status = request.GET.get('status', '').strip()
    if status:
        assignments = assignments.filter(status=status)

    return render(request, 'surveys/survey_list.html', {
        'assignments': assignments,
        'status': status,
    })


@role_required('ADMIN', 'OFFICER')
def survey_assign(request):
    """Step 3: Assign a land parcel to a surveyor."""
    land_id = request.GET.get('land_record')
    initial = {'land_record': land_id} if land_id else {}
    if request.method == 'POST':
        form = SurveyAssignmentForm(request.POST)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.project = assignment.land_record.project
            assignment.assigned_by = request.user
            assignment.status = 'ASSIGNED'
            assignment.save()

            record_status_change(
                project=assignment.project,
                new_status='SURVEY_ASSIGNED',
                updated_by=request.user,
                land_record=assignment.land_record,
                remarks=f'Survey assigned to {assignment.surveyor.get_full_name() or assignment.surveyor.username}.',
            )
            create_notification(
                recipient=assignment.surveyor,
                title=f'New Survey Assigned: {assignment.land_record}',
                message=(
                    f'You have been assigned to survey Survey {assignment.land_record.survey_number} / '
                    f'Plot {assignment.land_record.plot_number} in {assignment.land_record.village}.'
                ),
                notification_type='SURVEY_UPDATE',
                project=assignment.project,
                created_by=request.user,
            )
            log_audit(request, 'SURVEY_ASSIGNED', 'SurveyAssignment', assignment.id, str(assignment))
            messages.success(request, 'Survey assigned to surveyor successfully.')
            return redirect('surveys:detail', pk=assignment.pk)
    else:
        form = SurveyAssignmentForm(initial=initial)

    return render(request, 'surveys/survey_assign_form.html', {'form': form})


@role_required('ADMIN', 'OFFICER', 'SURVEYOR', 'MONITORING')
def survey_detail(request, pk):
    """Step 4 & 5: Surveyor submits report; Officer verifies or rejects report."""
    assignment = get_object_or_404(
        SurveyAssignment.objects.select_related(
            'project', 'land_record', 'land_record__landowner', 'surveyor', 'assigned_by'
        ),
        pk=pk,
    )
    role = get_user_role(request.user)
    if role == 'SURVEYOR' and assignment.surveyor != request.user:
        messages.error(request, 'Access denied: this survey is not assigned to you.')
        return redirect('surveys:surveyor_dashboard')

    report = getattr(assignment, 'report', None)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'mark_in_progress' and role == 'SURVEYOR':
            assignment.status = 'IN_PROGRESS'
            assignment.save(update_fields=['status', 'updated_at'])
            record_status_change(
                project=assignment.project,
                new_status='SURVEY_IN_PROGRESS',
                updated_by=request.user,
                land_record=assignment.land_record,
                remarks='Surveyor started field inspection.',
            )
            messages.info(request, 'Survey marked as In Progress.')
            return redirect('surveys:detail', pk=assignment.pk)

        if action == 'submit_report' and role in ('SURVEYOR', 'ADMIN'):
            form = SurveyReportForm(request.POST, request.FILES, instance=report)
            if form.is_valid():
                rep = form.save(commit=False)
                rep.assignment = assignment
                rep.submitted_by = request.user
                rep.save()

                assignment.status = 'SUBMITTED'
                assignment.save(update_fields=['status', 'updated_at'])
                record_status_change(
                    project=assignment.project,
                    new_status='SURVEY_COMPLETED',
                    updated_by=request.user,
                    land_record=assignment.land_record,
                    remarks='Survey report submitted for officer verification.',
                )
                if assignment.project.assigned_officer:
                    create_notification(
                        recipient=assignment.project.assigned_officer,
                        title=f'Survey Report Submitted: {assignment.land_record}',
                        message=(
                            f'Surveyor {request.user.get_full_name() or request.user.username} submitted '
                            f'the inspection report for {assignment.land_record}.'
                        ),
                        notification_type='SURVEY_UPDATE',
                        project=assignment.project,
                        created_by=request.user,
                    )
                log_audit(request, 'SURVEY_REPORT_SUBMITTED', 'SurveyReport', rep.id, str(assignment.land_record))
                messages.success(request, 'Survey report submitted to the Government Officer.')
                return redirect('surveys:detail', pk=assignment.pk)
        else:
            form = SurveyReportForm(instance=report)

        if action in ('verify', 'reject') and role in ('OFFICER', 'ADMIN'):
            remarks = request.POST.get('officer_remarks', '').strip()
            assignment.officer_remarks = remarks
            if action == 'verify':
                assignment.status = 'VERIFIED'
                assignment.save(update_fields=['status', 'officer_remarks', 'updated_at'])
                if report:
                    report.verified_by = request.user
                    report.verified_at = timezone.now()
                    report.save(update_fields=['verified_by', 'verified_at'])
                record_status_change(
                    project=assignment.project,
                    new_status='SURVEY_VERIFIED',
                    updated_by=request.user,
                    land_record=assignment.land_record,
                    remarks=remarks or 'Survey report verified by officer.',
                )
                messages.success(request, 'Survey report verified successfully.')
            else:
                assignment.status = 'REJECTED'
                assignment.save(update_fields=['status', 'officer_remarks', 'updated_at'])
                messages.warning(request, 'Survey report rejected with remarks.')

            create_notification(
                recipient=assignment.surveyor,
                title=f'Survey {assignment.get_status_display()}: {assignment.land_record}',
                message=f'Officer remarks: {remarks or "No remarks."}',
                notification_type='SURVEY_UPDATE',
                project=assignment.project,
                created_by=request.user,
            )
            log_audit(request, f'SURVEY_{assignment.status}', 'SurveyAssignment', assignment.id, remarks)
            return redirect('surveys:detail', pk=assignment.pk)
    else:
        initial = {}
        if not report:
            initial = {
                'actual_area_acres': assignment.land_record.area_acres,
                'verified_land_type': assignment.land_record.get_land_type_display(),
                'current_land_usage': assignment.land_record.current_usage,
            }
        form = SurveyReportForm(instance=report, initial=initial)

    return render(request, 'surveys/survey_detail.html', {
        'assignment': assignment,
        'report': report,
        'form': form,
    })
