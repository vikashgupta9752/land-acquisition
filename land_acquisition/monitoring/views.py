import csv
import json
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from accounts.decorators import role_required
from compensation.models import Compensation, Payment
from land_records.models import Landowner, LandRecord
from objections.models import Objection
from projects.models import AcquisitionProject
from surveys.models import SurveyAssignment
from .pdf_utils import generate_table_pdf


@role_required('ADMIN', 'MONITORING', 'OFFICER')
def monitoring_dashboard(request):
    """Panel 5: Monitoring & Decision Support Dashboard with real-time KPIs, charts, and map."""
    q = request.GET.get('q', '').strip()
    district = request.GET.get('district', '').strip()
    status = request.GET.get('status', '').strip()

    projects = AcquisitionProject.objects.select_related('department', 'assigned_officer')
    if q:
        projects = projects.filter(Q(project_code__icontains=q) | Q(name__icontains=q) | Q(village__icontains=q))
    if district:
        projects = projects.filter(district__icontains=district)
    if status:
        projects = projects.filter(status=status)

    total_required = projects.aggregate(s=Sum('required_area_acres'))['s'] or 0
    total_acquired = projects.aggregate(s=Sum('acquired_area_acres'))['s'] or 0
    total_pending_land = max(total_required - total_acquired, 0)

    total_estimated_comp = Compensation.objects.aggregate(s=Sum('proposed_compensation'))['s'] or 0
    total_approved_comp = Compensation.objects.aggregate(s=Sum('approved_compensation'))['s'] or 0
    total_paid_comp = Payment.objects.filter(status='PAID').aggregate(s=Sum('amount'))['s'] or 0
    total_pending_comp = max((total_approved_comp or total_estimated_comp) - total_paid_comp, 0)

    delayed_projects = [p for p in projects if p.is_delayed]

    district_stats = (
        AcquisitionProject.objects.values('district')
        .annotate(
            project_count=Count('id'),
            required_area=Sum('required_area_acres'),
            acquired_area=Sum('acquired_area_acres'),
        )
        .order_by('-required_area')
    )

    village_stats = (
        LandRecord.objects.values('village', 'district')
        .annotate(
            parcel_count=Count('id'),
            total_area=Sum('area_acres'),
        )
        .order_by('-total_area')[:10]
    )

    project_labels = [p.project_code for p in projects[:10]]
    project_required = [float(p.required_area_acres) for p in projects[:10]]
    project_acquired = [float(p.acquired_area_acres) for p in projects[:10]]

    map_markers = []
    for lr in LandRecord.objects.select_related('project', 'landowner').all():
        if lr.latitude is not None and lr.longitude is not None:
            cat = 'acquired' if lr.is_acquired else (
                'surveyed' if lr.acquisition_status in (
                    'SURVEY_COMPLETED', 'SURVEY_VERIFIED', 'COMPENSATION_PROPOSED', 'COMPENSATION_APPROVED'
                ) else 'pending'
            )
            map_markers.append({
                'survey_number': lr.survey_number,
                'plot_number': lr.plot_number,
                'project': lr.project.project_code,
                'village': lr.village,
                'area': float(lr.area_acres),
                'status': lr.get_acquisition_status_display(),
                'category': cat,
                'lat': float(lr.latitude),
                'lng': float(lr.longitude),
            })

    context = {
        'total_projects': projects.count(),
        'total_required': total_required,
        'total_acquired': total_acquired,
        'total_pending_land': total_pending_land,
        'total_landowners': Landowner.objects.count(),
        'completed_surveys': SurveyAssignment.objects.filter(status__in=['SUBMITTED', 'VERIFIED']).count(),
        'pending_surveys': SurveyAssignment.objects.filter(status__in=['PENDING', 'ASSIGNED', 'IN_PROGRESS']).count(),
        'total_objections': Objection.objects.count(),
        'approved_objections': Objection.objects.filter(status='APPROVED').count(),
        'rejected_objections': Objection.objects.filter(status='REJECTED').count(),
        'pending_objections': Objection.objects.filter(status__in=['SUBMITTED', 'UNDER_REVIEW']).count(),
        'total_estimated_comp': total_estimated_comp,
        'total_approved_comp': total_approved_comp,
        'total_paid_comp': total_paid_comp,
        'total_pending_comp': total_pending_comp,
        'projects': projects,
        'delayed_projects': delayed_projects,
        'district_stats': district_stats,
        'village_stats': village_stats,
        'project_labels_json': json.dumps(project_labels),
        'project_required_json': json.dumps(project_required),
        'project_acquired_json': json.dumps(project_acquired),
        'comp_chart_json': json.dumps([
            float(total_estimated_comp),
            float(total_approved_comp),
            float(total_paid_comp),
            float(total_pending_comp),
        ]),
        'obj_chart_json': json.dumps([
            Objection.objects.filter(status='SUBMITTED').count(),
            Objection.objects.filter(status='UNDER_REVIEW').count(),
            Objection.objects.filter(status='APPROVED').count(),
            Objection.objects.filter(status='REJECTED').count(),
        ]),
        'map_markers_json': json.dumps(map_markers),
        'q': q,
        'district': district,
        'status': status,
    }
    return render(request, 'monitoring/monitoring_dashboard.html', context)


