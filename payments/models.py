from django.db import models
from django.db.models import Sum
from students.models import Student
from courses.models import Course

class Payment(models.Model):
    PAYMENT_METHODS = (
        ('CASH', 'Cash'),
        ('CARD', 'Card'),
        ('BANK', 'Bank Transfer'),
    )

    STATUS = (
        ('PAID', 'Paid'),
        ('PENDING', 'Pending'),
    )

    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    installment_number = models.PositiveIntegerField(default=1)
    total_installments = models.PositiveIntegerField(default=1)
    payment_date = models.DateField(auto_now_add=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    status = models.CharField(max_length=20, choices=STATUS)
    reference_no = models.CharField(max_length=100, unique=True, blank=True)
    invoice_pdf = models.FileField(upload_to='payment_invoices/', blank=True, null=True)

    @property
    def total_paid_for_course(self):
        total = Payment.objects.filter(
            student=self.student,
            course=self.course,
            status='PAID'
        ).aggregate(total=Sum('amount'))['total']

        return total or 0

    @property
    def remaining_balance(self):
        return self.course.course_fee - self.total_paid_for_course

    def save(self, *args, **kwargs):
        if not self.reference_no:
            super().save(*args, **kwargs)
            self.reference_no = f"PAY.{self.pk:05d}"
            super().save(update_fields=['reference_no'])
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference_no} - {self.student} - {self.course}"