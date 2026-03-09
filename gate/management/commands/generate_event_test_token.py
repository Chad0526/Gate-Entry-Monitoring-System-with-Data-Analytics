"""
Generate test event registration with token for testing event attendance system.
Run: python manage.py generate_event_test_token
"""

from django.core.management.base import BaseCommand
from gate.models import Event, Student, EventRegistration, AttendanceLog


class Command(BaseCommand):
    help = 'Generate test event registration with QR token for testing'

    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write("EVENT ATTENDANCE TOKEN SYSTEM - TEST SETUP")
        self.stdout.write("=" * 60)

        # Get test event
        self.stdout.write("\n1. Finding active event...")
        event = Event.objects.filter(status='active').first()
        if not event:
            self.stdout.write(self.style.WARNING("   No active events found. Creating test event..."))
            # You can create a test event here if needed
            self.stdout.write(self.style.ERROR("   Please create an active event first via admin."))
            return
        
        self.stdout.write(self.style.SUCCESS(f"   ✅ Event: {event.name} (ID: {event.id})"))
        self.stdout.write(f"      Dates: {event.start_date} to {event.end_date}")

        # Get test student
        self.stdout.write("\n2. Finding active student...")
        student = Student.objects.filter(is_active=True).first()
        if not student:
            self.stdout.write(self.style.ERROR("   No active students found. Please create a student first."))
            return
        
        self.stdout.write(self.style.SUCCESS(f"   ✅ Student: {student.get_full_name()} ({student.student_id})"))

        # Create registration
        self.stdout.write("\n3. Creating event registration...")
        reg, created = EventRegistration.objects.get_or_create(
            event=event,
            student=student
        )
        if created or not reg.token:
            reg.token = EventRegistration.generate_token()
            reg.status = 'active'
            reg.save()
            self.stdout.write(self.style.SUCCESS("   ✅ New registration created"))
        else:
            self.stdout.write("   ℹ️  Registration already exists")

        self.stdout.write(f"   Token: {reg.token[:30]}...")
        self.stdout.write(f"   Status: {reg.status}")

        # QR payload
        qr_payload = reg.get_qr_payload()
        self.stdout.write(f"\n4. QR Code Payload:")
        self.stdout.write(f"   {qr_payload}")

        # Test command
        self.stdout.write(f"\n5. Test with curl (PowerShell):")
        self.stdout.write('''
$body = @{
    event_id = "''' + str(event.id) + '''"
    qr = "''' + qr_payload + '''"
    scan_type = "IN"
    device_id = "TEST-SCANNER"
}

Invoke-WebRequest -Uri http://127.0.0.1:8000/gate/scan-event/ `
    -Method POST `
    -Headers @{"X-CSRFToken"="YOUR_CSRF_TOKEN"} `
    -WebSession $session `
    -Body $body
''')

        # Show status
        self.stdout.write(f"\n6. Current Status:")
        self.stdout.write(f"   Checked In:  {reg.checked_in_at or 'Not yet'}")
        self.stdout.write(f"   Checked Out: {reg.checked_out_at or 'Not yet'}")

        # Recent logs
        self.stdout.write(f"\n7. Recent Logs:")
        logs = AttendanceLog.objects.filter(event=event).order_by('-scan_time')[:5]
        if logs.exists():
            for log in logs:
                sid = log.student.student_id if log.student else 'Unknown'
                self.stdout.write(f"   {log.scan_time.strftime('%Y-%m-%d %H:%M')} | {sid} | {log.scan_type} | {log.result}")
        else:
            self.stdout.write("   No logs yet")

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("✅ Test setup complete!"))
        self.stdout.write("=" * 60)
