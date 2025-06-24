from django.db import models
import os
import random
import string
class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Model(models.Model):
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name="models")
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ('brand', 'name')  # Ensure models are unique within each brand

    def __str__(self):
        return self.name

class SubModel(models.Model):
    model = models.ForeignKey(Model, on_delete=models.CASCADE, related_name="submodels", null=True, blank=True)
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ('model', 'name')

    def __str__(self):
        return self.name

class YearRange(models.Model):
    sub_model = models.ForeignKey(SubModel, on_delete=models.CASCADE, related_name="year_ranges")
    year_start = models.PositiveSmallIntegerField()
    year_end = models.PositiveSmallIntegerField()
    number_of_seats = models.PositiveSmallIntegerField(null=True, blank=True)
    number_of_doors = models.PositiveSmallIntegerField(null=True, blank=True)
    layout_code = models.CharField(max_length=100, unique=True)

    class Meta:
        unique_together = ('sub_model', 'year_start', 'year_end')

    def __str__(self):
        return f" {self.year_start} - {self.year_end}"
    
class SKU(models.Model):
    code = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    region = models.ForeignKey('MasterSetting', on_delete=models.SET_NULL, null=True, blank=True, related_name='skus_by_region')

    def __str__(self):
        return self.code


class MasterSetting(models.Model):
    CATEGORY_CHOICES = [
        ('Channel', 'Channel'),
        ('Country', 'Country'),
        ('Reported By', 'Reported By'),
        ('Category', 'Category'),
        ('Type', 'Type'),
        ('Series', 'Series'),
        ('Material', 'Material'),
        ('Region', 'Region'),
    ]

    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    name = models.CharField(max_length=100, unique=True)
    class Meta:
        unique_together = ('category', 'name')

    def __str__(self):
        return self.name

    
def generate_complaint_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
class Complaint(models.Model):
    complaint_id = models.CharField(primary_key=True, max_length=10, unique=True, default=generate_complaint_id)
    date = models.DateField(auto_now_add=False)
    channel = models.ForeignKey(
        'management.MasterSetting', 
        on_delete=models.SET_NULL, 
        null=True, 
        limit_choices_to={'category': 'Channel'}, 
        related_name="complaints_as_channel",
        default="Whatsapp"
    )
    country = models.ForeignKey(
        'management.MasterSetting', 
        on_delete=models.SET_NULL, 
        null=True, 
        limit_choices_to={'category': 'Country'}, 
        related_name="complaints_as_country"
    )
    person = models.ForeignKey(
        'management.MasterSetting', 
        on_delete=models.SET_NULL, 
        null=True, 
        limit_choices_to={'category': 'Reported By'}, 
        related_name="complaints_as_person"
    )
    case_category = models.ForeignKey(
        'management.MasterSetting', 
        on_delete=models.SET_NULL, 
        null=True, 
        limit_choices_to={'category': 'Category'}, 
        related_name="complaints_as_case_category"
    )
    case_sub_category = models.ForeignKey(
        'management.MasterSetting',
        on_delete=models.SET_NULL,
        null=True,
        limit_choices_to={'category': 'Type'},
        related_name="complaints_as_case_sub_category"
    )
    series = models.ForeignKey(
        'management.MasterSetting', 
        on_delete=models.SET_NULL, 
        null=True, 
        limit_choices_to={'category': 'Series'}, 
        related_name="complaints_as_series"
    )
    material = models.ForeignKey(
        'management.MasterSetting', 
        on_delete=models.SET_NULL, 
        null=True, 
        limit_choices_to={'category': 'Material'}, 
        related_name="complaints_as_material"
    )
    sku = models.ForeignKey(SKU, on_delete=models.SET_NULL, null=True, blank=True, related_name="complaints")
    brand = models.ForeignKey('management.Brand', on_delete=models.SET_NULL, null=True)
    model = models.ForeignKey('management.Model', on_delete=models.SET_NULL, null=True)
    sub_model = models.ForeignKey('management.SubModel', on_delete=models.SET_NULL, null=True, blank=True)
    year = models.ForeignKey('management.YearRange', on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=10, choices=[('Open', 'Open'), ('Closed', 'Closed'), ('On Hold', 'On Hold')], default='Open')
    priority = models.CharField(max_length=10, choices=[('High', 'High'), ('Medium', 'Medium'), ('Low', 'Low')], default='Medium')
    complaint_description = models.TextField(default="Not Provided")
    batch_order = models.CharField(max_length=100)
    justification_from_factory = models.TextField(blank=True, null=True, default="Not Provided")
    action_from_factory = models.TextField(blank=True, null=True,  default="Not Provided")
    cad_date = models.DateField(auto_now_add=False, null=True, blank=True)
    updated_order_no = models.CharField(max_length=100, blank=True, null=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)    

    def __str__(self):
        return self.complaint_id

def media_upload_path(instance, filename):
    return f'complaint_media/complaint_{instance.complaint.complaint_id}/{filename}'

class ComplaintMedia(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name='media_files')
    file = models.FileField(upload_to=media_upload_path)

    def __str__(self):
        return os.path.basename(self.file.name)
    


