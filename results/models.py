from django.db import models
from courses.models import Course
from students.models import Student


class Exam(models.Model):
    EXAM_TYPES = (
        ('QUIZ', 'Quiz'),
        ('MID', 'Mid Term'),
        ('FINAL', 'Final Exam'),
        ('ASSIGNMENT', 'Assignment'),
    )

    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    exam_type = models.CharField(max_length=20, choices=EXAM_TYPES)
    total_marks = models.DecimalField(max_digits=5, decimal_places=2)
    exam_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    duration_minutes = models.PositiveIntegerField(default=30)
    deadline = models.DateTimeField(blank=True, null=True)


    def __str__(self):
        return f"{self.course.course_name} - {self.title}"


class ExamResult(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    obtained_marks = models.DecimalField(max_digits=5, decimal_places=2)
    remarks = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('exam', 'student')

    @property
    def percentage(self):
        if self.exam.total_marks:
            return round((self.obtained_marks / self.exam.total_marks) * 100, 2)
        return 0

    @property
    def grade(self):
        p = self.percentage
        if p >= 85:
            return 'A+'
        elif p >= 75:
            return 'A'
        elif p >= 65:
            return 'B'
        elif p >= 55:
            return 'C'
        elif p >= 45:
            return 'D'
        return 'F'

    @property
    def status(self):
        return 'PASS' if self.percentage >= 50 else 'FAIL'

    def __str__(self):
        return f"{self.student} - {self.exam}"

class QuizQuestion(models.Model):
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name='quiz_questions'
    )

    question_text = models.TextField()

    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255)
    option_d = models.CharField(max_length=255)

    CORRECT_ANSWER_CHOICES = (
        ('A', 'Option A'),
        ('B', 'Option B'),
        ('C', 'Option C'),
        ('D', 'Option D'),
    )

    correct_answer = models.CharField(
        max_length=1,
        choices=CORRECT_ANSWER_CHOICES
    )

    marks = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1
    )

    def __str__(self):
        return f"{self.exam.title} - {self.question_text[:50]}"


class QuizSubmission(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)

    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(blank=True, null=True)

    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    is_submitted = models.BooleanField(default=False)

    class Meta:
        unique_together = ('exam', 'student')

    def __str__(self):
        return f"{self.student} - {self.exam}"


class QuizAnswer(models.Model):
    submission = models.ForeignKey(
        QuizSubmission,
        on_delete=models.CASCADE,
        related_name='answers'
    )

    question = models.ForeignKey(
        QuizQuestion,
        on_delete=models.CASCADE
    )

    selected_answer = models.CharField(
        max_length=1,
        choices=QuizQuestion.CORRECT_ANSWER_CHOICES
    )

    is_correct = models.BooleanField(default=False)


class ExamAssignment(models.Model):
    exam = models.OneToOneField(
        Exam,
        on_delete=models.CASCADE,
        related_name='assignment_detail'
    )

    instructions = models.TextField(blank=True)
    attachment = models.FileField(
        upload_to='exam_assignments/',
        blank=True,
        null=True
    )

    deadline = models.DateTimeField()

    def __str__(self):
        return f"Assignment - {self.exam.title}"


class ExamAssignmentSubmission(models.Model):
    assignment = models.ForeignKey(
        ExamAssignment,
        on_delete=models.CASCADE,
        related_name='submissions' )

    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    submitted_file = models.FileField(upload_to='exam_assignment_submissions/')
    submitted_at = models.DateTimeField(auto_now_add=True)

    marks = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True  )

    feedback = models.TextField(blank=True)

    is_late = models.BooleanField(default=False)

    class Meta:
        unique_together = ('assignment', 'student')