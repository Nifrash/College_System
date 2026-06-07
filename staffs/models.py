from django.db import models
from django.conf import settings
from accounts.utils import generate_custom_id

class Staff(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    staff_id = models.CharField(max_length=20, unique=True, blank=True)
    department = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True)

    def save(self, *args, **kwargs):
        if not self.staff_id:
            self.staff_id = generate_custom_id(Staff, 'staff_id', 'EUR.STF')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.staff_id} - {self.user.username}"