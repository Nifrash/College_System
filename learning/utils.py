from django.core.mail import send_mail
from courses.models import Enrollment
from students.models import Student
# from sms.utils import send_sms

def notify_course_students(course, subject, email_message, sms_message):

    enrollments = Enrollment.objects.filter(course=course)

    for enrollment in enrollments:

        try:
            student = enrollment.student.student_profile

            if student.user.email:
                send_mail(
                    subject,
                    email_message,
                    None,
                    [student.user.email],
                    fail_silently=True
                )

            if student.phone:
                send_sms(
                    student.phone,
                    sms_message
                )

        except Exception:
            pass