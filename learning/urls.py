from django.urls import path
from . import views

urlpatterns = [
    path('lecturer/', views.lecturer_dashboard, name='lecturer_dashboard'),
    path('lecturer/courses/', views.lecturer_courses, name='lecturer_courses'),

    path('lecturer/notes/upload/', views.upload_note, name='upload_note'),

    path('lecturer/assignments/', views.assignment_list, name='assignment_list'),
    path('lecturer/assignments/create/', views.create_assignment, name='create_assignment'),
    path('lecturer/assignments/<int:pk>/edit/', views.edit_assignment, name='edit_assignment'),
    path('lecturer/assignments/<int:pk>/submissions/', views.assignment_submissions, name='assignment_submissions'),

    path('lecturer/submissions/<int:pk>/mark/', views.mark_submission, name='mark_submission'),

    path('student/assignments/<int:pk>/submit/',  views.submit_assignment,  name='submit_assignment'),

    path('lecturer/submissions/',  views.all_submissions,  name='all_submissions'),

    path('lecturer/schedules/', views.schedule_list, name='schedule_list'),
    path('lecturer/schedules/create/', views.create_schedule, name='create_schedule'),

    path('lecturer/schedules/create-range/',  views.create_schedule_range,  name='create_schedule_range'),
    path('lecturer/schedules/<int:pk>/edit/',  views.edit_schedule, name='edit_schedule'),
    path('lecturer/schedules/<int:schedule_id>/attendance/', views.mark_attendance,  name='mark_attendance'),

    path(   'assignment-submissions/',  views.lecturer_assignment_submissions,  name='lecturer_assignment_submissions') ,

    path('assignment-submissions/<int:submission_id>/mark/',views.mark_assignment_exam, name='mark_assignment_exam'),

]