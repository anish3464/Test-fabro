from django import forms
from .models import Complaint, ComplaintMedia

class CarDetailsForm(forms.Form):
    layout_code = forms.CharField(label="Layout Code", max_length=100)
    brand_name = forms.CharField(label="Brand Name", max_length=100)
    model_name = forms.CharField(label="Model Name", max_length=100)
    sub_model_name = forms.CharField(label="Sub-Model Name", max_length=100, required=False,)
    year_start = forms.IntegerField(label="Year Start", min_value=1900, max_value=2100)
    year_end = forms.IntegerField(label="Year End", min_value=1900, max_value=2100)
    number_of_seats = forms.IntegerField(label="Number of Seats", min_value=1)
    number_of_doors = forms.IntegerField(label="Number of Doors", min_value=1)
    
    widgets = {
        'layout_code': forms.TextInput(attrs={'class': 'form-input'}),
        'brand_name': forms.TextInput(attrs={'class': 'form-input'}),
        'model_name': forms.TextInput(attrs={'class': 'form-input'}),
        'sub_model_name': forms.TextInput(attrs={'class': 'form-input'}),
        'year_start': forms.NumberInput(attrs={'class': 'form-input'}),
        'year_end': forms.NumberInput(attrs={'class': 'form-input'}),
        'number_of_seats': forms.NumberInput(attrs={'class': 'form-input'}),
        'number_of_doors': forms.NumberInput(attrs={'class': 'form-input'}),
    }

    def clean(self):
        cleaned_data = super().clean()
        for field in ['brand_name', 'model_name', 'sub_model_name', 'layout_code']:
            if field in cleaned_data and isinstance(cleaned_data[field], str):
                cleaned_data[field] = cleaned_data[field].strip()
        year_start = cleaned_data.get("year_start")
        year_end = cleaned_data.get("year_end")
        
        if year_start and year_end and year_start > year_end:
            self.add_error("year_end", "Year End must be greater than or equal to Year Start.")
        
        return cleaned_data

from django import forms
from .models import MasterSetting

class MasterSettingForm(forms.ModelForm):
    class Meta:
        model = MasterSetting
        fields = ['category', 'name']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            }

from django import forms
from .models import Complaint, MasterSetting, Brand, Model, SubModel, YearRange

class ComplaintForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = [
            'complaint_id','date', 'channel', 'country', 'person', 'case_category','case_sub_category', 'series', 'material', 
            'brand', 'model', 'sub_model', 'year', 'status','priority','sku', 'cad_date', 'updated_order_no',
            'complaint_description', 'batch_order', 
            'justification_from_factory', 'action_from_factory'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'complaint_id': forms.TextInput(attrs={'class': 'form-input'}),
            'channel': forms.Select(attrs={'class': 'form-select'}),
            'country': forms.Select(attrs={'class': 'form-select'}),
            'person': forms.Select(attrs={'class': 'form-select'}),
            'case_category': forms.Select(attrs={'class': 'form-select'}),
            'case_sub_category': forms.Select(attrs={'class': 'form-select'}),
            'series': forms.Select(attrs={'class': 'form-select'}),
            'material': forms.Select(attrs={'class': 'form-select'}),
            'brand': forms.Select(attrs={'class': 'form-select'}),
            'model': forms.Select(attrs={'class': 'form-select'}),
            'sub_model': forms.Select(attrs={'class': 'form-select'}),
            'year': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'cad_date': forms.DateInput(attrs={'type': 'date'}),
            'updated_order_no': forms.TextInput(attrs={'class': 'form-input'}),
            'sku': forms.Select(attrs={'class': 'form-select'}),
            'complaint_description': forms.Textarea(attrs={'rows': 3, 'class': 'form-textarea'}),
            'batch_order': forms.TextInput(attrs={'class': 'form-input'}),
            'justification_from_factory': forms.Textarea(attrs={'rows': 3, 'class': 'form-textarea'}),
            'action_from_factory': forms.Textarea(attrs={'rows': 3, 'class': 'form-textarea'}),

        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['brand'].queryset = Brand.objects.all()
        self.fields['model'].queryset = Model.objects.none()
        self.fields['sub_model'].queryset = SubModel.objects.none()
        self.fields['year'].queryset = YearRange.objects.none()
        self.fields['sku'].choices = [(sku.id, f"{sku.code} - {sku.description}") for sku in SKU.objects.all()]

        if 'brand' in self.data:
            try:
                brand_id = int(self.data.get('brand'))
                self.fields['model'].queryset = Model.objects.filter(brand_id=brand_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            self.fields['model'].queryset = Model.objects.filter(brand=self.instance.brand)
        if 'model' in self.data:
            try:
                model_id = int(self.data.get('model'))
                self.fields['sub_model'].queryset = SubModel.objects.filter(model_id=model_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            self.fields['sub_model'].queryset = SubModel.objects.filter(model=self.instance.model)
        if 'sub_model' in self.data:
            try:
                sub_model_id = int(self.data.get('sub_model'))
                self.fields['year'].queryset = YearRange.objects.filter(sub_model_id=sub_model_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            self.fields['year'].queryset = YearRange.objects.filter(sub_model=self.instance.sub_model)

# forms.py
from django import forms

class UploadCSVForm(forms.Form):
    csv_file = forms.FileField(label="Upload CSV File")


from .models import SKU
from django import forms
class SKUForm(forms.ModelForm):
    class Meta:
        model = SKU
        fields = ['code', 'description', 'region']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'region': forms.Select(attrs={'class': 'form-select'}),
        }
    def __init__(self, *args, **kwargs):
        super(SKUForm, self).__init__(*args, **kwargs)
        self.fields['region'].queryset = MasterSetting.objects.filter(category='Region')


class SKUUploadForm(forms.Form):
    csv_file = forms.FileField(label="Upload CSV File")
    def clean_csv_file(self):
        csv_file = self.cleaned_data.get('csv_file')
        if not csv_file.name.endswith('.csv'):
            raise forms.ValidationError("File must be a CSV.")
        return csv_file
    widgets = {
        'csv_file': forms.ClearableFileInput(attrs={'class': 'file-input'}),
    }
