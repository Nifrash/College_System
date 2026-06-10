from django import forms
from .models import Exam, QuizQuestion
from .models import ExamAssignment
from .models import ExamAssignmentSubmission


class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = [
            'course',
            'title',
            'exam_type',
            'total_marks',
            'exam_date',
            'deadline',
            'duration_minutes',
        ]

        widgets = {
            'course': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'exam_type': forms.Select(attrs={'class': 'form-select'}),
            'total_marks': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'exam_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'deadline': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        }


class QuizQuestionForm(forms.ModelForm):
    class Meta:
        model = QuizQuestion
        fields = [
            'question_text',
            'option_a',
            'option_b',
            'option_c',
            'option_d',
            'correct_answer',
            'marks',
        ]

        widgets = {
            'question_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'option_a': forms.TextInput(attrs={'class': 'form-control'}),
            'option_b': forms.TextInput(attrs={'class': 'form-control'}),
            'option_c': forms.TextInput(attrs={'class': 'form-control'}),
            'option_d': forms.TextInput(attrs={'class': 'form-control'}),
            'correct_answer': forms.Select(attrs={'class': 'form-select'}),
            'marks': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


class ExamAssignmentForm(forms.ModelForm):
    class Meta:
        model = ExamAssignment
        fields = [
            'instructions',
            'attachment',
            'deadline',
        ]

        widgets = {
            'instructions': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
            }),
            'attachment': forms.ClearableFileInput(attrs={
                'class': 'form-control',
            }),
            'deadline': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
            }),
        }

class ExamAssignmentSubmissionForm(forms.ModelForm):
    class Meta:
        model = ExamAssignmentSubmission
        fields = ['submitted_file']

        widgets = {
            'submitted_file': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),
        }