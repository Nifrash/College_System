from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from .models import Student
from .forms import StudentForm, StudentImageUpdateForm


def is_student(user):
    return user.is_authenticated and user.role == 'STUDENT'

@login_required
@user_passes_test(is_student)
def student_create(request):
    if Student.objects.filter(user=request.user).exists():
        return redirect('student_dashboard')

    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES)
        if form.is_valid():
            student = form.save(commit=False)
            student.user = request.user
            student.save()
            return redirect('student_dashboard')
    else:
        form = StudentForm()

    return render(request, 'students/student_form.html', {
        'form': form,
        'title': 'Create Student Profile'
    })


@login_required
@user_passes_test(is_student)
def student_detail(request):
    student = get_object_or_404(Student, user=request.user)

    return render(request, 'students/student_detail.html', {
        'students': student
    })

@login_required
@user_passes_test(is_student)
def student_update(request):
    student = get_object_or_404(Student, user=request.user)

    if request.method == 'POST':
        form = StudentImageUpdateForm(
            request.POST,
            request.FILES,
            instance=student
        )

        if form.is_valid():
            form.save()
            return redirect('student_dashboard')
    else:
        form = StudentImageUpdateForm(instance=student)

    return render(request, 'students/student_image_form.html', {
        'form': form,
        'student': student,
        'title': 'Update Profile Picture'
    })

@login_required
@user_passes_test(is_student)
def student_delete(request):
    student = get_object_or_404(Student, user=request.user)

    if request.method == 'POST':
        student.delete()
        return redirect('student_create')

    return render(request, 'students/student_confirm_delete.html', {
        'students': student
    })