@role_required('ADMIN', 'MONITORING', 'OFFICER')
def reports_hub(request):
    """Central page to preview and export all 8 system reports in CSV or PDF."""
    return render(request, 'monitoring/reports_hub.html')


def _get_report_data(report_type):
    """Build (title, headers, rows) for the requested report type."""
    if report_type == 'projects':
        title = 'Project-wise Land Acquisition Report'
        headers = ['Code', 'Project Name', 'Department', 'District', 'Village', 'Req (Ac)', 'Acq (Ac)', 'Status']
        rows = [
            [
                p.project_code, p.name, p.department.code, p.district, p.village,
                str(p.required_area_acres), str(p.acquired_area_acres), p.get_status_display(),
            ]
            for p in AcquisitionProject.objects.select_related('department').all()
        ]
    elif report_type == 'landowners':
        title = 'Landowner-wise Acquisition Report'
        headers = ['Landowner', 'Phone', 'Village', 'District', 'Parcels', 'Total Area (Ac)']
        rows = []
        for lo in Landowner.objects.prefetch_related('land_records').all():
            parcels = lo.land_records.count()
            area = sum(r.area_acres for r in lo.land_records.all())
            rows.append([lo.full_name, lo.phone, lo.village, lo.district, str(parcels), str(area)])
    elif report_type == 'villages':
        title = 'Village-wise Land Acquisition Report'
        headers = ['Village', 'District', 'Parcels', 'Total Area (Ac)', 'Acquired Parcels']
        qs = LandRecord.objects.values('village', 'district').annotate(
            parcels=Count('id'),
            area=Sum('area_acres'),
            acquired=Count('id', filter=Q(is_acquired=True)),
        )
        rows = [[r['village'], r['district'], str(r['parcels']), str(r['area'] or 0), str(r['acquired'])] for r in qs]
    elif report_type == 'surveys':
        title = 'Survey Completion Report'
        headers = ['Survey ID', 'Project', 'Parcel', 'Surveyor', 'Status', 'Assigned Date']
        rows = [
            [
                str(s.id), s.project.project_code, f'{s.land_record.survey_number}/{s.land_record.plot_number}',
                s.surveyor.get_full_name() or s.surveyor.username, s.get_status_display(), str(s.assigned_date),
            ]
            for s in SurveyAssignment.objects.select_related('project', 'land_record', 'surveyor').all()
        ]
    elif report_type == 'objections':
        title = 'Landowner Objections Report'
        headers = ['ID', 'Project', 'Landowner', 'Category', 'Subject', 'Status']
        rows = [
            [
                str(o.id), o.project.project_code, o.landowner.full_name,
                o.get_category_display(), o.subject, o.get_status_display(),
            ]
            for o in Objection.objects.select_related('project', 'landowner').all()
        ]
    elif report_type == 'compensation':
        title = 'Compensation Valuation & Approval Report'
        headers = ['Project', 'Parcel', 'Owner', 'Area', 'Proposed (INR)', 'Approved (INR)', 'Status']
        rows = [
            [
                c.project.project_code, f'{c.land_record.survey_number}/{c.land_record.plot_number}',
                c.land_record.landowner.full_name, str(c.land_area_acres),
                str(c.proposed_compensation), str(c.approved_compensation or 0), c.get_status_display(),
            ]
            for c in Compensation.objects.select_related('project', 'land_record', 'land_record__landowner').all()
        ]
    elif report_type == 'payments':
        title = 'Compensation Payment Disbursement Report'
        headers = ['Ref', 'Landowner', 'Mode', 'Amount (INR)', 'Date', 'Status']
        rows = [
            [
                p.transaction_reference or f'PAY-{p.id}', p.landowner.full_name,
                p.get_payment_mode_display(), str(p.amount), str(p.payment_date or '-'), p.get_status_display(),
            ]
            for p in Payment.objects.select_related('landowner').all()
        ]
    else:
        title = 'Delayed Acquisition Projects Report'
        headers = ['Code', 'Project Name', 'District', 'Target Date', 'Status', 'Progress %']
        rows = [
            [
                p.project_code, p.name, p.district, str(p.target_completion_date or '-'),
                p.get_status_display(), f'{p.progress_percent}%',
            ]
            for p in AcquisitionProject.objects.all() if p.is_delayed
        ]
    return title, headers, rows


@role_required('ADMIN', 'MONITORING', 'OFFICER')
def export_report(request, report_type, fmt):
    """Export any of the 8 reports as CSV or PDF."""
    title, headers, rows = _get_report_data(report_type)
    timestamp = timezone.now().strftime('%Y%m%d_%H%M')

    if fmt == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{report_type}_report_{timestamp}.csv"'
        writer = csv.writer(response)
        writer.writerow([title])
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row)
        return response

    pdf_bytes = generate_table_pdf(
        title=title,
        headers=headers,
        rows=rows,
        subtitle=f'Generated on {timezone.now():%Y-%m-%d %H:%M UTC}',
    )
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{report_type}_report_{timestamp}.pdf"'
    return response
