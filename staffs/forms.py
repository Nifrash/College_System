from django import forms
from django.contrib.auth import get_user_model
from students.models import Student
from lecturers.models import Lecturer
from courses.models import Course, Enrollment
from payments.models import Payment
from django.db.models import Sum
from decimal import Decimal
from lecturers.models import Lecturer


User = get_user_model()

class BootstrapFormMixin:
    def apply_bootstrap(self):
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs['class'] = 'form-check-input'
            elif isinstance(widget, forms.Select):
                widget.attrs['class'] = 'form-select'
            elif isinstance(widget, forms.ClearableFileInput):
                widget.attrs['class'] = 'form-control'
            else:
                widget.attrs['class'] = 'form-control'

            widget.attrs.setdefault('placeholder', field.label)


class StudentRegistrationForm(BootstrapFormMixin, forms.ModelForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    phone = forms.CharField(max_length=20, required=False)
    password = forms.CharField(widget=forms.PasswordInput)
    class Meta:
        model = Student
        fields = [
            'student_nic',
            'student_image',
            'nic_copy',
            'date_of_birth',
            'gender',
            'address',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email already exists.")
        return email

    def clean_student_nic(self):
        nic = self.cleaned_data.get('student_nic')
        if nic == '':
            return None
        return nic

class LecturerRegistrationForm(BootstrapFormMixin, forms.ModelForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = Lecturer
        fields = ['department', 'specialization', 'phone']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email already exists.")
        return email

class CourseForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Course
        fields = [
            'course_name',
            'description',
            'credits',
            'course_fee',
            'semester',
            'total_hours',
        ]

        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()

class AssignCourseForm(forms.Form):
    lecturer = forms.ModelChoiceField(
        queryset=Lecturer.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Select Lecturer'
    )

    def __init__(self, *args, **kwargs):
        course = kwargs.pop('course', None)
        super().__init__(*args, **kwargs)

        if course:
            assigned_lecturers = course.lecturers.all()
            self.fields['lecturer'].queryset = Lecturer.objects.exclude(
                id__in=assigned_lecturers.values_list('id', flat=True)
            )
        else:
            self.fields['lecturer'].queryset = Lecturer.objects.all()

class EnrollmentForm(forms.ModelForm):
    class Meta:
        model = Enrollment
        fields = [
            'student',
            'course',
            'mode_of_study',
            'original_course_fee',
            'discount_amount',
            'preferred_payment_method',
            'number_of_installments',
        ]

        widgets = {
            'student': forms.Select(attrs={'class': 'form-select'}),
            'course': forms.Select(attrs={'class': 'form-select'}),
            'mode_of_study': forms.Select(attrs={'class': 'form-select'}),
            'original_course_fee': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'discount_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'preferred_payment_method': forms.Select(attrs={'class': 'form-select'}),
            'number_of_installments': forms.Select(attrs={'class': 'form-select'}),
        }



    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['student'].queryset = User.objects.filter(role='STUDENT')
        self.fields['course'].queryset = Course.objects.all()

        self.fields['original_course_fee'].help_text = "Default course fee. You may adjust it for this student."

    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get('student')
        course = cleaned_data.get('course')

        if student and course:
            if Enrollment.objects.filter(student=student, course=course).exists():
                raise forms.ValidationError(
                    "This student is already enrolled in this course."
                )

        return cleaned_data

class PaymentForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Payment
        fields = [
            'student',
            'course',
            'amount',
            'payment_method',
            'status',
            'reference_no',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        enrolled_user_ids = Enrollment.objects.values_list('student_id', flat=True).distinct()

        self.fields['student'].queryset = Student.objects.filter(
            user_id__in=enrolled_user_ids
        )

        self.fields['course'].queryset = Course.objects.all()

        self.apply_bootstrap()

    def clean(self):
        cleaned_data = super().clean()

        student = cleaned_data.get('student')
        course = cleaned_data.get('course')
        amount = cleaned_data.get('amount')

        if student and course and amount:

            enrollment = Enrollment.objects.filter(
                student=student.user,
                course=course
            ).first()

            if not enrollment:
                raise forms.ValidationError(
                    "This student is not enrolled in the selected course."
                )

            course_fee = enrollment.final_course_fee or Decimal('0.00')

            already_paid = Payment.objects.filter(
                student=student,
                course=course,
                status='PAID'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            new_total = already_paid + amount

            if new_total > course_fee:
                remaining_balance = course_fee - already_paid

                raise forms.ValidationError(
                    f"Payment exceeds course fee. "  f"Remaining balance is {remaining_balance:.2f}." )

        return cleaned_data