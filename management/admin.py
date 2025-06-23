from django.contrib import admin
from .models import Brand, Model, SubModel, YearRange

admin.site.register(Brand)
admin.site.register(Model)
admin.site.register(SubModel)
admin.site.register(YearRange)
