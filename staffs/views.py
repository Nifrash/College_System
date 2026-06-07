from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from accounts.decorators import role_required
from students.models import Student
from lecturers.models import Lecturer
from courses.models import Course, Enrollment
from payments.models import Payment
from django.http import HttpResponse
from openpyxl import Workbook
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from .utils import send_email_notification, send_sms_notification
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Q
from accounts.models import User
from courses.models import Course
from .forms import StaffClassScheduleForm
from datetime import datetime, timedelta
from decimal import Decimal
from django.db.models import Sum
from learning.models import ClassSchedule


@login_required
@role_required('STAFF')
def staff_class_schedule_list(request):
    course_id = request.GET.get('course')
    lecturer_id = request.GET.get('lecturer')
    query = request.GET.get('q', '').strip()

    schedules = ClassSchedule.objects.select_related(
        'course',
        'lecturer'
    ).order_by('-class_date', 'start_time')

    courses = Course.objects.all().order_by('course_name')
    lecturers = User.objects.filter(role='LECTURER').order_by('first_name', 'username')

    if course_id:
        schedules = schedules.filter(course_id=course_id)

    if lecturer_id:
        schedules = schedules.filter(lecturer_id=lecturer_id)

    if query:
        schedules = schedules.filter(
            Q(course__course_code__icontains=query) |
            Q(course__course_name__icontains=query) |
            Q(lecturer__first_name__icontains=query) |
            Q(lecturer__last_name__icontains=query) |
            Q(lecturer__username__icontains=query) |
            Q(title__icontains=query)
        )

    return render(request, 'staffs/class_schedule_list.html', {
        'schedules': schedules,
        'courses': courses,
        'lecturers': lecturers,
        'selected_course': course_id,
        'selected_lecturer': lecturer_id,
        'query': query,
    })



from .forms import (
    StudentRegistrationForm,
    LecturerRegistrationForm,
    CourseForm,
    AssignCourseForm,
    EnrollmentForm,
    PaymentForm,
)

User = get_user_model()
def generate_username(first_name, last_name):
    base_username = f"{first_name}.{last_name}".lower().replace(" ", "")

    username = base_username
    counter = 1

    while User.objects.filter(username=username).exists():
        username = f"{base_username}{counter}"
        counter += 1

    return username
