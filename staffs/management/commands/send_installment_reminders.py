from datetime import timedelta
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand
from django.db.models import Sum
from django.utils import timezone
from courses.models import Enrollment
from payments.models import Payment
from students.models import Student
from staffs.utils import send_sms_notification


class Command(BaseCommand):
    help = "Send SMS reminders for upcoming installment payments"

    def handle(self, *args, **options):
        today = timezone.now().date()
        reminder_days = 7

        sent_count = 0
        skipped_count = 0

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
                skipped_count += 1
                continue

            final_fee = enrollment.final_course_fee or Decimal('0.00')
            installments = enrollment.number_of_installments or 1

            if installments <= 0 or final_fee <= 0:
                skipped_count += 1
                continue

            installment_amount = final_fee / installments

            paid_amount = Payment.objects.filter(
                student=student_profile,
                course=course,
                status='PAID'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            remaining_balance = final_fee - paid_amount

            if remaining_balance <= 0:
                skipped_count += 1
                continue

            paid_installments = int(paid_amount // installment_amount)

            if paid_installments >= installments:
                skipped_count += 1
                continue

            next_installment_no = paid_installments + 1

            # Every 2 months: Jan, Mar, May...
            next_due_date = enrollment.enrolled_date + relativedelta(
                months=(next_installment_no - 1) * 2
            )

            show_from_date = next_due_date - timedelta(days=reminder_days)

            if today < show_from_date:
                skipped_count += 1
                continue

            amount_due_now = installment_amount
            if amount_due_now > remaining_balance:
                amount_due_now = remaining_balance

            phone = student_user.phone

            if not phone:
                skipped_count += 1
                continue

            sms_message = (
                f"Payment reminder: {course.course_name}. "
                f"Installment {next_installment_no}/{installments} "
                f"of Rs. {amount_due_now:.2f} is due on {next_due_date}. "
                f"Balance: Rs. {remaining_balance:.2f}."
            )

            success = send_sms_notification(phone, sms_message)

            if success:
                sent_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"SMS sent to {student_user.username} - {course.course_name}"
                    )
                )
            else:
                skipped_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"SMS failed for {student_user.username} - {course.course_name}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Reminder job completed. Sent: {sent_count}, Skipped: {skipped_count}"
            )
        )