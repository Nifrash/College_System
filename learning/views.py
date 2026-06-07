from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from lecturers.models import Lecturer
from courses.models import Course, Enrollment
from .models import CourseNote, Assignment, AssignmentSubmission
from .forms import CourseNoteForm, AssignmentForm, MarkSubmissionForm
from django.utils import timezone
from .forms import AssignmentSubmissionForm
from django.db.models import Q
from .models import ClassSchedule
from .forms import ClassScheduleForm
from django.db.models import Sum
from .forms import ClassScheduleRangeForm
from datetime import datetime, timedelta
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from learning.models import ClassSchedule
from django.utils import timezone

def is_lecturer(user):
    return user.is_authenticated and user.role == 'LECTURER'
@login_required
@user_passes_test(is_lecturer)
def lecturer_dashboard(request):
    lecturer = get_object_or_404(Lecturer, user=request.user)

    courses = Course.objects.filter(lecturers=lecturer).prefetch_related('enrollment_set')

    notes_count = CourseNote.objects.filter(course__in=courses).count()
    assignments_count = Assignment.objects.filter(course__in=courses).count()
    submissions_count = AssignmentSubmission.objects.filter(
        assignment__course__in=courses
    ).count()

    context = {
        'lecturer': lecturer,
        'courses': courses,
        'courses_count': courses.count(),
        'notes_count': notes_count,
        'assignments_count': assignments_count,
        'submissions_count': submissions_count,
    }

    return render(request, 'lecturer/dashboard.html', context)

@login_required
@user_passes_test(is_lecturer)
def lecturer_courses(request):
    lecturer = get_object_or_404(Lecturer, user=request.user)
    Course.objects.filter(lecturers=lecturer)
    return render(request, 'lecturer/courses.html', {'lecturer': lecturer})

@login_required
@user_passes_test(is_lecturer)
def upload_note(request):
    lecturer = get_object_or_404(Lecturer, user=request.user)

    if request.method == 'POST':
        form = CourseNoteForm(request.POST, request.FILES)
        form.fields['course'].queryset = Course.objects.filter(lecturers=lecturer)

        if form.is_valid():
            note = form.save(commit=False)
            note.uploaded_by = request.user
            note.save()
            messages.success(request, 'Course note uploaded successfully.')
            return redirect('lecturer_dashboard')
    else:
        form = CourseNoteForm()
        form.fields['course'].queryset = Course.objects.filter(lecturers=lecturer)

    return render(request, 'lecturer/note_form.html', {'form': form})

@login_required
@user_passes_test(is_lecturer)
def create_assignment(request):
    lecturer = get_object_or_404(Lecturer, user=request.user)

    if request.method == 'POST':
        form = AssignmentForm(request.POST, request.FILES)
        form.fields['course'].queryset = Course.objects.filter(lecturers=lecturer)

        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.uploaded_by = request.user
            assignment.save()
            messages.success(request, 'Assignment uploaded successfully.')
            return redirect('lecturer_dashboard')
    else:
        form = AssignmentForm()
        form.fields['course'].queryset = Course.objects.filter(lecturers=lecturer)

    return render(request, 'lecturer/assignment_form.html', {'form': form})

@login_required
@user_passes_test(is_lecturer)
def edit_assignment(request, pk):
    lecturer = get_object_or_404(Lecturer, user=request.user)
    assignment = get_object_or_404(Assignment, pk=pk, course__lecturers=lecturer)

    if request.method == 'POST':
        form = AssignmentForm(request.POST, request.FILES, instance=assignment)
        form.fields['course'].queryset = Course.objects.filter(lecturers=lecturer)

        if form.is_valid():
            form.save()
            messages.success(request, 'Assignment updated successfully.')
            return redirect('assignment_submissions', pk=assignment.pk)
    else:
        form = AssignmentForm(instance=assignment)
        form.fields['course'].queryset = Course.objects.filter(lecturers=lecturer)

    return render(request, 'lecturer/assignment_form.html', {'form': form})

@login_required
@user_passes_test(is_lecturer)
def assignment_list(request):
    lecturer = get_object_or_404(Lecturer, user=request.user)
    assignments = Assignment.objects.filter(course__lecturers=lecturer).order_by('-uploaded_at')
    return render(request, 'lecturer/assignment_list.html', {'assignments': assignments})

