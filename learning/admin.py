from django.contrib import admin
from .models import CourseNote, Assignment, AssignmentSubmission, ClassSchedule


@admin.register(CourseNote)
class CourseNoteAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'semester', 'uploaded_by', 'uploaded_at')
    list_filter = ('course', 'semester', 'uploaded_at')
    search_fields = ('title', 'course__course_name', 'uploaded_by__username')
    readonly_fields = ('uploaded_at',)


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'semester', 'deadline', 'uploaded_by', 'uploaded_at')
    list_filter = ('course', 'semester', 'deadline')
    search_fields = ('title', 'course__course_name', 'uploaded_by__username')
    readonly_fields = ('uploaded_at',)


@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = ('assignment', 'student', 'submitted_at', 'marks')
    list_filter = ('submitted_at', 'assignment__course')
    search_fields = (
        'assignment__title',
        'student__username',
        'student__first_name',
        'student__last_name',
    )
    readonly_fields = ('submitted_at',)


@admin.register(ClassSchedule)
class ClassScheduleAdmin(admin.ModelAdmin):
    list_display = (
        'course',
        'lecturer',
        'title',
        'class_date',
        'start_time',
        'end_time',
        'mode',
        'covered_hours',
    )

    list_filter = (
        'course',
        'lecturer',
        'mode',
        'class_date',
    )

    search_fields = (
        'course__course_code',
        'course__course_name',
        'lecturer__username',
        'title',
    )

    readonly_fields = ('created_at',)

    ordering = ('-class_date', 'start_time')