"""Shared constants for land acquisition statuses and roles."""

ACQUISITION_STATUS_CHOICES = [
    ('PROJECT_CREATED', 'Project Created'),
    ('LAND_REGISTERED', 'Land Registered'),
    ('SURVEY_ASSIGNED', 'Survey Assigned'),
    ('SURVEY_IN_PROGRESS', 'Survey In Progress'),
    ('SURVEY_COMPLETED', 'Survey Completed'),
    ('SURVEY_VERIFIED', 'Survey Verified'),
    ('NOTIFICATION_PUBLISHED', 'Notification Published'),
    ('OBJECTION_SUBMITTED', 'Objection Submitted'),
    ('OBJECTION_UNDER_REVIEW', 'Objection Under Review'),
    ('COMPENSATION_PROPOSED', 'Compensation Proposed'),
    ('COMPENSATION_APPROVED', 'Compensation Approved'),
    ('PAYMENT_PENDING', 'Payment Pending'),
    ('PAYMENT_COMPLETED', 'Payment Completed'),
    ('POSSESSION_COMPLETED', 'Possession Completed'),
    ('ACQUISITION_COMPLETED', 'Acquisition Completed'),
]

STATUS_ORDER = {code: idx + 1 for idx, (code, _) in enumerate(ACQUISITION_STATUS_CHOICES)}

STATUS_BADGE_MAP = {
    'PROJECT_CREATED': 'secondary',
    'LAND_REGISTERED': 'info',
    'SURVEY_ASSIGNED': 'primary',
    'SURVEY_IN_PROGRESS': 'warning',
    'SURVEY_COMPLETED': 'info',
    'SURVEY_VERIFIED': 'success',
    'NOTIFICATION_PUBLISHED': 'primary',
    'OBJECTION_SUBMITTED': 'danger',
    'OBJECTION_UNDER_REVIEW': 'warning',
    'COMPENSATION_PROPOSED': 'info',
    'COMPENSATION_APPROVED': 'success',
    'PAYMENT_PENDING': 'warning',
    'PAYMENT_COMPLETED': 'success',
    'POSSESSION_COMPLETED': 'primary',
    'ACQUISITION_COMPLETED': 'success',
}

ROLE_CHOICES = [
    ('ADMIN', 'Administrator'),
    ('OFFICER', 'Government Officer'),
    ('SURVEYOR', 'Surveyor'),
    ('LANDOWNER', 'Landowner / Citizen'),
    ('MONITORING', 'Senior Monitoring Official'),
]
