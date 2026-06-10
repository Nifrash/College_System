from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from accounts.decorators import role_required
from courses.models import Enrollment, Course
from students.models import Student
from .forms import ExamForm
from .models import Exam, ExamResult
from django.db.models import Q, Avg, Count
from django.http import HttpResponse
import openpyxl
from lecturers.models import Lecturer
from .forms import ExamForm, QuizQuestionForm
from .models import Exam, ExamResult, QuizQuestion
from django.utils import timezone
from students.models import Student
from courses.models import Enrollment
from .models import Exam, QuizQuestion, QuizSubmission, QuizAnswer, ExamResult
from .forms import ExamAssignmentForm
from .models import ExamAssignment
from .forms import ExamAssignmentSubmissionForm
from .models import ExamAssignment, ExamAssignmentSubmission
from django.utils import timezone

@login_required
@role_required('STAFF')
def exam_list(request):
    exams = Exam.objects.select_related('course').order_by('-exam_date', '-id')

    return render(request, 'results/exam_list.html', {
        'exams': exams,
    })

@login_required
@role_required('STAFF')
def create_exam(request):
    if request.method == 'POST':
        form = ExamForm(request.POST)

        if form.is_valid():
            exam = form.save()

            messages.success(request, 'Exam created successfully.')

            if exam.exam_type == 'QUIZ':
                return redirect('add_quiz_questions', exam_id=exam.id)

            if exam.exam_type == 'ASSIGNMENT':
                return redirect('add_exam_assignment', exam_id=exam.id)

            return redirect('exam_list')
    else:
        form = ExamForm()

    return render(request, 'results/exam_form.html', {
        'form': form,
        'page_title': 'Create Exam',
    })

@login_required
@role_required('STAFF')
def enter_exam_marks(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)

    enrollments = Enrollment.objects.filter(
        course=exam.course
    ).select_related('student', 'student__student_profile')

    existing_results = {
        result.student_id: result
        for result in ExamResult.objects.filter(exam=exam)
    }

    if request.method == 'POST':
        for enrollment in enrollments:
            student_user = enrollment.student

            try:
                student_profile = student_user.student_profile
            except Student.DoesNotExist:
                continue

            marks_value = request.POST.get(f'marks_{student_profile.id}', '').strip()
            remarks = request.POST.get(f'remarks_{student_profile.id}', '').strip()

            if marks_value == '':
                continue

            try:
                obtained_marks = Decimal(marks_value)
            except Exception:
                messages.error(request, f'Invalid marks for {student_user.username}.')
                return redirect('enter_exam_marks', exam_id=exam.id)

            if obtained_marks < 0:
                messages.error(request, 'Marks cannot be negative.')
                return redirect('enter_exam_marks', exam_id=exam.id)

            if obtained_marks > exam.total_marks:
                messages.error(
                    request,
                    f'Marks for {student_user.username} cannot exceed total marks.'
                )
                return redirect('enter_exam_marks', exam_id=exam.id)

            ExamResult.objects.update_or_create(
                exam=exam,
                student=student_profile,
                defaults={
                    'obtained_marks': obtained_marks,
                    'remarks': remarks,
                }
            )

        messages.success(request, 'Exam marks saved successfully.')
        return redirect('exam_list')

    return render(request, 'results/enter_marks.html', {
        'exam': exam,
        'enrollments': enrollments,
        'existing_results': existing_results,
    })

@login_required
@role_required('STAFF')
def result_list(request):
    course_id = request.GET.get('course')
    exam_type = request.GET.get('exam_type')
    query = request.GET.get('q', '').strip()

    results = ExamResult.objects.select_related(
        'exam',
        'exam__course',
        'student',
        'student__user'
    ).order_by('-created_at')

    courses = Course.objects.all().order_by('course_name')

    if course_id:
        results = results.filter(exam__course_id=course_id)

    if exam_type:
        results = results.filter(exam__exam_type=exam_type)

    if query:
        results = results.filter(
            Q(student__student_id__icontains=query) |
            Q(student__user__username__icontains=query) |
            Q(student__user__first_name__icontains=query) |
            Q(student__user__last_name__icontains=query) |
            Q(exam__title__icontains=query)
        )

    return render(request, 'results/result_list.html', {
        'results': results,
        'courses': courses,
        'exam_types': Exam.EXAM_TYPES,
        'selected_course': course_id,
        'selected_exam_type': exam_type,
        'query': query,
    })


