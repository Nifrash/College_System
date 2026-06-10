from django.urls import path
from . import views

urlpatterns = [
    path('exams/', views.exam_list, name='exam_list'),
    path('exams/create/', views.create_exam, name='create_exam'),
    path('exams/<int:exam_id>/marks/', views.enter_exam_marks, name='enter_exam_marks'),

    path('results/', views.result_list, name='result_list'),
    path('results/<int:result_id>/edit/', views.edit_result, name='edit_result'),
    path('results/<int:result_id>/delete/', views.delete_result, name='delete_result'),
    path('summary/', views.result_summary, name='result_summary'),
    path('export/', views.export_results_excel, name='export_results_excel'),
    path( 'lecturer/exams/',  views.lecturer_exam_list, name='lecturer_exam_list'),
    path('lecturer/exams/<int:exam_id>/marks/',views.lecturer_enter_exam_marks, name='lecturer_enter_exam_marks'),
    path(   'exams/<int:exam_id>/quiz-questions/',  views.add_quiz_questions,   name='add_quiz_questions'),

    path( 'student/quizzes/', views.student_quiz_list,  name='student_quiz_list' ),
    path('student/quizzes/<int:exam_id>/start/',  views.start_quiz,  name='start_quiz' ),
    path('student/quizzes/<int:exam_id>/submit/',  views.submit_quiz,   name='submit_quiz'  ),
    path('exams/<int:exam_id>/assignment/',  views.add_exam_assignment, name='add_exam_assignment'),

    path(
        'student/assignment-exams/<int:assignment_id>/submit/',
        views.submit_exam_assignment,
        name='submit_exam_assignment'
    ),

]