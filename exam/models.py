from django.db import models
from ophthalmologist.models import Patient

# Create your models here.
class Exam(models.Model):
    id = models.AutoField(primary_key=True)
    exam_date = models.DateField(null=True, blank=True)
    analysis_date = models.DateField(null=True, blank=True)
    file = models.FileField(upload_to='uploads/')
    result_analysis = models.TextField(blank=True)
    is_analyzed = models.BooleanField(default=False)
    is_validated = models.BooleanField(default=False)
    apparatus = models.CharField(max_length=50, blank=True, null=True)
    exam_type = models.CharField(max_length=50, blank=True, null=True)

    #doctor = models.ForeignKey(Ophtalmologist, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)

    def __str__(self):
        return f"File {self.id} - {self.exam_date}"