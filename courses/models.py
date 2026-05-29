from django.db import models
from college_management import settings
from lecturers.models import Lecturer

class Course(models.Model):
    SEMESTER_CHOICES = (
        ('SEM1', 'Semester 1'),
        ('SEM2', 'Semester 2'),
        ('SEM3', 'Semester 3'),
        ('SEM4', 'Semester 4'),
    )

    course_code = models.CharField(max_length=20, unique=True, blank=True)
    course_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    credits = models.IntegerField()
    course_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    semester = models.CharField(
        max_length=20,
        choices=SEMESTER_CHOICES,
        default='SEM1'
    )

    total_hours = models.PositiveIntegerField(default=0)

    lecturers = models.ManyToManyField(Lecturer, blank=True, related_name='courses')

    def save(self, *args, **kwargs):
        if not self.course_code:
            super().save(*args, **kwargs)
            self.course_code = f"CRS.{self.pk:04d}"
            super().save(update_fields=['course_code'])
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.course_code} - {self.course_name}"

class Enrollment(models.Model):

    MODE_CHOICES = (
        ('ONLINE', 'Online'),
        ('PHYSICAL', 'Physical'),
    )

    INSTALLMENT_CHOICES = (
        (1, '1 Installment'),
        (2, '2 Installments'),
        (3, '3 Installments'),
        (4, '4 Installments'),
        (6, '6 Installments'),
        (12, '12 Installments'),
    )

    PAYMENT_METHODS = (
        ('CASH', 'Cash'),
        ('CARD', 'Card'),
        ('BANK', 'Bank Transfer'),
    )

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'STUDENT'}
    )

    course = models.ForeignKey(Course, on_delete=models.CASCADE)

    mode_of_study = models.CharField(
        max_length=20,
        choices=MODE_CHOICES,
        default='PHYSICAL'
    )

    original_course_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    final_course_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    preferred_payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        default='CASH'
    )

    number_of_installments = models.PositiveIntegerField(
        choices=INSTALLMENT_CHOICES,
        default=1
    )

    enrolled_date = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'course')

    def save(self, *args, **kwargs):
        if self.course and not self.original_course_fee:
            self.original_course_fee = self.course.course_fee

        self.final_course_fee = self.original_course_fee - self.discount_amount

        if self.final_course_fee < 0:
            self.final_course_fee = 0

        super().save(*args, **kwargs)

    @property
    def installment_amount(self):
        if self.number_of_installments:
            return self.final_course_fee / self.number_of_installments
        return self.final_course_fee

    def __str__(self):
        return f"{self.student} - {self.course}"