@login_required
@user_passes_test(is_lecturer)
def assignment_submissions(request, pk):
    lecturer = get_object_or_404(Lecturer, user=request.user)
    assignment = get_object_or_404(Assignment, pk=pk, course__lecturers=lecturer)

    submissions = AssignmentSubmission.objects.filter(
        assignment=assignment
    ).select_related('student', 'student__student_profile')

    return render(request, 'lecturer/submissions.html', {
        'assignment': assignment,
        'submissions': submissions,
    })

@login_required
@user_passes_test(is_lecturer)
def mark_submission(request, pk):
    submission = get_object_or_404(
        AssignmentSubmission,
        pk=pk,
        assignment__course__lecturers__user=request.user
    )

    if request.method == 'POST':
        form = MarkSubmissionForm(request.POST, instance=submission)
        if form.is_valid():
            form.save()
            messages.success(request, 'Submission marked successfully.')
            return redirect('assignment_submissions', pk=submission.assignment.pk)
    else:
        form = MarkSubmissionForm(instance=submission)

    return render(request, 'lecturer/mark_submission.html', {
        'form': form,
        'submission': submission,
    })

@login_required
@user_passes_test(lambda u: u.role == 'STUDENT')
def submit_assignment(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk)

    # Check student is enrolled in this course
    enrolled = Enrollment.objects.filter(
        student=request.user,
        course=assignment.course
    ).exists()

    if not enrolled:
        messages.error(request, "You are not enrolled in this course.")
        return redirect('student_dashboard')

    # Deadline check
    if timezone.now() > assignment.deadline:
        messages.error(request, "Assignment deadline has passed.")
        return redirect('student_dashboard')

    existing_submission = AssignmentSubmission.objects.filter(
        assignment=assignment,
        student=request.user
    ).first()

    if request.method == 'POST':
        form = AssignmentSubmissionForm(
            request.POST,
            request.FILES,
            instance=existing_submission
        )

        if form.is_valid():
            submission = form.save(commit=False)
            submission.assignment = assignment
            submission.student = request.user
            submission.save()

            messages.success(request, "Assignment submitted successfully.")
            return redirect('student_dashboard')
    else:
        form = AssignmentSubmissionForm(instance=existing_submission)

    return render(request, 'students/submit_assignment.html', {
        'form': form,
        'assignment': assignment,
        'existing_submission': existing_submission,
    })

@login_required
@user_passes_test(is_lecturer)
def all_submissions(request):
    lecturer = get_object_or_404(Lecturer, user=request.user)

    course_id = request.GET.get('course')
    assignment_id = request.GET.get('assignment')
    status = request.GET.get('status')
    query = request.GET.get('q', '').strip()

    # Only this lecturer's assigned courses
    courses = Course.objects.filter(lecturers=lecturer)

    assignments = Assignment.objects.filter(
        course__in=courses
    ).order_by('-uploaded_at')

    submissions = AssignmentSubmission.objects.filter(
        assignment__course__in=courses
    ).select_related(
        'assignment',
        'assignment__course',
        'student',
        'student__student_profile'
    ).order_by('-submitted_at')

    if course_id:
        # Protect against manually changing URL course ID
        submissions = submissions.filter(
            assignment__course_id=course_id,
            assignment__course__in=courses
        )
        assignments = assignments.filter(course_id=course_id)

    if assignment_id:
        submissions = submissions.filter(
            assignment_id=assignment_id,
            assignment__course__in=courses
        )

    if status == 'marked':
        submissions = submissions.filter(marks__isnull=False)

    elif status == 'unmarked':
        submissions = submissions.filter(marks__isnull=True)

    if query:
        submissions = submissions.filter(
            Q(student__first_name__icontains=query) |
            Q(student__last_name__icontains=query) |
            Q(student__username__icontains=query) |
            Q(student__student_profile__student_id__icontains=query) |
            Q(assignment__title__icontains=query)
        )

    return render(request, 'lecturer/all_submissions.html', {
        'courses': courses,
        'assignments': assignments,
        'submissions': submissions,
        'selected_course': course_id,
        'selected_assignment': assignment_id,
        'selected_status': status,
        'query': query,
    })

@login_required
@user_passes_test(is_lecturer)
def schedule_list(request):
    lecturer = get_object_or_404(Lecturer, user=request.user)

    schedules = ClassSchedule.objects.filter(
        course__lecturers=lecturer
    ).select_related('course').order_by('-class_date')

    return render(request, 'lecturer/schedule_list.html', {'schedules': schedules, 'today': timezone.now().date(), })


