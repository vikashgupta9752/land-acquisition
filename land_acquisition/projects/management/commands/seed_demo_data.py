from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import AuditLog, UserProfile
from compensation.models import Compensation, Payment
from land_records.models import Landowner, LandRecord, PossessionRecord
from notifications.models import Notification
from objections.models import Objection
from projects.models import AcquisitionProject, Department, StatusHistory
from surveys.models import SurveyAssignment, SurveyReport


class Command(BaseCommand):
    help = 'Seed realistic demonstration data for all 5 panels and the 12-step workflow.'

    def handle(self, *args, **options):
        self.stdout.write('Seeding NLAMS demonstration data...')

        # 1. Departments
        nhai, _ = Department.objects.get_or_create(
            code='NHAI',
            defaults={
                'name': 'National Highways Authority of India',
                'head_name': 'Shri R. K. Deshmukh',
                'contact_email': 'land.nhai@gov.in',
            },
        )
        rail, _ = Department.objects.get_or_create(
            code='IRCON',
            defaults={
                'name': 'Ministry of Railways - Corridor Division',
                'head_name': 'Smt. Meera Nair',
                'contact_email': 'corridor.rail@gov.in',
            },
        )

        # 2. Users for all 5 roles
        def make_user(username, password, first, last, role, dept=None, emp_id='', desig=''):
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'first_name': first, 'last_name': last, 'email': f'{username}@nlams.gov.in'},
            )
            if created:
                user.set_password(password)
                if role == 'ADMIN':
                    user.is_staff = True
                    user.is_superuser = True
                user.save()
            UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    'role': role,
                    'department': dept,
                    'employee_id': emp_id,
                    'designation': desig,
                    'phone': '9876543210',
                },
            )
            return user

        admin_user = make_user('admin', 'Admin@123', 'System', 'Administrator', 'ADMIN', nhai, 'ADM-001', 'System Controller')
        officer1 = make_user('officer1', 'Officer@123', 'Rajesh', 'Kulkarni', 'OFFICER', nhai, 'OFF-101', 'Special Land Acquisition Officer')
        surveyor1 = make_user('surveyor1', 'Survey@123', 'Amit', 'Patil', 'SURVEYOR', nhai, 'SRV-201', 'Senior Land Surveyor')
        monitor1 = make_user('monitor1', 'Monitor@123', 'Dr. Sunita', 'Rao', 'MONITORING', nhai, 'MON-301', 'Joint Secretary (Monitoring)')
        citizen1 = make_user('citizen1', 'Citizen@123', 'Ramesh', 'Shinde', 'LANDOWNER', None, '', 'Citizen')
        citizen2 = make_user('citizen2', 'Citizen@123', 'Suresh', 'Jadhav', 'LANDOWNER', None, '', 'Citizen')

        # 3. Landowners
        lo1, _ = Landowner.objects.get_or_create(
            user=citizen1,
            defaults={
                'full_name': 'Ramesh Tukaram Shinde',
                'father_or_spouse_name': 'Tukaram Shinde',
                'aadhaar_last4': '4821',
                'phone': '9822001122',
                'email': 'ramesh.shinde@example.com',
                'address': 'At Post Shirur, Taluka Shirur, Pune',
                'village': 'Shirur',
                'district': 'Pune',
                'bank_account_number': 'XXXX-XXXX-8921',
                'ifsc_code': 'SBIN0001234',
            },
        )
        lo2, _ = Landowner.objects.get_or_create(
            user=citizen2,
            defaults={
                'full_name': 'Suresh Baburao Jadhav',
                'father_or_spouse_name': 'Baburao Jadhav',
                'aadhaar_last4': '7734',
                'phone': '9822003344',
                'email': 'suresh.jadhav@example.com',
                'address': 'At Post Ranjangaon, Pune',
                'village': 'Ranjangaon',
                'district': 'Pune',
                'bank_account_number': 'XXXX-XXXX-5510',
                'ifsc_code': 'MAHB0000456',
            },
        )

        # 4. Projects (one active, one delayed for monitoring demonstration)
        proj1, _ = AcquisitionProject.objects.get_or_create(
            project_code='NHAI-2026-001',
            defaults={
                'name': 'Pune-Nashik 6-Lane Express Highway Expansion',
                'purpose': 'Widening of National Highway Corridor for Freight & Passenger Mobility',
                'department': nhai,
                'assigned_officer': officer1,
                'state': 'Maharashtra',
                'district': 'Pune',
                'taluka': 'Shirur',
                'village': 'Shirur',
                'required_area_acres': Decimal('15.00'),
                'acquired_area_acres': Decimal('2.50'),
                'latitude': Decimal('18.823500'),
                'longitude': Decimal('74.374200'),
                'status': 'COMPENSATION_APPROVED',
                'start_date': date.today() - timedelta(days=90),
                'target_completion_date': date.today() + timedelta(days=120),
                'created_by': officer1,
            },
        )
        proj2, _ = AcquisitionProject.objects.get_or_create(
            project_code='IRCON-2025-014',
            defaults={
                'name': 'Western Dedicated Freight Rail Spur',
                'purpose': 'New Railway Logistics Terminal & Track Alignment',
                'department': rail,
                'assigned_officer': officer1,
                'state': 'Maharashtra',
                'district': 'Nashik',
                'taluka': 'Sinnar',
                'village': 'Musalgaon',
                'required_area_acres': Decimal('10.00'),
                'acquired_area_acres': Decimal('0.00'),
                'latitude': Decimal('19.845000'),
                'longitude': Decimal('74.012000'),
                'status': 'OBJECTION_UNDER_REVIEW',
                'start_date': date.today() - timedelta(days=200),
                'target_completion_date': date.today() - timedelta(days=15),  # Intentionally delayed
                'created_by': officer1,
            },
        )

        # 5. Land Records
        lr1, _ = LandRecord.objects.get_or_create(
            project=proj1,
            survey_number='104/A',
            plot_number='12',
            defaults={
                'landowner': lo1,
                'khata_number': 'KH-451',
                'village': 'Shirur',
                'taluka': 'Shirur',
                'district': 'Pune',
                'area_acres': Decimal('2.50'),
                'land_type': 'AGRICULTURAL',
                'ownership_type': 'SOLE',
                'current_usage': 'Sugarcane Cultivation',
                'latitude': Decimal('18.825100'),
                'longitude': Decimal('74.376500'),
                'acquisition_status': 'ACQUISITION_COMPLETED',
                'possession_status': 'TAKEN_OVER',
                'is_acquired': True,
                'created_by': officer1,
            },
        )
        lr2, _ = LandRecord.objects.get_or_create(
            project=proj1,
            survey_number='105/B',
            plot_number='18',
            defaults={
                'landowner': lo2,
                'khata_number': 'KH-489',
                'village': 'Ranjangaon',
                'taluka': 'Shirur',
                'district': 'Pune',
                'area_acres': Decimal('3.00'),
                'land_type': 'AGRICULTURAL',
                'ownership_type': 'JOINT',
                'current_usage': 'Seasonal Maize',
                'latitude': Decimal('18.754000'),
                'longitude': Decimal('74.245000'),
                'acquisition_status': 'COMPENSATION_PROPOSED',
                'created_by': officer1,
            },
        )
        lr3, _ = LandRecord.objects.get_or_create(
            project=proj2,
            survey_number='22/1',
            plot_number='04',
            defaults={
                'landowner': lo1,
                'khata_number': 'KH-901',
                'village': 'Musalgaon',
                'taluka': 'Sinnar',
                'district': 'Nashik',
                'area_acres': Decimal('1.75'),
                'land_type': 'BARREN',
                'ownership_type': 'SOLE',
                'current_usage': 'Unused Plot',
                'latitude': Decimal('19.847200'),
                'longitude': Decimal('74.015500'),
                'acquisition_status': 'SURVEY_ASSIGNED',
                'created_by': officer1,
            },
        )

        # 6. Surveys
        sa1, _ = SurveyAssignment.objects.get_or_create(
            land_record=lr1,
            project=proj1,
            surveyor=surveyor1,
            defaults={'assigned_by': officer1, 'status': 'VERIFIED', 'officer_remarks': 'Measurements verified.'},
        )
        SurveyReport.objects.get_or_create(
            assignment=sa1,
            defaults={
                'actual_area_acres': Decimal('2.50'),
                'verified_land_type': 'Agricultural',
                'current_land_usage': 'Irrigated Sugarcane',
                'inspection_date': date.today() - timedelta(days=45),
                'inspection_remarks': 'Boundary stones intact. No encroachment.',
                'submitted_by': surveyor1,
                'verified_by': officer1,
                'verified_at': timezone.now() - timedelta(days=40),
            },
        )
        SurveyAssignment.objects.get_or_create(
            land_record=lr3,
            project=proj2,
            surveyor=surveyor1,
            defaults={
                'assigned_by': officer1,
                'status': 'ASSIGNED',
                'due_date': date.today() + timedelta(days=7),
                'instructions': 'Verify north boundary and check for borewell.',
            },
        )

        # 7. Compensation & Payment
        comp1, _ = Compensation.objects.get_or_create(
            land_record=lr1,
            defaults={
                'project': proj1,
                'land_area_acres': Decimal('2.50'),
                'rate_per_acre': Decimal('1000000.00'),
                'solatium_percent': Decimal('100.00'),
                'structure_compensation': Decimal('150000.00'),
                'approved_compensation': Decimal('5150000.00'),
                'status': 'DISBURSED',
                'calculated_by': officer1,
                'approved_by': officer1,
                'approved_at': timezone.now() - timedelta(days=20),
            },
        )
        Payment.objects.get_or_create(
            compensation=comp1,
            landowner=lo1,
            defaults={
                'transaction_reference': 'DBT-NHAI-2026-88412',
                'amount': Decimal('5150000.00'),
                'payment_mode': 'DBT',
                'payment_date': date.today() - timedelta(days=10),
                'status': 'PAID',
                'processed_by': officer1,
            },
        )
        Compensation.objects.get_or_create(
            land_record=lr2,
            defaults={
                'project': proj1,
                'land_area_acres': Decimal('3.00'),
                'rate_per_acre': Decimal('1200000.00'),
                'solatium_percent': Decimal('100.00'),
                'status': 'PROPOSED',
                'calculated_by': officer1,
            },
        )

        # 8. Possession Record
        PossessionRecord.objects.get_or_create(
            land_record=lr1,
            defaults={
                'project': proj1,
                'possession_date': date.today() - timedelta(days=5),
                'handover_officer': officer1,
                'witness_names': 'Gram Sevak Shirur, Talathi Shirur',
                'remarks': 'Peaceful possession handed over.',
                'status': 'COMPLETED',
            },
        )

        # 9. Objection
        Objection.objects.get_or_create(
            land_record=lr2,
            project=proj1,
            landowner=lo2,
            subject='Request for Market Rate Revision',
            defaults={
                'category': 'VALUATION',
                'description': 'Adjacent highway frontage plots have higher circle rate; kindly review.',
                'status': 'UNDER_REVIEW',
                'officer_remarks': 'Forwarded to District Valuation Committee.',
                'reviewed_by': officer1,
            },
        )

        # 10. Official Notification & Personal Alert
        Notification.objects.get_or_create(
            project=proj1,
            notice_number='SEC-11/2026/NHAI-01',
            recipient=None,
            defaults={
                'is_official_notice': True,
                'title': 'Section 11 Preliminary Acquisition Notification - Pune-Nashik Highway',
                'message': 'All affected landowners in Shirur & Ranjangaon may inspect valuation schedules and file objections within 30 days.',
                'notification_type': 'OFFICIAL_NOTICE',
                'created_by': officer1,
            },
        )
        Notification.objects.get_or_create(
            recipient=citizen1,
            title='Compensation Disbursed (₹51,50,000)',
            message='Your compensation for Survey 104/A Plot 12 has been credited via DBT.',
            notification_type='PAYMENT_UPDATE',
            project=proj1,
            created_by=officer1,
        )

        StatusHistory.objects.get_or_create(
            project=proj1,
            land_record=lr1,
            status='ACQUISITION_COMPLETED',
            defaults={'remarks': 'Full workflow completed.', 'updated_by': officer1},
        )
        AuditLog.objects.get_or_create(
            user=admin_user,
            action='DEMO_SEED_COMPLETED',
            model_name='System',
            details='Seeded sample data for all 5 panels.',
        )

        self.stdout.write(self.style.SUCCESS('Demo data seeded successfully!'))
