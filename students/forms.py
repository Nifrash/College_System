from django import forms
from .models import Student
from django import forms


class StudentForm(forms.ModelForm):
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
            'student_nic': forms.TextInput(attrs={'class': 'form-control'}),
            'student_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'nic_copy': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
        }


class StudentImageUpdateForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['student_image']

        widgets = {
            'student_image': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),
        }