@login_required
@role_required('STAFF')
def edit_result(request, result_id):
    result = get_object_or_404(ExamResult, id=result_id)

    if request.method == 'POST':
        obtained_marks = request.POST.get('obtained_marks')
        remarks = request.POST.get('remarks', '')

        try:
            obtained_marks = Decimal(obtained_marks)
        except Exception:
            messages.error(request, 'Invalid marks.')
            return redirect('edit_result', result_id=result.id)

        if obtained_marks < 0:
            messages.error(request, 'Marks cannot be negative.')
            return redirect('edit_result', result_id=result.id)

        if obtained_marks > result.exam.total_marks:
            messages.error(request, 'Marks cannot exceed total marks.')
            return redirect('edit_result', result_id=result.id)

        result.obtained_marks = obtained_marks
        result.remarks = remarks
        result.save()

        messages.success(request, 'Result updated successfully.')
        return redirect('result_list')

    return render(request, 'results/edit_result.html', {
        'result': result,
    })


@login_required
@role_required('STAFF')
def delete_result(request, result_id):
    result = get_object_or_404(ExamResult, id=result_id)

    if request.method == 'POST':
        result.delete()
        messages.success(request, 'Result deleted successfully.')
        return redirect('result_list')

    return render(request, 'results/delete_result.html', {
        'result': result,
    })


@login_required
@role_required('STAFF')
def result_summary(request):
    courses = Course.objects.all().order_by('course_name')

    course_summary = []

    for course in courses:
        results = ExamResult.objects.filter(exam__course=course)

        total_results = results.count()
        pass_count = 0
        fail_count = 0
        total_percentage = 0

        for result in results:
            total_percentage += result.percentage

            if result.status == 'PASS':
                pass_count += 1
            else:
                fail_count += 1

        average_percentage = 0

        if total_results > 0:
            average_percentage = round(total_percentage / total_results, 2)

        course_summary.append({
            'course': course,
            'total_results': total_results,
            'pass_count': pass_count,
            'fail_count': fail_count,
            'average_percentage': average_percentage,
        })

    return render(request, 'results/result_summary.html', {
        'course_summary': course_summary,
    })


