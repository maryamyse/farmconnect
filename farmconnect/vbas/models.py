from django.db import models

class VBA(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, unique=True)
    location = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Farmer(models.Model):
    vba = models.ForeignKey(VBA, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    age = models.IntegerField()
    gender = models.CharField(max_length=10)
    household_code = models.CharField(max_length=20)
    phone = models.CharField(max_length=20, blank=True)
    village = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name

class Visit(models.Model):
    vba = models.ForeignKey(VBA, on_delete=models.CASCADE)
    date = models.DateField()
    village = models.CharField(max_length=100)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.vba.name} - {self.date}"
