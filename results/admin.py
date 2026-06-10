from django.contrib import admin

from .models import (
    Exam,
    ExamResult,
    QuizQuestion,
    QuizSubmission,
    QuizAnswer,
    ExamAssignment,
    ExamAssignmentSubmission
)


class QuizQuestionInline(admin.TabularInline):
    model = QuizQuestion
    extra = 1


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'exam_type', 'total_marks', 'exam_date', 'deadline')
    list_filter = ('exam_type', 'course', 'exam_date')
    search_fields = ('title', 'course__course_name', 'course__course_code')
    inlines = [QuizQuestionInline]


@admin.register(ExamAssignment)
class ExamAssignmentAdmin(admin.ModelAdmin):
    list_display = ('exam', 'deadline')


@admin.register(ExamAssignmentSubmission)
class ExamAssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = ('assignment', 'student', 'submitted_at', 'marks')


admin.site.register(QuizSubmission)
admin.site.register(QuizAnswer)