@login_required
@role_required('STAFF')
def export_results_excel(request):
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Exam Results"

    headers = [
        'Student ID',
        'Student Name',
        'Username',
        'Course Code',
        'Course Name',
        'Exam Title',
        'Exam Type',
        'Total Marks',
        'Obtained Marks',
        'Percentage',
        'Grade',
        'Status',
        'Remarks',
    ]

    sheet.append(headers)

    results = ExamResult.objects.select_related(
        'exam',
        'exam__course',
        'student',
        'student__user'
    ).order_by('exam__course__course_name', 'student__student_id')

    for result in results:
        sheet.append([
            result.student.student_id,
            result.student.user.get_full_name() or result.student.user.username,
            result.student.user.username,
            result.exam.course.course_code,
            result.exam.course.course_name,
            result.exam.title,
            result.exam.get_exam_type_display(),
            float(result.exam.total_marks),
            float(result.obtained_marks),
            result.percentage,
            result.grade,
            result.status,
            result.remarks,
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

    response['Content-Disposition'] = 'attachment; filename=exam_results.xlsx'

    workbook.save(response)

    return response

@login_required
def lecturer_exam_list(request):
    if request.user.role != 'LECTURER':
        messages.error(request, 'Access denied.')
        return redirect('login')

    lecturer = get_object_or_404(Lecturer, user=request.user)

    exams = Exam.objects.filter(
        course__lecturers=lecturer
    ).select_related('course').order_by('-exam_date', '-id')

    return render(request, 'results/lecturer_exam_list.html', {
        'exams': exams,
    })


@login_required
def lecturer_enter_exam_marks(request, exam_id):
    if request.user.role != 'LECTURER':
        messages.error(request, 'Access denied.')
        return redirect('login')

    lecturer = get_object_or_404(Lecturer, user=request.user)

    exam = get_object_or_404(
        Exam,
        id=exam_id,
        course__lecturers=lecturer
    )

    enrollments = Enrollment.objects.filter(
        course=exam.course
    ).select_related('student', 'student__student_profile')

    existing_results = {
        result.student_id: result
        for result in ExamResult.objects.filter(exam=exam)
    }

    if request.method == 'POST':
        for enrollment in enrollments:
            student_user = enrollment.student

            try:
                student_profile = student_user.student_profile
            except Student.DoesNotExist:
                continue

            marks_value = request.POST.get(
                f'marks_{student_profile.id}',
                ''
            ).strip()

            remarks = request.POST.get(
                f'remarks_{student_profile.id}',
                ''
            ).strip()

            if marks_value == '':
                continue

            try:
                obtained_marks = Decimal(marks_value)
            except Exception:
                messages.error(request, f'Invalid marks for {student_user.username}.')
                return redirect('lecturer_enter_exam_marks', exam_id=exam.id)

            if obtained_marks < 0:
                messages.error(request, 'Marks cannot be negative.')
                return redirect('lecturer_enter_exam_marks', exam_id=exam.id)

            if obtained_marks > exam.total_marks:
                messages.error(
                    request,
                    f'Marks for {student_user.username} cannot exceed total marks.'
                )
                return redirect('lecturer_enter_exam_marks', exam_id=exam.id)

            ExamResult.objects.update_or_create(
                exam=exam,
                student=student_profile,
                defaults={
                    'obtained_marks': obtained_marks,
                    'remarks': remarks,
                }
            )

        messages.success(request, 'Exam marks saved successfully.')
        return redirect('lecturer_exam_list')

    return render(request, 'results/lecturer_enter_marks.html', {
        'exam': exam,
        'enrollments': enrollments,
        'existing_results': existing_results,
    })

@login_required
@role_required('STAFF')
def add_quiz_questions(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, exam_type='QUIZ')

    questions = QuizQuestion.objects.filter(exam=exam).order_by('id')

    if request.method == 'POST':
        form = QuizQuestionForm(request.POST)

        if form.is_valid():
            question = form.save(commit=False)
            question.exam = exam
            question.save()

            messages.success(request, 'Quiz question added successfully.')
            return redirect('add_quiz_questions', exam_id=exam.id)
    else:
        form = QuizQuestionForm()

    total_question_marks = sum(q.marks for q in questions)

    return render(request, 'results/add_quiz_questions.html', {
        'exam': exam,
        'form': form,
        'questions': questions,
        'total_question_marks': total_question_marks,
    })

@login_required
def student_quiz_list(request):
    if request.user.role != 'STUDENT':
        messages.error(request, 'Access denied.')
        return redirect('login')

    try:
        student_profile = request.user.student_profile
    except Student.DoesNotExist:
        messages.error(request, 'Student profile not found.')
        return redirect('student_dashboard')

    enrolled_courses = Enrollment.objects.filter(
        student=request.user
    ).values_list('course_id', flat=True)

    quizzes = Exam.objects.filter(
        course_id__in=enrolled_courses,
        exam_type='QUIZ'
    ).select_related('course').order_by('-exam_date')

    submissions = QuizSubmission.objects.filter(
        student=student_profile
    )

    submitted_exam_ids = submissions.filter(
        is_submitted=True
    ).values_list('exam_id', flat=True)

    return render(request, 'results/student_quiz_list.html', {
        'quizzes': quizzes,
        'submitted_exam_ids': submitted_exam_ids,
    })


@login_required
def start_quiz(request, exam_id):
    if request.user.role != 'STUDENT':
        messages.error(request, 'Access denied.')
        return redirect('login')

    student_profile = get_object_or_404(Student, user=request.user)

    exam = get_object_or_404(
        Exam,
        id=exam_id,
        exam_type='QUIZ'
    )

    enrolled = Enrollment.objects.filter(
        student=request.user,
        course=exam.course
    ).exists()

    if not enrolled:
        messages.error(request, 'You are not enrolled in this course.')
        return redirect('student_quiz_list')

    if exam.deadline and timezone.now() > exam.deadline:
        messages.error(request, 'Quiz deadline has passed.')
        return redirect('student_quiz_list')

    questions = QuizQuestion.objects.filter(exam=exam)

    if not questions.exists():
        messages.error(request, 'No questions available for this quiz.')
        return redirect('student_quiz_list')

    submission, created = QuizSubmission.objects.get_or_create(
        exam=exam,
        student=student_profile
    )

    if submission.is_submitted:
        messages.info(request, 'You have already submitted this quiz.')
        return redirect('student_quiz_list')

    return render(request, 'results/start_quiz.html', {
        'exam': exam,
        'questions': questions,
        'submission': submission,
    })


@login_required
def submit_quiz(request, exam_id):
    if request.user.role != 'STUDENT':
        messages.error(request, 'Access denied.')
        return redirect('login')

    student_profile = get_object_or_404(Student, user=request.user)

    exam = get_object_or_404(
        Exam,
        id=exam_id,
        exam_type='QUIZ'
    )

    submission = get_object_or_404(
        QuizSubmission,
        exam=exam,
        student=student_profile
    )

    if submission.is_submitted:
        messages.info(request, 'Quiz already submitted.')
        return redirect('student_quiz_list')

    if exam.deadline and timezone.now() > exam.deadline:
        messages.error(request, 'Quiz deadline has passed.')
        return redirect('student_quiz_list')

    if request.method == 'POST':
        questions = QuizQuestion.objects.filter(exam=exam)

        score = 0

        for question in questions:
            selected_answer = request.POST.get(f'question_{question.id}')

            if not selected_answer:
                continue

            is_correct = selected_answer == question.correct_answer

            if is_correct:
                score += question.marks

            QuizAnswer.objects.create(
                submission=submission,
                question=question,
                selected_answer=selected_answer,
                is_correct=is_correct
            )

        submission.score = score
        submission.is_submitted = True
        submission.submitted_at = timezone.now()
        submission.save()

        ExamResult.objects.update_or_create(
            exam=exam,
            student=student_profile,
            defaults={
                'obtained_marks': score,
                'remarks': 'Auto-generated from online quiz',
            }
        )

        messages.success(
            request,
            f'Quiz submitted successfully. Your score is {score}/{exam.total_marks}.'
        )

        return redirect('student_quiz_list')

    return redirect('start_quiz', exam_id=exam.id)

@login_required
@role_required('STAFF')
def add_exam_assignment(request, exam_id):
    exam = get_object_or_404(
        Exam,
        id=exam_id,
        exam_type='ASSIGNMENT'
    )

    assignment, created = ExamAssignment.objects.get_or_create(
        exam=exam,
        defaults={
            'deadline': exam.deadline,
        }
    )

    if request.method == 'POST':
        form = ExamAssignmentForm(
            request.POST,
            request.FILES,
            instance=assignment
        )

        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.exam = exam
            assignment.save()

            # Keep exam deadline same as assignment deadline
            exam.deadline = assignment.deadline
            exam.save(update_fields=['deadline'])

            messages.success(request, 'Assignment exam uploaded successfully.')
            return redirect('exam_list')
    else:
        form = ExamAssignmentForm(instance=assignment)

    return render(request, 'results/add_exam_assignment.html', {
        'exam': exam,
        'form': form,
        'assignment': assignment,
    })

@login_required
def submit_exam_assignment(request, assignment_id):
    if request.user.role != 'STUDENT':
        messages.error(request, 'Access denied.')
        return redirect('login')

    student_profile = get_object_or_404(Student, user=request.user)

    assignment = get_object_or_404(
        ExamAssignment,
        id=assignment_id
    )

    enrolled = Enrollment.objects.filter(
        student=request.user,
        course=assignment.exam.course
    ).exists()

    if not enrolled:
        messages.error(request, 'You are not enrolled in this course.')
        return redirect('student_dashboard')

    existing_submission = ExamAssignmentSubmission.objects.filter(
        assignment=assignment,
        student=student_profile
    ).first()

    if existing_submission and existing_submission.marks is not None:
        messages.error(
            request,
            'Marks have already been published. Re-submission is not allowed.'
        )
        return redirect('student_dashboard')

    if request.method == 'POST':
        form = ExamAssignmentSubmissionForm(
            request.POST,
            request.FILES,
            instance=existing_submission
        )

        if form.is_valid():
            submission = form.save(commit=False)
            submission.assignment = assignment
            submission.student = student_profile

            if timezone.now() > assignment.deadline:
                submission.is_late = True
            else:
                submission.is_late = False

            submission.save()

            if submission.is_late:
                messages.warning(
                    request,
                    'Assignment submitted successfully, but it is marked as late.'
                )
            else:
                messages.success(
                    request,
                    'Assignment submitted successfully.'
                )

            return redirect('student_dashboard')
    else:
        form = ExamAssignmentSubmissionForm(instance=existing_submission)

    return render(request, 'results/submit_exam_assignment.html', {
        'form': form,
        'assignment': assignment,
        'existing_submission': existing_submission,
    })