@login_required
@role_required('STAFF')
def staff_dashboard(request):

    total_expected_amount = Decimal('0.00')
    total_paid_amount = Decimal('0.00')

    course_summary = {}

    enrollments = Enrollment.objects.select_related('course', 'student')

    for enrollment in enrollments:
        course = enrollment.course
        final_fee = enrollment.final_course_fee or Decimal('0.00')

        paid_amount = Payment.objects.filter(
            student__user=enrollment.student,
            course=course,
            status='PAID'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        total_expected_amount += final_fee
        total_paid_amount += paid_amount

        course_key = course.course_name

        if course_key not in course_summary:
            course_summary[course_key] = {
                'expected': Decimal('0.00'),
                'paid': Decimal('0.00'),
                'balance': Decimal('0.00'),
            }

        course_summary[course_key]['expected'] += final_fee
        course_summary[course_key]['paid'] += paid_amount

    total_balance_amount = total_expected_amount - total_paid_amount

    for course_name, data in course_summary.items():
        data['balance'] = data['expected'] - data['paid']

    course_chart_json = []

    for course_name, data in course_summary.items():
        course_obj = Course.objects.filter(course_name=course_name).first()

        course_chart_json.append({
            'course_id': course_obj.id if course_obj else None,
            'course_name': course_name,
            'expected': float(data['expected']),
            'paid': float(data['paid']),
            'balance': float(data['balance']),
        })

        today = timezone.now().date()
        reminder_days = 7

        today_date = timezone.now().date()
        reminder_days = 7

        outstanding_balances = []

        for enrollment in enrollments:
            student_user = enrollment.student
            course = enrollment.course

            try:
                student_profile = student_user.student_profile
            except Student.DoesNotExist:
                continue

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

            if today_date < show_from_date:
                continue

            outstanding_balances.append({
                'student_id': student_profile.student_id,
                'student_name': student_user.get_full_name() or student_user.username,
                'course_code': course.course_code,
                'course_name': course.course_name,
                'final_fee': final_fee,
                'paid_amount': paid_amount,
                'balance': remaining_balance,
                'installment_no': next_installment_no,
                'total_installments': installments,
                'installment_amount': installment_amount,
                'amount_due_now': amount_due_now,
                'next_due_date': next_due_date,
                'show_from_date': show_from_date,
            })

            outstanding_balances.append({
                'student_id': student_profile.student_id,
                'student_name': student_user.get_full_name() or student_user.username,
                'course_code': course.course_code,
                'course_name': course.course_name,
                'final_fee': final_fee,
                'paid_amount': paid_amount,
                'balance': remaining_balance,
                'installment_no': next_installment_no,
                'total_installments': installments,
                'installment_amount': installment_amount,
                'amount_due_now': amount_due_now,
                'next_due_date': next_due_date,
                'show_from_date': show_from_date,
            })

            class_schedule_summary = []

            courses_for_schedule = Course.objects.prefetch_related('lecturers__user')

            for course in courses_for_schedule:
                covered_hours = ClassSchedule.objects.filter(
                    course=course
                ).aggregate(total=Sum('covered_hours'))['total'] or Decimal('0.00')

                total_hours = Decimal(course.total_hours or 0)
                remaining_hours = total_hours - covered_hours

                if remaining_hours < 0:
                    remaining_hours = Decimal('0.00')

                class_schedule_summary.append({
                    'course': course,
                    'total_hours': total_hours,
                    'covered_hours': covered_hours,
                    'remaining_hours': remaining_hours,
                })

            today = timezone.now().date()
            next_3_days = today + timedelta(days=3)

            upcoming_class_schedules = ClassSchedule.objects.select_related('course',  'lecturer'  ).filter(
                class_date__gte=today,
                class_date__lte=next_3_days ).order_by('class_date', 'start_time')

    context = {

        'class_schedule_summary': class_schedule_summary,
        'upcoming_class_schedules': upcoming_class_schedules,
        'total_students': Student.objects.count(),
        'total_lecturers': Lecturer.objects.count(),
        'total_courses': Course.objects.count(),
        'total_enrollments': Enrollment.objects.count(),
        'total_payments': Payment.objects.count(),

        'total_expected_amount': total_expected_amount,
        'total_paid_amount': total_paid_amount,
        'total_balance_amount': total_balance_amount,

        'recent_students': Student.objects.select_related('user').order_by('-id')[:5],
        'recent_payments': Payment.objects.select_related('student', 'student__user', 'course').order_by('-id')[:5],

        'outstanding_balances': outstanding_balances,

        'overall_chart_json': json.dumps({
            'labels': ['Expected Amount', 'Paid Amount', 'Balance Amount'],
            'data': [
                float(total_expected_amount),
                float(total_paid_amount),
                float(total_balance_amount),
            ]
        }, cls=DjangoJSONEncoder),

        'course_chart_json': json.dumps(course_chart_json, cls=DjangoJSONEncoder),

        'course_dropdown_json': json.dumps([
            {
                'id': course.id,
                'name': course.course_name,
            }
            for course in Course.objects.all()
        ], cls=DjangoJSONEncoder),
    }

    return render(request, 'staffs/dashboard.html', context)

@login_required
@role_required('STAFF')
def register_student(request):
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            username = generate_username(first_name, last_name)

            user = User.objects.create_user(
                username=username,
                first_name=first_name,
                last_name=last_name,
                email=form.cleaned_data['email'],
                phone=form.cleaned_data['phone'],
                password=form.cleaned_data['password'],
                role='STUDENT',
            )

            student = form.save(commit=False)
            student.user = user
            student.save()
            messages.success(request, f"Student registered successfully. Username: {username}")

            return redirect('student_list')
    else:
        form = StudentRegistrationForm()

    return render(request, 'staffs/register_student.html', {
        'form': form,
        'page_title': 'Register Student'
    })

@login_required
@role_required('STAFF')
def student_list(request):
    query = request.GET.get('q', '').strip()
    students = Student.objects.select_related('user')

    if query:
        students = students.filter(
            Q(student_id__icontains=query) |
            Q(student_nic__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__username__icontains=query) |
            Q(user__email__icontains=query)|
            Q(user__phone__icontains=query)
        )

    students = students.order_by('-id')

    return render(request, 'staffs/student_list.html', {
        'students': students,
        'query': query,
        'page_title': 'Students',
    })

@login_required
@role_required('STAFF')
def register_lecturer(request):
    if request.method == 'POST':
        form = LecturerRegistrationForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            username = generate_username(first_name, last_name)

            user = User.objects.create_user(
                username=username,
                first_name=first_name,
                last_name=last_name,
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                role='LECTURER',
            )

            lecturer = form.save(commit=False)
            lecturer.user = user
            lecturer.save()

            messages.success(request, f'Lecturer registered successfully. Username: {username}')
            return redirect('lecturer_list')
    else:
        form = LecturerRegistrationForm()

    return render(request, 'staffs/register_lecturer.html', {
        'form': form,
        'page_title': 'Register Lecturer'
    })

@login_required
@role_required('STAFF')
def lecturer_list(request):
    lecturers = Lecturer.objects.select_related('user').order_by('-id')
    return render(request, 'staffs/lecturer_list.html', {'lecturers': lecturers, 'page_title': 'Lecturers'})


@login_required
@role_required('STAFF')
def register_course(request):
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Course created successfully.')
            return redirect('course_list')
    else:
        form = CourseForm()
    return render(request, 'staffs/register_course.html', {'form': form, 'page_title': 'Register Course'})


@login_required
@role_required('STAFF')
def course_list(request):
    courses = Course.objects.prefetch_related('lecturers__user')
    return render(request, 'staffs/course_list.html', {'courses': courses, 'page_title': 'Courses'})

@login_required
@role_required('STAFF')
def assign_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if request.method == 'POST':
        form = AssignCourseForm(request.POST, course=course)

        if form.is_valid():
            lecturer = form.cleaned_data['lecturer']
            course.lecturers.add(lecturer)

            messages.success(
                request,
                f'{lecturer.user.get_full_name() or lecturer.user.username} assigned successfully to {course.course_name}.'
            )
            return redirect('course_list')
    else:
        form = AssignCourseForm(course=course)

    return render(
        request,
        'staffs/assign_course.html',
        {
            'form': form,
            'course': course,
            'page_title': 'Assign Lecturer',
        }
    )
@login_required
@role_required('STAFF')
def enroll_student(request):

    courses = Course.objects.all()

    course_fees = {
        str(course.id): str(course.course_fee)
        for course in courses
    }
    if request.method == 'POST':
        form = EnrollmentForm(request.POST)
        if form.is_valid():
            enrollment = form.save()

            student_user = enrollment.student
            course = enrollment.course

            subject = "Course Enrollment Confirmation"

            message = f"""
            Dear {student_user.get_full_name() or student_user.username},
            You have been successfully enrolled in the following course:
            Course: {course.course_code} - {course.course_name}
            Mode of Study: {enrollment.mode_of_study}
            Final Course Fee: {enrollment.final_course_fee}
            Installments: {enrollment.number_of_installments}
                Thank you.
                Europe Campus Management
                """

            send_email_notification(
                subject,
                message,
                student_user.email
            )

            sms_message = (
                f"You have been enrolled in {course.course_name}. "
                f"Mode: {enrollment.mode_of_study}. "
                f"Fee: {enrollment.final_course_fee}. "
                f"Installments: {enrollment.number_of_installments}."
            )

            send_sms_notification(student_user.phone, sms_message)

            messages.success(request, 'Student enrolled successfully. Email notification sent.')
            return redirect('enrollment_list')
        else:
            messages.error(request, 'Enrollment failed. Please check the form.')
    else:
        form = EnrollmentForm()
        courses = Course.objects.all()

        course_fees = {
            str(course.id): str(course.course_fee)
            for course in courses
        }

    return render(request, 'staffs/enroll_student.html', {
        'form': form,
        'page_title': 'Enroll Student',
        'course_fees_json': json.dumps(course_fees, cls=DjangoJSONEncoder),

    })
@login_required
@role_required('STAFF')
def enrollment_list(request):
    query = request.GET.get('q', '').strip()

    enrollments = Enrollment.objects.select_related(
        'student',
        'course'
    )

    if query:
        enrollments = enrollments.filter(
            Q(student__student_profile__student_id__icontains=query) |
            Q(student__first_name__icontains=query) |
            Q(student__last_name__icontains=query) |
            Q(student__username__icontains=query) |
            Q(course__course_code__icontains=query) |
            Q(course__course_name__icontains=query)
        )

    enrollments = enrollments.order_by('-id')

    return render(request, 'staffs/enrollment_list.html', {
        'enrollments': enrollments,
        'query': query,
        'page_title': 'Enrollments',
    })

@login_required
@role_required('STAFF')
@login_required
@role_required('STAFF')
def payment_list(request):

    query = request.GET.get('q', '').strip()

    payments = Payment.objects.select_related(
        'student',
        'student__user',
        'course'
    )

    if query:
        payments = payments.filter(
            Q(student__student_id__icontains=query) |
            Q(student__student_nic__icontains=query) |
            Q(student__user__first_name__icontains=query) |
            Q(student__user__last_name__icontains=query) |
            Q(student__user__username__icontains=query) |
            Q(reference_no__icontains=query)
        )

    payments = payments.order_by('-id')

    return render(request, 'staffs/payment_list.html', {
        'payments': payments,
        'query': query,
        'page_title': 'Payments',
    })

@login_required
@role_required('STAFF')
def add_payment(request):
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save()

            student_profile = payment.student
            student_user = student_profile.user
            course = payment.course

            subject = "Payment Confirmation"

            email_message = f"""
            Dear {student_user.get_full_name() or student_user.username},
            
            Your payment has been recorded successfully.
            
            Reference No: {payment.reference_no}
            Course: {course.course_code} - {course.course_name}
            Amount Paid: {payment.amount}
            Payment Method: {payment.payment_method}
            Status: {payment.status}
            Date: {payment.payment_date}
            
            Thank you.
            Europe Campus Management
            """

            sms_message = (
                f"Payment received. Ref: {payment.reference_no}, "
                f"Course: {course.course_name}, Amount: {payment.amount}, "
                f"Status: {payment.status}."
            )

            send_email_notification(
                subject,
                email_message,
                student_user.email
            )

            send_sms_notification(
                student_user.phone,
                sms_message
            )

            messages.success(request, 'Payment added successfully. Email and SMS notifications sent.')
            return redirect('payment_list')
    else:
        form = PaymentForm()

    enrollment_data = {}

    enrollments = Enrollment.objects.select_related(
        'student',
        'student__student_profile',
        'course'
    )

    for enrollment in enrollments:
        try:
            student_profile = enrollment.student.student_profile
        except Student.DoesNotExist:
            continue

        paid_amount = Payment.objects.filter(
            student=student_profile,
            course=enrollment.course,
            status='PAID'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        final_fee = enrollment.final_course_fee or Decimal('0.00')
        remaining_balance = final_fee - paid_amount

        student_id = str(student_profile.id)

        enrollment_data.setdefault(student_id, [])

        enrollment_data[student_id].append({
            'course_id': enrollment.course.id,
            'course_code': enrollment.course.course_code,
            'course_name': enrollment.course.course_name,
            'course_fee': float(final_fee),
            'paid_amount': float(paid_amount),
            'remaining_balance': float(remaining_balance),
        })

    return render(request, 'staffs/payment_form.html', {
        'form': form,
        'page_title': 'Add Payment',
        'title': 'Add Payment',
        'enrollment_data_json': json.dumps(enrollment_data, cls=DjangoJSONEncoder),
    })

@login_required
@role_required('STAFF')
def edit_payment(request, pk):
    payment = get_object_or_404(Payment, pk=pk)

    if request.method == 'POST':
        form = PaymentForm(request.POST, instance=payment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Payment updated successfully.')
            return redirect('payment_list')
    else:
        form = PaymentForm(instance=payment)

    return render(
        request,
        'staffs/payment_form.html',
        {
            'form': form,
            'page_title': 'Edit Payment',
            'title': 'Edit Payment',
        }
    )

@login_required
@role_required('STAFF')
def export_payments_excel(request):
    query = request.GET.get('q', '').strip()

    payments = Payment.objects.select_related(
        'student',
        'student__user',
        'course'
    )

    if query:
        payments = payments.filter(
            Q(student__student_id__icontains=query) |
            Q(student__student_nic__icontains=query) |
            Q(student__user__first_name__icontains=query) |
            Q(student__user__last_name__icontains=query) |
            Q(student__user__username__icontains=query) |
            Q(reference_no__icontains=query)
        )

    payments = payments.order_by('-id')

    wb = Workbook()
    ws = wb.active
    ws.title = "Payment Report"

    headers = [
        "Reference No",
        "Student ID",
        "Student Name",
        "NIC",
        "Course Code",
        "Course Name",
        "Course Fee",
        "Paid Amount",
        "Payment Method",
        "Status",
        "Payment Date",
    ]

    ws.append(headers)

    for payment in payments:
        ws.append([
            payment.reference_no,
            payment.student.student_id,
            payment.student.user.get_full_name(),
            payment.student.student_nic,
            payment.course.course_code,
            payment.course.course_name,
            float(payment.course.course_fee),
            float(payment.amount),
            payment.payment_method,
            payment.status,
            payment.payment_date.strftime("%Y-%m-%d"),
        ])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="payment_report.xlsx"'
    wb.save(response)
    return response

@login_required
@role_required('STAFF')
def staff_class_schedule_list(request):
    course_id = request.GET.get('course')
    lecturer_id = request.GET.get('lecturer')
    query = request.GET.get('q', '').strip()

    schedules = ClassSchedule.objects.select_related(
        'course',
        'lecturer'
    ).order_by('-class_date', 'start_time')

    courses = Course.objects.all().order_by('course_name')
    lecturers = User.objects.filter(role='LECTURER').order_by('first_name', 'username')

    if course_id:
        schedules = schedules.filter(course_id=course_id)

    if lecturer_id:
        schedules = schedules.filter(lecturer_id=lecturer_id)

    if query:
        schedules = schedules.filter(
            Q(course__course_code__icontains=query) |
            Q(course__course_name__icontains=query) |
            Q(lecturer__first_name__icontains=query) |
            Q(lecturer__last_name__icontains=query) |
            Q(lecturer__username__icontains=query) |
            Q(title__icontains=query)
        )

    return render(request, 'staffs/class_schedule_list.html', {
        'schedules': schedules,
        'courses': courses,
        'lecturers': lecturers,
        'selected_course': course_id,
        'selected_lecturer': lecturer_id,
        'query': query,
    })

@login_required
@role_required('STAFF')
def staff_create_class_schedule(request):
    if request.method == 'POST':
        form = StaffClassScheduleForm(request.POST)

        if form.is_valid():
            schedule = form.save(commit=False)

            existing_hours = ClassSchedule.objects.filter(
                course=schedule.course
            ).exclude(
                pk=schedule.pk
            ).aggregate(total=Sum('covered_hours'))['total'] or Decimal('0.00')

            course_total_hours = Decimal(schedule.course.total_hours or 0)

            if existing_hours + schedule.covered_hours > course_total_hours:
                messages.error(
                    request,
                    'Cannot create schedule. Covered hours exceed total course hours.'
                )
            else:
                schedule.save()
                messages.success(request, 'Class schedule created successfully.')
                return redirect('staff_class_schedule_list')
    else:
        form = StaffClassScheduleForm()

    return render(request, 'staffs/class_schedule_form.html', {
        'form': form,
        'page_title': 'Create Class Schedule',
    })

@login_required
@role_required('STAFF')
def staff_create_class_schedule_range(request):
    if request.method == 'POST':
        form = StaffClassScheduleRangeForm(request.POST)

        if form.is_valid():
            course = form.cleaned_data['course']
            lecturer_user = form.cleaned_data['lecturer']
            title = form.cleaned_data['title']
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            weekdays = [int(day) for day in form.cleaned_data['weekdays']]
            start_time = form.cleaned_data['start_time']
            end_time = form.cleaned_data['end_time']
            mode = form.cleaned_data['mode']
            location_or_link = form.cleaned_data['location_or_link']

            if end_date < start_date:
                messages.error(request, 'End date cannot be before start date.')
                return redirect('staff_create_class_schedule_range')

            start_dt = datetime.combine(start_date, start_time)
            end_dt = datetime.combine(start_date, end_time)

            if end_dt <= start_dt:
                messages.error(request, 'End time must be after start time.')
                return redirect('staff_create_class_schedule_range')

            duration_hours = Decimal(
                str((end_dt - start_dt).total_seconds() / 3600)
            )

            schedule_dates = []
            current_date = start_date

            while current_date <= end_date:
                if current_date.weekday() in weekdays:
                    schedule_dates.append(current_date)
                current_date += timedelta(days=1)

            if not schedule_dates:
                messages.error(request, 'No matching class dates found.')
                return redirect('staff_create_class_schedule_range')

            total_new_hours = duration_hours * len(schedule_dates)

            existing_hours = ClassSchedule.objects.filter(
                course=course
            ).aggregate(total=Sum('covered_hours'))['total'] or Decimal('0.00')

            course_total_hours = Decimal(course.total_hours or 0)

            if existing_hours + total_new_hours > course_total_hours:
                messages.error(
                    request,
                    f'Schedule exceeds total course hours. '
                    f'Existing: {existing_hours}, New: {total_new_hours}, '
                    f'Course Total: {course_total_hours}.'
                )
                return redirect('staff_create_class_schedule_range')

            for class_date in schedule_dates:
                ClassSchedule.objects.create(
                    course=course,
                    lecturer=lecturer_user,
                    title=title,
                    class_date=class_date,
                    start_time=start_time,
                    end_time=end_time,
                    mode=mode,
                    location_or_link=location_or_link,
                    covered_hours=duration_hours,
                )

            messages.success(
                request,
                f'{len(schedule_dates)} class schedules created successfully.'
            )
            return redirect('staff_class_schedule_list')
    else:
        form = StaffClassScheduleRangeForm()

    return render(request, 'staffs/class_schedule_range_form.html', {
        'form': form,
        'page_title': 'Create Range Class Schedule',
    })