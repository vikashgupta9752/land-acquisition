from datetime import date
from decimal import Decimal
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from accounts.models import UserProfile
from compensation.models import Compensation, Payment
from land_records.models import Landowner, LandRecord
from notifications.models import Notification
from objections.models import Objection
from projects.models import AcquisitionProject, Department
from surveys.models import SurveyAssignment


class EndToEndWorkflowTests(TestCase):
    """Verify all 5 role-based panels, permissions, reports, and the 12-step workflow."""

    def setUp(self):
        self.dept = Department.objects.create(name='Highways Dept', code='NHAI')
        self.admin = self._create_user('adm', 'Pass@123', 'ADMIN')
        self.officer = self._create_user('off', 'Pass@123', 'OFFICER')
        self.surveyor = self._create_user('srv', 'Pass@123', 'SURVEYOR')
        self.monitor = self._create_user('mon', 'Pass@123', 'MONITORING')
        self.citizen = self._create_user('cit', 'Pass@123', 'LANDOWNER')
        self.other_citizen = self._create_user('cit2', 'Pass@123', 'LANDOWNER')

        self.landowner = Landowner.objects.create(
            user=self.citizen,
            full_name='Test Citizen',
            phone='9999999999',
            address='Test Village',
            village='Shirur',
            district='Pune',
        )
        self.other_landowner = Landowner.objects.create(
            user=self.other_citizen,
            full_name='Other Citizen',
            phone='8888888888',
            address='Other Village',
            village='Shirur',
            district='Pune',
        )

    def _create_user(self, username, password, role):
        user = User.objects.create_user(username=username, password=password, email=f'{username}@test.gov')
        UserProfile.objects.create(user=user, role=role, department=self.dept)
        return user

    def test_role_access_control(self):
        c = Client()
        c.login(username='cit', password='Pass@123')
        # Landowner cannot access Admin or Officer dashboards
        resp_admin = c.get(reverse('accounts:admin_dashboard'))
        self.assertEqual(resp_admin.status_code, 302)
        resp_officer = c.get(reverse('projects:officer_dashboard'))
        self.assertEqual(resp_officer.status_code, 302)
        # Landowner can access their own dashboard
        resp_own = c.get(reverse('land_records:landowner_dashboard'))
        self.assertEqual(resp_own.status_code, 200)

    def test_complete_12_step_acquisition_workflow(self):
        c = Client()

        # Step 1: Officer creates project
        c.login(username='off', password='Pass@123')
        resp = c.post(reverse('projects:project_create'), {
            'project_code': 'HW-2026-99',
            'name': 'Expressway Demo',
            'purpose': 'Highway Expansion',
            'department': self.dept.id,
            'assigned_officer': self.officer.id,
            'state': 'Maharashtra',
            'district': 'Pune',
            'taluka': 'Shirur',
            'village': 'Shirur',
            'required_area_acres': '5.00',
            'latitude': '18.823500',
            'longitude': '74.374200',
            'start_date': date.today().isoformat(),
        })
        self.assertEqual(resp.status_code, 302)
        project = AcquisitionProject.objects.get(project_code='HW-2026-99')

        # Step 2: Officer registers land record
        resp = c.post(reverse('land_records:create'), {
            'project': project.id,
            'landowner': self.landowner.id,
            'survey_number': '501/A',
            'plot_number': '9',
            'village': 'Shirur',
            'district': 'Pune',
            'area_acres': '2.00',
            'land_type': 'AGRICULTURAL',
            'ownership_type': 'SOLE',
        })
        self.assertEqual(resp.status_code, 302)
        lr = LandRecord.objects.get(survey_number='501/A', plot_number='9')

        # Step 3: Officer assigns survey
        resp = c.post(reverse('surveys:assign'), {
            'land_record': lr.id,
            'surveyor': self.surveyor.id,
            'instructions': 'Verify boundary',
        })
        self.assertEqual(resp.status_code, 302)
        assignment = SurveyAssignment.objects.get(land_record=lr)

        # Step 4: Surveyor submits report
        c.login(username='srv', password='Pass@123')
        # Valid 1x1 PNG bytes for ImageField upload test
        png_bytes = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0'
            b'\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        photo = SimpleUploadedFile('site.png', png_bytes, content_type='image/png')
        resp = c.post(reverse('surveys:detail', args=[assignment.id]), {
            'action': 'submit_report',
            'actual_area_acres': '2.00',
            'verified_land_type': 'Agricultural',
            'current_land_usage': 'Crop land',
            'boundary_verified': 'on',
            'inspection_date': date.today().isoformat(),
            'inspection_remarks': 'All clear',
            'photo_1': photo,
        })
        self.assertEqual(resp.status_code, 302)
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, 'SUBMITTED')

        # Step 5, 6, 7: Officer verifies survey, calculates compensation, publishes notification
        c.login(username='off', password='Pass@123')
        c.post(reverse('surveys:detail', args=[assignment.id]), {
            'action': 'verify',
            'officer_remarks': 'Verified OK',
        })
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, 'VERIFIED')

        c.post(reverse('compensation:calculate'), {
            'land_record': lr.id,
            'land_area_acres': '2.00',
            'rate_per_acre': '1000000.00',
            'solatium_percent': '100.00',
            'structure_compensation': '0.00',
            'tree_crop_compensation': '0.00',
            'interest_amount': '0.00',
            'other_allowance': '0.00',
        })
        comp = Compensation.objects.get(land_record=lr)
        self.assertEqual(comp.base_land_value, Decimal('2000000.00'))
        self.assertEqual(comp.proposed_compensation, Decimal('4000000.00'))

        c.post(reverse('projects:publish_notification', args=[project.id]), {
            'notice_number': 'SEC-11/99',
            'title': 'Highway Notice',
            'message': 'Official acquisition notice.',
        })
        self.assertTrue(Notification.objects.filter(project=project, is_official_notice=True).exists())

        # Step 8: Citizen submits objection (and cannot view other citizen's land)
        c.login(username='cit2', password='Pass@123')
        self.assertEqual(c.get(reverse('land_records:detail', args=[lr.id])).status_code, 302)

        c.login(username='cit', password='Pass@123')
        self.assertEqual(c.get(reverse('land_records:detail', args=[lr.id])).status_code, 200)
        c.post(reverse('objections:submit'), {
            'land_record': lr.id,
            'subject': 'Rate review',
            'category': 'VALUATION',
            'description': 'Please check market rate.',
        })
        obj = Objection.objects.get(land_record=lr)

        # Step 9, 10, 11: Officer reviews objection, approves compensation, records payment & possession
        c.login(username='off', password='Pass@123')
        c.post(reverse('objections:detail', args=[obj.id]), {
            'status': 'APPROVED',
            'officer_remarks': 'Revised and approved.',
        })
        c.post(reverse('compensation:approve', args=[comp.id]), {
            'approved_compensation': '4200000.00',
            'valuation_remarks': 'Approved with solatium.',
        })
        c.post(reverse('compensation:payment_record', args=[comp.id]), {
            'amount': '4200000.00',
            'payment_mode': 'DBT',
            'transaction_reference': 'TXN-999',
            'payment_date': date.today().isoformat(),
            'status': 'PAID',
        })
        self.assertTrue(Payment.objects.filter(compensation=comp, status='PAID').exists())

        c.post(reverse('land_records:record_possession', args=[lr.id]), {
            'possession_date': date.today().isoformat(),
            'witness_names': 'Village Officer',
            'mark_acquisition_completed': 'on',
            'remarks': 'Handed over',
        })
        project.refresh_from_db()
        self.assertEqual(project.acquired_area_acres, Decimal('2.00'))

        # Step 12: Monitoring dashboard + CSV/PDF export
        c.login(username='mon', password='Pass@123')
        self.assertEqual(c.get(reverse('monitoring:dashboard')).status_code, 200)
        csv_resp = c.get(reverse('monitoring:export_report', args=['projects', 'csv']))
        self.assertEqual(csv_resp.status_code, 200)
        self.assertIn(b'HW-2026-99', csv_resp.content)

        pdf_resp = c.get(reverse('monitoring:export_report', args=['projects', 'pdf']))
        self.assertEqual(pdf_resp.status_code, 200)
        self.assertTrue(pdf_resp.content.startswith(b'%PDF-1.4'))
