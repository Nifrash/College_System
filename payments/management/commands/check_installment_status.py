from datetime import timedelta
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand
from django.db.models import Sum
from django.utils import timezone
from courses.models import Enrollment
from payments.models import Payment
from students.models import Student
from staffs.utils import send_email_notification, send_sms_notification


class Command(BaseCommand):
    help = "Check installment due payments, send reminders, suspend and reactivate students"

    def handle(self, *args, **options):
        today = timezone.now().date()
        now = timezone.now()

        reminder_days_before = 7
        grace_days_after_due = 0

        reminded = 0
        suspended = 0
        reactivated = 0
        skipped = 0

        enrollments = Enrollment.objects.select_related(
            'student',
            'student__student_profile',
            'course'
        )

        for enrollment in enrollments:
            student_user = enrollment.student
            course = enrollment.course

            try:
                student_profile = student_user.student_profile
            except Student.DoesNotExist:
                skipped += 1
                continue

            final_fee = enrollment.final_course_fee or Decimal('0.00')
            installments = enrollment.number_of_installments or 1

            if final_fee <= 0 or installments <= 0:
                skipped += 1
                continue

            installment_amount = final_fee / installments

            paid_amount = Payment.objects.filter(
                student=student_profile,
                course=course,
                status='PAID'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            remaining_balance = final_fee - paid_amount

            # Fully paid: reactivate if suspended
            if remaining_balance <= 0:
                if student_profile.is_suspended:
                    student_profile.is_suspended = False
                    student_profile.suspended_reason = None
                    student_profile.suspended_at = None
                    student_profile.save()

                    student_user.is_active = True
                    student_user.save()

                    reactivated += 1

                    send_email_notification(
                        "Account Reactivated",
                        f"""
Dear {student_user.get_full_name() or student_user.username},

Your account has been reactivated because your payment is now cleared.

Course: {course.course_name}

Thank you.
Europe Campus Management
""",
                        student_user.email
                    )

                    if student_user.phone:
                        send_sms_notification(
                            student_user.phone,
                            f"Your Europe Campus account has been reactivated. Payment cleared for {course.course_name}."
                        )
                continue

            completed_installments = int(paid_amount // installment_amount)

            if completed_installments >= installments:
                continue

            next_installment_no = completed_installments + 1

            amount_paid_towards_next = paid_amount - (
                completed_installments * installment_amount
            )

            amount_due_now = installment_amount - amount_paid_towards_next

            if amount_due_now > remaining_balance:
                amount_due_now = remaining_balance

            next_due_date = enrollment.enrolled_date + relativedelta(
                months=(next_installment_no - 1) * 2
            )

            reminder_start_date = next_due_date - timedelta(days=reminder_days_before)
            suspension_date = next_due_date + timedelta(days=grace_days_after_due)

            # Reminder period
            if reminder_start_date <= today <= next_due_date:
                subject = "Payment Installment Reminder"

                email_message = f"""
Dear {student_user.get_full_name() or student_user.username},

This is a reminder for your upcoming course installment.

Course: {course.course_name}
Installment: {next_installment_no}/{installments}
Due Date: {next_due_date}
Amount Due: {amount_due_now:.2f}
Remaining Balance: {remaining_balance:.2f}

Please make the payment on or before the due date.

Thank you.
Europe Campus Management
"""

                sms_message = (
                    f"Payment Reminder: {course.course_name}. "
                    f"Installment {next_installment_no}/{installments}, "
                    f"Due {next_due_date}, Amount {amount_due_now:.2f}."
                )

                send_email_notification(subject, email_message, student_user.email)

                if student_user.phone:
                    send_sms_notification(student_user.phone, sms_message)

                reminded += 1

            # Suspend if overdue
            if today > suspension_date:
                if not student_profile.is_suspended:
                    student_profile.is_suspended = True
                    student_profile.suspended_reason = (
                        f"Payment overdue for {course.course_name}. "
                        f"Installment {next_installment_no}/{installments} "
                        f"due on {next_due_date}."
                    )
                    student_profile.suspended_at = now
                    student_profile.save()

                    student_user.is_active = False
                    student_user.save()

                    suspended += 1

                    subject = "Student Account Suspended"

                    email_message = f"""
Dear {student_user.get_full_name() or student_user.username},

Your student account has been suspended due to overdue payment.

Course: {course.course_name}
Installment: {next_installment_no}/{installments}
Due Date: {next_due_date}
Amount Due: {amount_due_now:.2f}

Your account will be reactivated automatically once the due payment is recorded.

Thank you.
Europe Campus Management
"""

                    sms_message = (
                        f"Account suspended: payment overdue for {course.course_name}. "
                        f"Amount due {amount_due_now:.2f}. "
                        f"Account will reactivate after payment."
                    )

                    send_email_notification(subject, email_message, student_user.email)

                    if student_user.phone:
                        send_sms_notification(student_user.phone, sms_message)

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Reminded: {reminded}, Suspended: {suspended}, Reactivated: {reactivated}, Skipped: {skipped}"
            )
        )