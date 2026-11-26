from notifications.models import Notification
from projects.models import StatusHistory


def create_notification(
    recipient,
    title,
    message,
    notification_type='PROJECT_UPDATE',
    project=None,
    is_official_notice=False,
    notice_number='',
    attachment=None,
    created_by=None,
):
    """Create an internal notification for a user."""
    return Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message,
        notification_type=notification_type,
        project=project,
        is_official_notice=is_official_notice,
        notice_number=notice_number,
        attachment=attachment,
        created_by=created_by,
    )


def record_status_change(
    project,
    new_status,
    updated_by,
    land_record=None,
    remarks='',
    is_exception=False,
    exception_reason='',
):
    """Update project/land record status and persist an immutable StatusHistory entry."""
    previous_status = land_record.acquisition_status if land_record else project.status
    if land_record:
        land_record.acquisition_status = new_status
        if new_status in ('POSSESSION_COMPLETED', 'ACQUISITION_COMPLETED'):
            land_record.is_acquired = True
        land_record.save(update_fields=['acquisition_status', 'is_acquired', 'updated_at'])

    if not land_record or new_status == 'ACQUISITION_COMPLETED':
        project.status = new_status
        project.save(update_fields=['status', 'updated_at'])

    return StatusHistory.objects.create(
        project=project,
        land_record=land_record,
        previous_status=previous_status,
        status=new_status,
        remarks=remarks,
        is_exception=is_exception,
        exception_reason=exception_reason,
        updated_by=updated_by,
    )
