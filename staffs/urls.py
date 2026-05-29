from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.staff_dashboard, name='staff_dashboard'),

    path('students/register/', views.register_student, name='register_student'),
    path('students/', views.student_list, name='student_list'),

    path('lecturers/register/', views.register_lecturer, name='register_lecturer'),
    path('lecturers/', views.lecturer_list, name='lecturer_list'),

    path('courses/register/', views.register_course, name='register_course'),
    path('courses/', views.course_list, name='course_list'),
    path('courses/<int:course_id>/assign/', views.assign_course, name='assign_course'),

    path('enrollments/register/', views.enroll_student, name='enroll_student'),
    path('enrollments/', views.enrollment_list, name='enrollment_list'),

    path('payments/', views.payment_list, name='payment_list'),
    path('payments/add/', views.add_payment, name='add_payment'),
    path('payments/<int:pk>/edit/', views.edit_payment, name='edit_payment'),

    path('payments/export-excel/', views.export_payments_excel, name='export_payments_excel'),

    path(  'class-schedules/',   views.staff_class_schedule_list,   name='staff_class_schedule_list'),
]