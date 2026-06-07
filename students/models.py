from django.db import models
from django.conf import settings


class Student(models.Model):
    GENDER_CHOICES = (
        ('Male', 'Male'),
        ('Female', 'Female'),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='student_profile'
    )

    student_id = models.CharField(
        max_length=20,
        unique=True,
        blank=True
    )

    student_nic = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True
    )

    student_image = models.ImageField(
        upload_to='students/photos/',
        blank=True,
        null=True
    )

    nic_copy = models.FileField(
        upload_to='students/nic_copies/',
        blank=True,
        null=True
    )

    date_of_birth = models.DateField(
        null=True,
        blank=True
    )

    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        blank=True,
        null=True
    )

    address = models.TextField(
        blank=True,
        null=True
    )

    admission_date = models.DateField(auto_now_add=True)

    is_suspended = models.BooleanField(default=False)
    suspended_reason = models.TextField(blank=True, null=True)
    suspended_at = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.student_id:
            super().save(*args, **kwargs)
            self.student_id = f"EUR.STU.{self.pk:04d}"
            super().save(update_fields=['student_id'])
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student_id} - {self.user.get_full_name() or self.user.username}"