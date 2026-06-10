from accounts.decorators import role_required
from django.shortcuts import redirect, get_object_or_404
from courses.models import Course, Enrollment
from decimal import Decimal
from django.db.models import Sum
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from students.models import Student
from courses.models import Enrollment
from payments.models import Payment
from learning.models import CourseNote, Assignment, AssignmentSubmission
from django.utils import timezone
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from results.models import ExamResult
from results.models import Exam, ExamAssignment, ExamAssignmentSubmission

@login_required
def dashboard_redirect(request):
    user = request.user
    if user.is_superuser or user.role == 'ADMIN':
        return redirect('admin_dashboard')
    elif user.role == 'STAFF':
        return redirect('staff_dashboard')
    elif user.role == 'LECTURER':
        return redirect('lecturer_dashboard')
    elif user.role == 'STUDENT':
        return redirect('student_dashboard')
    return redirect('login')

@login_required
@role_required('ADMIN')
def admin_dashboard(request):
    return render(request, 'dashboard/admin_dashboard.html')

@login_required
@role_required('LECTURER')
def lecturer_dashboard(request):
    return render(request, 'dashboard/lecturer_dashboard.html')

def is_student(user):
    return user.is_authenticated and user.role == 'STUDENT'

@login_required
@user_passes_test(is_student)
def student_dashboard(request):
    try:
        student_profile = request.user.student_profile
    except Student.DoesNotExist:
        return redirect('student_create')

    enrollments = Enrollment.objects.filter(
        student=request.user
    ).select_related(
        'course'
    ).prefetch_related(
        'course__lecturers',
        'course__lecturers__user'
    )

    today = timezone.now()
    deadline_limit = today + timedelta(days=7)
    enrolled_courses = [enrollment.course for enrollment in enrollments]

    submitted_assignment_ids = AssignmentSubmission.objects.filter(
        student=request.user
    ).values_list('assignment_id', flat=True)

    upcoming_deadlines = Assignment.objects.filter(
        course__in=enrolled_courses,
        deadline__gte=today,
        deadline__lte=deadline_limit
    ).exclude(
        id__in=submitted_assignment_ids
    ).select_related('course').order_by('deadline')

    course_details = []

    total_fee = Decimal('0.00')
    total_paid = Decimal('0.00')

    for enrollment in enrollments:
        course = enrollment.course

        paid_amount = Payment.objects.filter(
            student=student_profile,
            course=course,
            status='PAID'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        final_fee = enrollment.final_course_fee or Decimal('0.00')
        balance = final_fee - paid_amount

        notes = CourseNote.objects.filter(
            course=course
        ).order_by('-uploaded_at')

        payments = Payment.objects.filter(
            student=student_profile,
            course=course
        ).order_by('-id')

        assignment_exams = ExamAssignment.objects.filter(
            exam__course=course,
            exam__exam_type='ASSIGNMENT'
        ).select_related(
            'exam',
            'exam__course'
        ).order_by('-deadline')

        assignment_exam_details = []

        for assignment in assignment_exams:
            submission = ExamAssignmentSubmission.objects.filter(
                assignment=assignment,
                student=student_profile
            ).first()

            assignment_exam_details.append({
                'assignment': assignment,
                'submission': submission,
            })

        course_exam_results_qs = ExamResult.objects.filter(
            student__user=request.user,

            exam__course_id=course.id
        ).select_related(
            'exam',
            'exam__course'
        ).order_by('exam__exam_date')

        course_exam_results = list(course_exam_results_qs)

        course_total_results = len(course_exam_results)
        course_passed = 0
        course_failed = 0
        course_total_percentage = 0

        for result in course_exam_results:
            course_total_percentage += result.percentage

            if result.status == 'PASS':
                course_passed += 1
            else:
                course_failed += 1

        course_average = 0

        if course_total_results > 0:
            course_average = round(
                course_total_percentage / course_total_results,
                2
            )

        total_fee += final_fee
        total_paid += paid_amount

        course_details.append({
            'enrollment': enrollment,
            'course': course,
            'lecturers': course.lecturers.all(),
            'notes': notes,
            'assignment_exam_details': assignment_exam_details,
            'payments': payments,

            'course_exam_results': course_exam_results,
            'course_total_results': course_total_results,
            'course_passed': course_passed,
            'course_failed': course_failed,
            'course_average': course_average,

            'final_fee': final_fee,
            'paid_amount': paid_amount,
            'balance': balance,
        })

    total_balance = total_fee - total_paid

    today_date = timezone.now().date()
    reminder_days = 7

    installment_reminders = []

    for enrollment in enrollments:
        course = enrollment.course
        final_fee = enrollment.final_course_fee or Decimal('0.00')
        installments = enrollment.number_of_installments or 1

        if installments <= 0 or final_fee <= 0:
            continue

        installment_amount = final_fee / installments

        paid_amount = Payment.objects.filter(
            student=student_profile,
            course=course,
            status='PAID'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        remaining_balance = final_fee - paid_amount

        if remaining_balance <= 0:
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

        show_from_date = next_due_date - timedelta(days=reminder_days)

        if today_date >= show_from_date:
            installment_reminders.append({
                'course': course,
                'installment_no': next_installment_no,
                'total_installments': installments,
                'installment_amount': installment_amount,
                'next_due_date': next_due_date,
                'amount_due_now': amount_due_now,
                'remaining_balance': remaining_balance,
                'paid_amount': paid_amount,
            })

    context = {
        'student': student_profile,
        'course_details': course_details,
        'total_courses': enrollments.count(),
        'total_fee': total_fee,
        'total_paid': total_paid,
        'total_balance': total_balance,
        'upcoming_deadlines': upcoming_deadlines,
        'installment_reminders': installment_reminders,
    }

    return render(request, 'dashboard/student_dashboard.html', context)