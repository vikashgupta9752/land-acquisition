from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from accounts.decorators import get_user_role, log_audit, role_required
from land_records.models import LandRecord
from notifications.utils import create_notification, record_status_change
from .forms import CompensationApprovalForm, CompensationCalculatorForm, PaymentForm
from .models import Compensation, Payment


@role_required('ADMIN', 'OFFICER', 'MONITORING')
def compensation_list(request):
    """List all compensation records."""
    role = get_user_role(request.user)
    records = Compensation.objects.select_related('project', 'land_record', 'land_record__landowner')
    if role == 'OFFICER':
        records = records.filter(Q(project__assigned_officer=request.user) | Q(project__created_by=request.user))

    status = request.GET.get('status', '').strip()
    if status:
        records = records.filter(status=status)

    return render(request, 'compensation/compensation_list.html', {
        'compensations': records,
        'status': status,
    })


@role_required('ADMIN', 'OFFICER')
def compensation_calculate(request):
    """Step 6: Calculate land valuation and proposed compensation."""
    land_id = request.GET.get('land_record')
    initial = {}
    instance = None
    if land_id:
        lr = get_object_or_404(LandRecord, pk=land_id)
        instance = getattr(lr, 'compensation', None)
        if not instance:
            initial = {
                'land_record': lr,
                'land_area_acres': lr.area_acres,
                'rate_per_acre': 1000000,
                'solatium_percent': 100,
            }

    if request.method == 'POST':
        land_record_id = request.POST.get('land_record')
        if land_record_id and not instance:
            instance = Compensation.objects.filter(land_record_id=land_record_id).first()
        form = CompensationCalculatorForm(request.POST, instance=instance)
        if form.is_valid():
            comp = form.save(commit=False)
            comp.project = comp.land_record.project
            comp.calculated_by = request.user
            if comp.status == 'ESTIMATED':
                comp.status = 'PROPOSED'
            comp.save()

            record_status_change(
                project=comp.project,
                new_status='COMPENSATION_PROPOSED',
                updated_by=request.user,
                land_record=comp.land_record,
                remarks=f'Proposed compensation calculated: ₹{comp.proposed_compensation:,.2f}',
            )
            log_audit(
                request,
                'COMPENSATION_CALCULATED',
                'Compensation',
                comp.id,
                f'{comp.land_record} -> ₹{comp.proposed_compensation:,.2f}',
            )
            messages.success(request, f'Compensation calculated: ₹{comp.proposed_compensation:,.2f}')
            return redirect('compensation:detail', pk=comp.pk)
    else:
        form = CompensationCalculatorForm(instance=instance, initial=initial)

    return render(request, 'compensation/compensation_calculator.html', {'form': form, 'instance': instance})


@role_required('ADMIN', 'OFFICER', 'LANDOWNER', 'MONITORING')
def compensation_detail(request, pk):
    """View compensation breakdown, approval controls, and payment history."""
    comp = get_object_or_404(
        Compensation.objects.select_related('project', 'land_record', 'land_record__landowner'), pk=pk
    )
    role = get_user_role(request.user)
    if role == 'LANDOWNER' and comp.land_record.landowner.user != request.user:
        messages.error(request, 'Access denied: you can only view your own compensation records.')
        return redirect('land_records:landowner_dashboard')

    payments = comp.payments.all()
    approval_form = CompensationApprovalForm(initial={
        'approved_compensation': comp.approved_compensation or comp.proposed_compensation,
        'valuation_remarks': comp.valuation_remarks,
    })
    payment_form = PaymentForm(initial={'amount': comp.approved_compensation or comp.proposed_compensation})

    return render(request, 'compensation/compensation_detail.html', {
        'comp': comp,
        'payments': payments,
        'approval_form': approval_form,
        'payment_form': payment_form,
    })


@role_required('ADMIN', 'OFFICER')
def compensation_approve(request, pk):
    """Step 9 & 10: Officially approve compensation amount."""
    comp = get_object_or_404(Compensation, pk=pk)
    if request.method == 'POST':
        form = CompensationApprovalForm(request.POST)
        if form.is_valid():
            comp.approved_compensation = form.cleaned_data['approved_compensation']
            comp.valuation_remarks = form.cleaned_data['valuation_remarks']
            comp.status = 'APPROVED'
            comp.approved_by = request.user
            comp.approved_at = timezone.now()
            comp.save()

            record_status_change(
                project=comp.project,
                new_status='COMPENSATION_APPROVED',
                updated_by=request.user,
                land_record=comp.land_record,
                remarks=f'Approved compensation: ₹{comp.approved_compensation:,.2f}',
            )
            record_status_change(
                project=comp.project,
                new_status='PAYMENT_PENDING',
                updated_by=request.user,
                land_record=comp.land_record,
                remarks='Awaiting compensation payment disbursement.',
            )
            if comp.land_record.landowner.user:
                create_notification(
                    recipient=comp.land_record.landowner.user,
                    title=f'Compensation Approved: Survey {comp.land_record.survey_number}',
                    message=(
                        f'Official compensation of ₹{comp.approved_compensation:,.2f} has been approved '
                        f'for your land parcel ({comp.land_record}).'
                    ),
                    notification_type='COMPENSATION_UPDATE',
                    project=comp.project,
                    created_by=request.user,
                )
            log_audit(request, 'COMPENSATION_APPROVED', 'Compensation', comp.id, f'Approved ₹{comp.approved_compensation:,.2f}')
            messages.success(request, 'Compensation approved and marked for payment.')
    return redirect('compensation:detail', pk=comp.pk)


@role_required('ADMIN', 'OFFICER')
def payment_record(request, comp_pk):
    """Step 10: Record or update compensation payment disbursement."""
    comp = get_object_or_404(Compensation, pk=comp_pk)
    if request.method == 'POST':
        payment_id = request.POST.get('payment_id')
        instance = Payment.objects.filter(pk=payment_id, compensation=comp).first() if payment_id else None
        form = PaymentForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.compensation = comp
            payment.landowner = comp.land_record.landowner
            payment.processed_by = request.user
            payment.save()

            if payment.status == 'PAID':
                comp.status = 'DISBURSED'
                comp.save()
                record_status_change(
                    project=comp.project,
                    new_status='PAYMENT_COMPLETED',
                    updated_by=request.user,
                    land_record=comp.land_record,
                    remarks=f'Payment ₹{payment.amount:,.2f} completed via {payment.get_payment_mode_display()}.',
                )
            elif payment.status in ('PENDING', 'PROCESSING'):
                record_status_change(
                    project=comp.project,
                    new_status='PAYMENT_PENDING',
                    updated_by=request.user,
                    land_record=comp.land_record,
                    remarks=f'Payment status updated to {payment.get_status_display()}.',
                )

            if comp.land_record.landowner.user:
                create_notification(
                    recipient=comp.land_record.landowner.user,
                    title=f'Payment Status: {payment.get_status_display()}',
                    message=(
                        f'Compensation payment of ₹{payment.amount:,.2f} for {comp.land_record} '
                        f'is now {payment.get_status_display()}. Ref: {payment.transaction_reference or "N/A"}'
                    ),
                    notification_type='PAYMENT_UPDATE',
                    project=comp.project,
                    created_by=request.user,
                )

            log_audit(request, f'PAYMENT_{payment.status}', 'Payment', payment.id, f'₹{payment.amount:,.2f}')
            messages.success(request, f'Payment recorded with status: {payment.get_status_display()}.')
        else:
            messages.error(request, f'Payment error: {form.errors.as_text()}')
    return redirect('compensation:detail', pk=comp.pk)