@login_required
@user_passes_test(is_lecturer)
def create_schedule(request):
    lecturer = get_object_or_404(Lecturer, user=request.user)

    if request.method == 'POST':
        form = ClassScheduleForm(request.POST)
        form.fields['course'].queryset = Course.objects.filter(lecturers=lecturer)

        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.lecturer = request.user

            total_scheduled = ClassSchedule.objects.filter(
                course=schedule.course
            ).aggregate(total=Sum('covered_hours'))['total'] or 0

            if total_scheduled + schedule.covered_hours > schedule.course.total_hours:
                messages.error(
                    request,
                    'Scheduled hours exceed the course total hours.'
                )
            else:
                schedule.save()
                messages.success(request, 'Class schedule created successfully.')
                return redirect('schedule_list')
    else:
        form = ClassScheduleForm()
        form.fields['course'].queryset = Course.objects.filter(lecturers=lecturer)

    return render(request, 'lecturer/schedule_form.html', {
        'form': form,
        'page_title': 'Create Class Schedule',
    })

@login_required
@user_passes_test(is_lecturer)
def create_schedule_range(request):
    lecturer = get_object_or_404(Lecturer, user=request.user)

    if request.method == 'POST':
        form = ClassScheduleRangeForm(request.POST)
        form.fields['course'].queryset = Course.objects.filter(lecturers=lecturer)

        if form.is_valid():
            course = form.cleaned_data['course']
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
                return redirect('create_schedule_range')

            start_dt = datetime.combine(start_date, start_time)
            end_dt = datetime.combine(start_date, end_time)

            if end_dt <= start_dt:
                messages.error(request, 'End time must be after start time.')
                return redirect('create_schedule_range')

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
                messages.error(request, 'No matching class dates found for selected days.')
                return redirect('create_schedule_range')

            total_new_hours = duration_hours * len(schedule_dates)

            existing_hours = ClassSchedule.objects.filter(
                course=course
            ).aggregate(total=Sum('covered_hours'))['total'] or Decimal('0.00')

            course_total_hours = Decimal(course.total_hours or 0)

            if existing_hours + total_new_hours > course_total_hours:
                messages.error(
                    request,
                    f'Schedule exceeds course total hours. '
                    f'Existing: {existing_hours}, New: {total_new_hours}, '
                    f'Course Total: {course_total_hours}.'
                )
                return redirect('create_schedule_range')

            created_count = 0

            for class_date in schedule_dates:
                ClassSchedule.objects.create(
                    course=course,
                    lecturer=request.user,
                    title=title,
                    class_date=class_date,
                    start_time=start_time,
                    end_time=end_time,
                    mode=mode,
                    location_or_link=location_or_link,
                    covered_hours=duration_hours,
                )
                created_count += 1

            messages.success(
                request,
                f'{created_count} schedules created successfully. '
                f'Each class: {duration_hours} hours. '
                f'Total covered: {total_new_hours} hours.'
            )
            return redirect('schedule_list')

    else:
        form = ClassScheduleRangeForm()
        form.fields['course'].queryset = Course.objects.filter(lecturers=lecturer)

    return render(request, 'lecturer/schedule_range_form.html', {
        'form': form,
        'page_title': 'Create Schedule for Date Range',
    })

@login_required
@user_passes_test(is_lecturer)
def edit_schedule(request, pk):
    lecturer = get_object_or_404(Lecturer, user=request.user)

    schedule = get_object_or_404(
        ClassSchedule,
        pk=pk,
        lecturer=request.user,
        course__lecturers=lecturer
    )

    if schedule.class_date < timezone.now().date():
        messages.error(request, "You cannot edit past class schedules.")
        return redirect('schedule_list')

    if request.method == 'POST':
        form = ClassScheduleForm(request.POST, instance=schedule)
        form.fields['course'].queryset = Course.objects.filter(lecturers=lecturer)

        if form.is_valid():
            updated_schedule = form.save(commit=False)

            existing_hours = ClassSchedule.objects.filter(
                course=updated_schedule.course
            ).exclude(
                pk=schedule.pk
            ).aggregate(total=Sum('covered_hours'))['total'] or 0

            if existing_hours + updated_schedule.covered_hours > updated_schedule.course.total_hours:
                messages.error(request, "Updated schedule exceeds course total hours.")
            else:
                updated_schedule.lecturer = request.user
                updated_schedule.save()
                messages.success(request, "Class schedule updated successfully.")
                return redirect('schedule_list')
    else:
        form = ClassScheduleForm(instance=schedule)
        form.fields['course'].queryset = Course.objects.filter(lecturers=lecturer)

    return render(request, 'lecturer/schedule_form.html', {
        'form': form,
        'page_title': 'Edit Class Schedule',
    })