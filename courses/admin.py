from django.contrib import admin
from .models import Course, Enrollment


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        'course_code',
        'course_name',
        'credits',
        'course_fee',
        'semester',
        'total_hours',
    )

    search_fields = (
        'course_code',
        'course_name',
    )

    list_filter = (
        'semester',
    )

    filter_horizontal = (
        'lecturers',
    )


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = (
        'student',
        'course',
        'mode_of_study',
        'final_course_fee',
        'preferred_payment_method',
        'number_of_installments',
        'enrolled_date',
    )

    search_fields = (
        'student__username',
        'student__student_profile__student_id',
        'course__course_name',
        'course__course_code',
    )

    list_filter = (
        'mode_of_study',
        'preferred_payment_method',
        'course',
    )