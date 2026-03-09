from django.test import TestCase
from django.utils import timezone
import datetime

from .models import Student, StudentLoadSlip, LoadSlipSubject, GateEntry, VisitorEntry, VisitorPass, VisitorVisit
from .policy import evaluate_scan


class GatePolicyTests(TestCase):
    def setUp(self):
        # create an active student with course/section so previews include data
        self.student = Student.objects.create(
            student_id="S1",
            first_name="Test",
            last_name="Student",
            account_status=Student.ACCOUNT_STATUS_APPROVED,
            is_active=True,
            course="BST",
            section="A",
        )

    def test_get_user_role_case_insensitive(self):
        """Group names with different capitalization should still yield the role."""
        from gate_analytics.roles import get_user_role
        from django.contrib.auth.models import User, Group
        u = User.objects.create(username='foo')
        # lower-case group
        g1, _ = Group.objects.get_or_create(name='guard')
        u.groups.add(g1)
        self.assertEqual(get_user_role(u), 'guard')
        # uppercase group should also work
        u2 = User.objects.create(username='bar')
        g2, _ = Group.objects.get_or_create(name='Guard')
        u2.groups.add(g2)
        self.assertEqual(get_user_role(u2), 'guard')

    def _make_slip(self, sessions):
        """Helper: sessions is list of (day, start_time, end_time, code)."""
        slip = StudentLoadSlip.objects.create(
            student=self.student,
            school_year="2025-2026",
            semester="1st",
        )
        for day, start, end, code in sessions:
            LoadSlipSubject.objects.create(
                load_slip=slip,
                subject_code=code,
                subject_title="",
                section="",
                units=3,
                day=day,
                start_time=start,
                end_time=end,
            )
        return slip

    def test_in_denied_if_no_class_today(self):
        now = timezone.make_aware(datetime.datetime(2025, 9, 1, 8, 0))
        # no sessions added to slip
        self._make_slip([])
        result = evaluate_scan(self.student, 'IN', now)
        self.assertFalse(result['allowed'])
        self.assertEqual(result['result'], 'DENIED')
        self.assertIn('no classes today', result['message'].lower())

    def test_in_requires_reason_if_not_in_class_but_has_later(self):
        now = timezone.make_aware(datetime.datetime(2025, 9, 1, 9, 0))
        # add a class later at 15:00
        self._make_slip([('Mon', datetime.time(15, 0), datetime.time(16, 0), 'TEST101')])
        result = evaluate_scan(self.student, 'IN', now)
        self.assertFalse(result['allowed'])
        self.assertEqual(result['result'], 'REQUIRE_REASON')
        self.assertIn('not currently in class', result['message'].lower())

    def test_in_allowed_during_class(self):
        now = timezone.make_aware(datetime.datetime(2025, 9, 1, 15, 30))
        self._make_slip([('Mon', datetime.time(15, 0), datetime.time(16, 0), 'TEST101')])
        result = evaluate_scan(self.student, 'IN', now)
        self.assertTrue(result['allowed'])
        self.assertEqual(result['result'], 'SUCCESS')

    def test_export_daily_visits_includes_visitors(self):
        # create a student entry for today and a visitor entry/visit
        from .gate_views import _reports_export_build_data, _local_day_bounds, _reports_export_preview
        today = timezone.localdate()
        day_start, day_end = _local_day_bounds(today)
        # student log
        entry = GateEntry.objects.create(
            timestamp=timezone.now(),
            student=self.student,
            scan_type='IN',
            granted=True,
        )
        # visitor entry
        from .models import VisitorEntry, VisitorPass, VisitorVisit
        ve = VisitorEntry.objects.create(
            visitor_name='Visitor One',
            purpose='Check',
            who_to_visit='Cashier',
        )
        # visitor visit
        vp = VisitorPass.objects.create(code='VIS-001', status=VisitorPass.STATUS_AVAILABLE)
        vv = VisitorVisit.objects.create(
            pass_obj=vp,
            full_name='Visitor Two',
            purpose='Visit',
            department='Cashier',
            checked_in_at=timezone.now(),
            checked_out_at=timezone.now() + datetime.timedelta(hours=1),
        )
        headers, rows = _reports_export_build_data(today, day_start, day_end, 'daily_gate_visits', '', None)
        # header should include new course/section column as well as student id
        self.assertIn('Student ID', headers)
        self.assertIn('Course/Section', headers)
        # first student row should show the course/section value we set
        self.assertTrue(any(isinstance(r, list) and r and r[2] == 'BST A' for r in rows))
        # name formatting should use last, first
        self.assertTrue(any(isinstance(r, list) and r and r[1].startswith('Student,') for r in rows))
        # ensure earliest timestamp comes first
        # only consider rows that are not visitor headers (student rows have numeric datetime strings)
        times = [r[4] for r in rows if len(r) > 4 and r[0] != 'Visitor Name' and r[4]]
        if len(times) > 1:
            self.assertLessEqual(times[0], times[-1])
        # name should be formatted as Last, First
        self.assertTrue(any(isinstance(r, list) and r and r[1].startswith('Student,') for r in rows))
        # and ordering should be oldest-first (first row timestamp <= last row)
        times = [r[3] for r in rows if len(r) > 3 and r[3]]
        if len(times) > 1:
            self.assertLessEqual(times[0], times[-1])
        # rows should contain at least one blank row and a visitor header row
        self.assertTrue(any(isinstance(r, list) and r and r[0] == 'Visitor Name' for r in rows))
        # preview should also handle visitors without crashing and provide type column
        preview = _reports_export_preview(today, day_start, day_end, 'daily_gate_visits', '', None)
        self.assertTrue(any(r.get('Type') == 'Visitor' for r in preview))
        # preview rows should include Course/Section key and our value
        self.assertTrue(any(r.get('Course/Section') == 'BST A' for r in preview))
        # preview name ordering
        self.assertTrue(any(r.get('Name','').startswith('Student,') for r in preview))
        # oldest-first preview
        times = [r.get('In time') for r in preview if r.get('In time')]
        if len(times) > 1:
            self.assertLessEqual(times[0], times[-1])

    def test_event_attendance_filtering(self):
        from .gate_views import _reports_export_preview, _reports_export_build_data, _local_day_bounds
        from .models import Event, EventAttendance, EventCategory
        from django.contrib.auth import get_user_model
        User = get_user_model()
        today = timezone.localdate()
        day_start, day_end = _local_day_bounds(today)
        # create dummy user for category
        cat_user = User.objects.create(username='catuser')
        cat = EventCategory.objects.create(name='Cat', code='C1', priority=1, created_user=cat_user, updated_user=cat_user, status='active')
        # create event and attendance
        ev1 = Event.objects.create(name='Test', category=cat, start_date=today, end_date=today, status='active')
        ev2 = Event.objects.create(name='Other', category=cat, start_date=today, end_date=today, status='active')
        # attendance for both
        a1 = EventAttendance.objects.create(event=ev1, student=self.student, checked_in_at=timezone.now())
        a2 = EventAttendance.objects.create(event=ev2, student=self.student, checked_in_at=timezone.now())
        # preview without event_id returns both events rows
        preview = _reports_export_preview(today, day_start, day_end, 'event_attendance', '', None)
        self.assertTrue(any(r.get('event') == 'Test' for r in preview))
        self.assertTrue(any(r.get('event') == 'Other' for r in preview))
        # preview should also have course/section column with our value
        self.assertTrue(any(r.get('Course/Section') == 'BST A' for r in preview))
        # student name order
        self.assertTrue(any(r.get('name','').startswith('Student,') for r in preview))
        # check ascending order by checked_in_at (preview should now be oldest first)
        times = [r.get('checked_in_at') for r in preview if r.get('checked_in_at')]
        if len(times) > 1:
            self.assertLessEqual(times[0], times[-1])
        # build_data without event_id returns both rows and includes event column
        headers, rows = _reports_export_build_data(today, day_start, day_end, 'event_attendance', '', None)
        self.assertIn('Event', headers)
        self.assertIn('Course/Section', headers)
        self.assertTrue(any(r[0] == 'Test' for r in rows))
        self.assertTrue(any(r[0] == 'Other' for r in rows))
        # first row should have course section value at index 3 (after event,id,name)
        self.assertTrue(any(r[3] == 'BST A' for r in rows if len(r) > 3))
        # build_data should be in ascending time order as well
        times_build = [r[4] for r in rows if len(r) > 4 and r[4]]
        if len(times_build) > 1:
            self.assertLessEqual(times_build[0], times_build[-1])
        # filtering by single event reduces results
        headers2, rows2 = _reports_export_build_data(today, day_start, day_end, 'event_attendance', '', ev1.id)
        self.assertTrue(all(r[0] == 'Test' for r in rows2))

    def test_event_attendance_checkout_and_range(self):
        from .gate_views import _reports_export_preview, _reports_export_build_data, _local_day_bounds
        from .models import EventAttendance, Event, EventCategory
        from django.contrib.auth import get_user_model
        User = get_user_model()
        # setup category/user similar to other event tests
        cat_user = User.objects.create(username='catuser2')
        cat = EventCategory.objects.create(name='Cat2', code='C2', priority=1, created_user=cat_user, updated_user=cat_user, status='active')
        today = timezone.localdate()
        # create event and two attendance records
        ev = Event.objects.create(name='Ranged', category=cat, start_date=today, end_date=today, status='active')
        # create a second student to avoid unique constraint on (student,event)
        student2 = Student.objects.create(
            student_id="S2",
            first_name="Other",
            last_name="Student",
            account_status=Student.ACCOUNT_STATUS_APPROVED,
            is_active=True,
        )
        # attendance with check-in before window but check-out during window
        old_in = timezone.now() - datetime.timedelta(days=2)
        out_in_window = timezone.now()
        a1 = EventAttendance.objects.create(event=ev, student=self.student, participated=True,
                                           checked_in_at=old_in, checked_out_at=out_in_window)
        # attendance with both times inside window (use second student)
        in2 = timezone.now() - datetime.timedelta(hours=1)
        out2 = timezone.now() + datetime.timedelta(hours=1)
        a2 = EventAttendance.objects.create(event=ev, student=student2, participated=True,
                                           checked_in_at=in2, checked_out_at=out2)
        # filter covering today only
        filter_date = today
        day_start, day_end = _local_day_bounds(filter_date)
        # preview should include both and show checked_out values
        preview = _reports_export_preview(filter_date, day_start, day_end, 'event_attendance', '', None)
        self.assertTrue(any(r.get('checked_out_at') == out_in_window for r in preview))
        self.assertTrue(any(r.get('checked_out_at') == out2 for r in preview))
        # preview should also include course/section
        self.assertTrue(any(r.get('Course/Section') == 'BST A' for r in preview))
        # build_data should likewise include both rows with checkout strings
        headers, rows = _reports_export_build_data(filter_date, day_start, day_end, 'event_attendance', '', None)
        self.assertIn('Course/Section', headers)
        self.assertGreaterEqual(len(rows), 2)
        self.assertTrue(any(row[4] != '' for row in rows))

    def test_event_attendance_specific_event_30day_range(self):
        """Preview should include rows when filtering last 30 days + event_id."""
        from .gate_views import _reports_export_preview, _reports_export_build_data, _local_day_bounds
        from .models import EventAttendance, Event, EventCategory
        from django.contrib.auth import get_user_model
        User = get_user_model()
        # create event/category
        cat_user = User.objects.create(username='catuser3')
        cat = EventCategory.objects.create(name='Cat3', code='C3', priority=1, created_user=cat_user, updated_user=cat_user, status='active')
        today = timezone.localdate()
        ev = Event.objects.create(name='Thirty', category=cat, start_date=today, end_date=today, status='active')
        # attendance in the window (has check-in)
        a = EventAttendance.objects.create(event=ev, student=self.student, checked_in_at=timezone.now())
        # also create a second attendance without check timestamps; recorded_at is now
        student2 = Student.objects.create(
            student_id="S3",
            first_name="Sample",
            last_name="User",
            account_status=Student.ACCOUNT_STATUS_APPROVED,
            is_active=True,
        )
        b = EventAttendance.objects.create(event=ev, student=student2)
        # define a 30-day window using helper logic as request would
        filter_date = today - datetime.timedelta(days=29)
        day_start, day_end = _local_day_bounds(filter_date)
        # extend to tomorrow like last_30_days
        day_end = timezone.make_aware(
            datetime.datetime.combine(today + datetime.timedelta(days=1), datetime.time.min),
            timezone.get_current_timezone()
        )
        preview = _reports_export_preview(filter_date, day_start, day_end, 'event_attendance', '', ev.id)
        self.assertTrue(preview, "Expected preview rows for event but got empty")
        # both attendances should be included
        self.assertEqual(len(preview), 2)
        # at least one row should show our student's course/section
        self.assertTrue(any(r.get('Course/Section') == 'BST A' for r in preview))
        # build data also
        headers2, rows2 = _reports_export_build_data(filter_date, day_start, day_end, 'event_attendance', '', ev.id)
        self.assertTrue(rows2)
        self.assertEqual(len(rows2), 2)

    def test_scan_event_qr_endpoint_student(self):
        """POSTing a student ID to scan_event_qr should succeed for current event."""
        from django.urls import reverse
        from .models import Event, EventCategory
        from django.contrib.auth import get_user_model
        User = get_user_model()
        cat_user = User.objects.create(username='scanuser')
        cat_user.set_password('secret')
        cat_user.save()
        # create lowercase guard group so case-insensitive lookup is exercised
        from django.contrib.auth.models import Group
        guard_group, _ = Group.objects.get_or_create(name='guard')
        cat_user.groups.add(guard_group)
        cat_user.save()
        cat = EventCategory.objects.create(name='ScanCat', code='SC', priority=1, created_user=cat_user, updated_user=cat_user, status='active')
        today = timezone.localdate()
        ev = Event.objects.create(name='ScanEvent', category=cat, start_date=today, end_date=today, status='active')
        # login as guard
        from gate_analytics.roles import get_user_role
        self.assertEqual(get_user_role(cat_user), 'guard')
        self.assertTrue(self.client.login(username='scanuser', password='secret'))
        url = reverse('scan_event_qr')
        resp = self.client.post(url, {
            'event_id': ev.id,
            'qr': self.student.student_id,
            'scan_type': 'IN',
            'device_id': 'DEV123',
        })
        self.assertEqual(resp.status_code, 200,
                         f"expected 200 but got {resp.status_code}, body={resp.content!r}")
        data = resp.json()
        self.assertTrue(data.get('ok'))
        self.assertEqual(data.get('result'), 'SUCCESS')
        # second scan should return DUPLICATE but still 200
        resp2 = self.client.post(url, {
            'event_id': ev.id,
            'qr': self.student.student_id,
            'scan_type': 'IN',
            'device_id': 'DEV123',
        })
        self.assertEqual(resp2.status_code, 200,
                         f"expected 200 but got {resp2.status_code}, body={resp2.content!r}")
        data2 = resp2.json()
        self.assertEqual(data2.get('result'), 'DUPLICATE')
        self.assertIn('already checked in', data2.get('message','').lower())

    def test_scan_event_qr_endpoint_token(self):
        """Token-based event scan should also work."""
        from django.urls import reverse
        from .models import Event, EventCategory, EventRegistration
        from django.contrib.auth import get_user_model
        User = get_user_model()
        cat_user = User.objects.create(username='scanuser2')
        cat_user.set_password('secret2')
        cat_user.save()
        from django.contrib.auth.models import Group
        # lowercase guard should succeed now
        guard_group, _ = Group.objects.get_or_create(name='guard')
        cat_user.groups.add(guard_group)
        cat_user.save()
        cat = EventCategory.objects.create(name='ScanCat2', code='SC2', priority=1, created_user=cat_user, updated_user=cat_user, status='active')
        today = timezone.localdate()
        ev = Event.objects.create(name='Secure', category=cat, start_date=today, end_date=today, status='active')
        reg = EventRegistration.objects.create(event=ev, student=self.student, token='TOKEN123', status='active')
        from gate_analytics.roles import get_user_role
        self.assertEqual(get_user_role(cat_user), 'guard')
        self.assertTrue(self.client.login(username='scanuser2', password='secret2'))
        url = reverse('scan_event_qr')
        resp = self.client.post(url, {
            'event_id': ev.id,
            'qr': f'EVT:{ev.id}:{reg.token}',
            'scan_type': 'IN',
            'device_id': 'DEV456',
        })
        self.assertEqual(resp.status_code, 200,
                         f"expected 200 but got {resp.status_code}, body={resp.content!r}")
        data = resp.json()
        self.assertTrue(data.get('ok'))
        self.assertEqual(data.get('result'), 'SUCCESS')

    def test_summary_respects_date_range(self):
        # ensure preview/build total visits use the full day_start/day_end
        from .gate_views import _reports_export_preview, _reports_export_build_data, _local_day_bounds, _granted_visits_count_for_bounds
        today = timezone.localdate()
        # create an entry for today (should be within range)
        GateEntry.objects.create(
            timestamp=timezone.now(),
            student=self.student,
            scan_type='IN',
            granted=True,
        )
        # choose a filter_date one day earlier and extend end to tomorrow
        filter_date = today - datetime.timedelta(days=1)
        day_start, day_end = _local_day_bounds(filter_date)
        # mimic last_7_days/last_30_days behaviour by extending day_end
        day_end = timezone.make_aware(
            datetime.datetime.combine(today + datetime.timedelta(days=1), datetime.time.min),
            timezone.get_current_timezone()
        )
        # baseline expectation using helper
        expected_count = _granted_visits_count_for_bounds(day_start, day_end, daily_gate_only=True)
        self.assertEqual(expected_count, 1)
        # preview should show the same total
        preview = _reports_export_preview(filter_date, day_start, day_end, 'overview_summary', '', None)
        tv = next((r['Value'] for r in preview if r.get('Metric') == 'Total visits'), None)
        self.assertEqual(tv, expected_count)
        # build_data should also include the correct row
        headers, rows = _reports_export_build_data(filter_date, day_start, day_end, 'overview_summary', '', None)
        self.assertIn(['Total visits', expected_count], rows)
