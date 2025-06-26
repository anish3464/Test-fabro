from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .forms import ComplaintForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import Brand, Model, SubModel, YearRange, ComplaintMedia, MasterSetting, SKU, Complaint
from .forms import CarDetailsForm
from django.contrib import messages
import os
from django.db.models import Q
from django.utils.dateparse import parse_date
from collections import Counter
from django.db.models import Count
from datetime import datetime
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User, Group, Permission
from django.contrib.sessions.models import Session
from django.utils.timezone import now
from .forms import UserCreationForm, GroupCreationForm, AssignUserToGroupForm
from .models import ActivityLog  # assuming you already created this
from django.contrib.auth.models import User, Group

@login_required
def index(request):
    # Get dashboard statistics
    context = {
        'total_complaints': Complaint.objects.count(),
        'total_vehicles': YearRange.objects.count(),
        'total_skus': SKU.objects.count(),
        'total_settings': MasterSetting.objects.count(),
    }
    return render(request, 'management/index.html', context)


from django.contrib import messages
from io import TextIOWrapper
@login_required
def add_car_details(request):
    show_duplicate_modal = False
    show_layout_code_error_modal = False
    conflicting_car = None

    if request.method == "POST":
        form = CarDetailsForm(request.POST)
        if form.is_valid():
            layout_code = form.cleaned_data["layout_code"]
            brand_name = form.cleaned_data["brand_name"]
            model_name = form.cleaned_data["model_name"]
            sub_model_name = form.cleaned_data["sub_model_name"] or '-'
            year_start = form.cleaned_data["year_start"]
            year_end = form.cleaned_data["year_end"]
            number_of_seats = form.cleaned_data["number_of_seats"]
            number_of_doors = form.cleaned_data["number_of_doors"]

            brand, _ = Brand.objects.get_or_create(name=brand_name)
            model, _ = Model.objects.get_or_create(brand=brand, name=model_name)
            sub_model, _ = SubModel.objects.get_or_create(model=model, name=sub_model_name)

            # ✅ Check for layout code duplication
            if YearRange.objects.filter(layout_code=layout_code).exists():
                show_layout_code_error_modal = True

            # ✅ Check for year range overlap
            elif YearRange.objects.filter(
                sub_model=sub_model,
                year_start__lte=year_end,
                year_end__gte=year_start
            ).exists():
                show_duplicate_modal = True
                conflicting = YearRange.objects.filter(
                    sub_model=sub_model,
                    year_start__lte=year_end,
                    year_end__gte=year_start
                ).first()
                conflicting_car = {
                    "layout_code": conflicting.layout_code,
                    "brand": brand.name,
                    "model": model.name,
                    "sub_model": sub_model.name,
                    "year_start": conflicting.year_start,
                    "year_end": conflicting.year_end,
                    "number_of_seats": conflicting.number_of_seats,
                    "number_of_doors": conflicting.number_of_doors
                }

            else:
                YearRange.objects.create(
                    sub_model=sub_model,
                    year_start=year_start,
                    year_end=year_end,
                    number_of_seats=number_of_seats,
                    number_of_doors=number_of_doors,
                    layout_code=layout_code
                )
                ActivityLog.objects.create(
                user=request.user,
                action="created",
                object_type="Car",
                object_name= f"{brand_name} {model_name} {sub_model_name} ({year_start}-{year_end})"
                )
                messages.success(request, 'Vehicle added successfully!')
                return redirect('add_car_details')
    else:
        form = CarDetailsForm()

    # Fetch car data
    car_data = []
    for brand in Brand.objects.prefetch_related('models__submodels__year_ranges').all():
        for model in brand.models.all():
            for sub_model in model.submodels.all():
                for year_range in sub_model.year_ranges.all():
                    car_data.append({
                        "layout_code": year_range.layout_code,
                        "id": year_range.id,
                        "brand": brand.name,
                        "model": model.name,
                        "sub_model": sub_model.name,
                        "year_start": year_range.year_start,
                        "year_end": year_range.year_end,
                        "seats": year_range.number_of_seats,
                        "doors": year_range.number_of_doors
                    })

    return render(request, 'management/add_car_details.html', {
        'form': form,
        'car_data': car_data,
        'show_duplicate_modal': show_duplicate_modal,
        'show_layout_code_error_modal': show_layout_code_error_modal,
        'conflicting_car': conflicting_car
    })


@login_required
def car_details(request):
    car_data = []
    for brand in Brand.objects.prefetch_related('models__submodels__year_ranges').all():
        for model in brand.models.all():
            for sub_model in model.submodels.all():
                for year_range in sub_model.year_ranges.all():
                    car_data.append({
                        "layout_code": year_range.layout_code,
                        "id": year_range.id,
                        "brand": brand.name,
                        "model": model.name,
                        "sub_model": sub_model.name,
                        "year_start": year_range.year_start,
                        "year_end": year_range.year_end,
                        "seats": year_range.number_of_seats,
                        "doors": year_range.number_of_doors
                    })
    return render(request, 'management/car_details.html', {
    'car_data': car_data
    })


@login_required
def delete_car_detail(request, year_range_id):
    year_range = get_object_or_404(YearRange, id=year_range_id)
    messages.success(request, 'Vehicle deleted successfully!')
    ActivityLog.objects.create(
        user=request.user,
        action="deleted",
        object_type="Car",
        object_name=f"{year_range.sub_model.model.brand.name} {year_range.sub_model.model.name} {year_range.sub_model.name} ({year_range.year_start}-{year_range.year_end})"
    )
    year_range.delete()
    return redirect('add_car_details')

@login_required
def edit_car_detail(request, car_id):
    year_range = get_object_or_404(YearRange, id=car_id)

    # Prepopulate form values
    initial_data = {
        'layout_code': year_range.layout_code,
        'brand_name': year_range.sub_model.model.brand.name if year_range.sub_model else '',
        'model_name': year_range.sub_model.model.name if year_range.sub_model else '',
        'sub_model_name': year_range.sub_model.name if year_range.sub_model else '',
        'year_start': year_range.year_start,
        'year_end': year_range.year_end,
        'number_of_seats': year_range.number_of_seats,
        'number_of_doors': year_range.number_of_doors,
    }

    if request.method == "POST":
        form = CarDetailsForm(request.POST)
        if form.is_valid():
            layout_code = form.cleaned_data["layout_code"].strip()
            brand_name = form.cleaned_data["brand_name"].strip()
            model_name = form.cleaned_data["model_name"].strip()
            sub_model_name = form.cleaned_data["sub_model_name"].strip() or '-'
            year_start = form.cleaned_data["year_start"]
            year_end = form.cleaned_data["year_end"]
            number_of_seats = form.cleaned_data["number_of_seats"]
            number_of_doors = form.cleaned_data["number_of_doors"]

            # Check for layout code duplication (excluding current record)
            if YearRange.objects.filter(layout_code=layout_code).exclude(id=car_id).exists():
                messages.error(request, 'Layout code already exists. Please use a unique layout code.')
                return render(request, 'management/edit_car_detail.html', {
                    'form': form,
                    'car_id': car_id,
                })

            brand, _ = Brand.objects.get_or_create(name=brand_name)
            model, _ = Model.objects.get_or_create(brand=brand, name=model_name)

            sub_model = None
            if sub_model_name:
                sub_model, _ = SubModel.objects.get_or_create(model=model, name=sub_model_name)

            # Update the existing YearRange
            year_range.sub_model = sub_model
            year_range.year_start = year_start
            year_range.year_end = year_end
            year_range.number_of_seats = number_of_seats
            year_range.number_of_doors = number_of_doors
            year_range.layout_code = layout_code
            year_range.save()

            messages.success(request, 'Vehicle updated successfully!')
            ActivityLog.objects.create(
                user=request.user,
                action="updated",
                object_type="Car",
                object_name=f"{brand_name} {model_name} {sub_model_name} ({year_start}-{year_end})"
            )
            return redirect('car_details')
    else:
        form = CarDetailsForm(initial=initial_data)

    return render(request, 'management/edit_car_detail.html', {
        'form': form,
        'car_id': car_id,
    })



from django.shortcuts import render, redirect, get_object_or_404
from .models import MasterSetting
from .forms import MasterSettingForm
from django.contrib.auth.decorators import user_passes_test

@login_required
def master_settings(request):
    if not request.user.is_superuser:
        messages.error(request, "This page is restricted to administrators only.")
        return redirect('index')
    
    if request.method == "POST":
        form = MasterSettingForm(request.POST)
        if form.is_valid():
            mas=form.save()
            ActivityLog.objects.create(
                user=request.user,
                action="created",
                object_type="Master Setting",
                object_name=mas.category + " - " + mas.name
            )
            return redirect('master_settings')
    else:
        form = MasterSettingForm()

    # Fetch existing master settings, grouped by category
    master_settings = {}
    for category, _ in MasterSetting.CATEGORY_CHOICES:
        master_settings[category] = MasterSetting.objects.filter(category=category)

    return render(request, 'management/master_settings.html', {
        'form': form,
        'master_settings': master_settings
    })

@login_required
def edit_master_setting(request, setting_id):
    setting = get_object_or_404(MasterSetting, id=setting_id)

    if request.method == 'POST':
        form = MasterSettingForm(request.POST, instance=setting)
        if form.is_valid():
            form.save()
            ActivityLog.objects.create(
                user=request.user,
                action="updated",
                object_type="Master Setting",
                object_name=setting.category + " - " + setting.name
            )
            return redirect('master_settings')
    else:
        form = MasterSettingForm(instance=setting)

    return render(request, 'management/edit_master_setting.html', {
        'form': form,
        'setting': setting
    })
@login_required
def delete_master_setting(request, setting_id):
    setting = get_object_or_404(MasterSetting, id=setting_id)
    ActivityLog.objects.create(
        user=request.user,
        action="deleted",
        object_type="Master Setting",
        object_name=setting.category + " - " + setting.name
    )
    setting.delete()
    return redirect('master_settings')


@login_required
def add_complaint(request):
    if request.method == 'POST':
        form = ComplaintForm(request.POST)
        if form.is_valid():
            complaint = form.save()

            # Save each uploaded file
            for uploaded_file in request.FILES.getlist('media_files'):
                ComplaintMedia.objects.create(
                    complaint=complaint,
                    file=uploaded_file
                )
            
            ActivityLog.objects.create(
                user=request.user,
                action="created",
                object_type="complaint",
                object_name= complaint.complaint_id)
            return redirect('complaint_list')
    else:
        form = ComplaintForm()
    return render(request, 'management/add_complaint.html', {'form': form})

@login_required

def get_brands(request):
    brands = Brand.objects.all().values('id', 'name')
    return JsonResponse(list(brands), safe=False)
def get_models(request, brand_id):
    models = Model.objects.filter(brand_id=brand_id).values('id', 'name')
    return JsonResponse(list(models), safe=False)

def get_sub_models(request, model_id):
    sub_models = SubModel.objects.filter(model_id=model_id).values('id', 'name')
    return JsonResponse(list(sub_models), safe=False)

def get_year_ranges(request, sub_model_id):
    year_ranges = YearRange.objects.filter(sub_model_id=sub_model_id).values('id', 'year_start', 'year_end')
    return JsonResponse([{'id': yr['id'], 'range': f"{yr['year_start'] % 100}-{yr['year_end'] % 100}"} for yr in year_ranges], safe=False)

@login_required
def complaint_list(request):
    complaints = Complaint.objects.all()
    search_query = request.GET.get('search', '')
    search_by = request.GET.get('search_by', 'complaint_id')
    selected_brand = request.GET.get('brand')
    selected_country = request.GET.get('country')
    selected_status = request.GET.get('status')
    selected_priority = request.GET.get('priority')
    selected_channel = request.GET.get('channel')
    selected_person = request.GET.get('person')
    selected_case_category = request.GET.get('case_category')
    selected_case_sub_category = request.GET.get('case_sub_category')

    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')

    if search_query:
        filter_kwargs = {f'{search_by}__icontains': search_query}
        complaints = complaints.filter(**filter_kwargs)
    if selected_status:
        complaints = complaints.filter(status=selected_status)
    if selected_priority:
        complaints = complaints.filter(priority=selected_priority)
    if selected_channel:
        complaints = complaints.filter(channel=selected_channel)
    if selected_person:
        complaints = complaints.filter(person=selected_person) 

    if selected_brand:
        complaints = complaints.filter(brand_id=selected_brand)

    if selected_country:
        complaints = complaints.filter(country=selected_country)

    if from_date:
        complaints = complaints.filter(date__gte=parse_date(from_date))

    if to_date:
        complaints = complaints.filter(date__lte=parse_date(to_date))

    if selected_case_category:
        complaints = complaints.filter(case_category=selected_case_category)

    if selected_case_sub_category:
        complaints = complaints.filter(case_sub_category=selected_case_sub_category)

    brands = Brand.objects.all()
    countries = MasterSetting.objects.filter(id__in=Complaint.objects.values_list('country', flat=True).distinct())
    channels = MasterSetting.objects.filter(id__in=Complaint.objects.values_list('channel', flat=True).distinct())
    case_categories = MasterSetting.objects.filter(id__in=Complaint.objects.values_list('case_category', flat=True).distinct())
    case_sub_categories = MasterSetting.objects.filter(id__in=Complaint.objects.values_list('case_sub_category', flat=True).distinct())
    persons = MasterSetting.objects.filter(id__in=Complaint.objects.values_list('person', flat=True).distinct())
    statuses = Complaint.objects.values_list('status', flat=True).distinct()
    priorities = Complaint.objects.values_list('priority', flat=True).distinct()
    sku = Complaint.objects.values_list('sku__code', flat=True).distinct()

    # Status Pie Data
    status_qs = complaints.values('status').annotate(count=Count('status'))
    status_labels = [entry['status'] for entry in status_qs]
    status_data = [entry['count'] for entry in status_qs]

    # Country Pie Data
    country_qs = complaints.values('country__name').annotate(count=Count('country'))
    country_labels = [entry['country__name'] for entry in country_qs]
    country_data = [entry['count'] for entry in country_qs]

    return render(request, 'management/complaint_list.html', {
        'complaints': complaints,
        'status_labels': status_labels,
        'status_data': status_data,
        'country_labels': country_labels,
        'country_data': country_data,
        'search_query': search_query,
        'search_by': search_by,
        'selected_case_category': selected_case_category,
        'selected_case_sub_category': selected_case_sub_category,
        'selected_brand': selected_brand,
        'selected_country': selected_country,
        'selected_channel': selected_channel,
        'selected_person': selected_person,
        'selected_status': selected_status,
        'selected_priority': selected_priority,
        'from_date': from_date,
        'to_date': to_date,
        'brands': brands,
        'countries': countries,
        'channels': channels,
        'case_categories': case_categories,
        'case_sub_categories': case_sub_categories,
        'persons': persons,
        'statuses': statuses,
        'priorities': priorities,
        'sku': sku
    })


def logout_success(request):
    return render(request, 'management/logout_success.html')


@login_required
def edit_complaint(request, complaint_id):
    complaint = get_object_or_404(Complaint, complaint_id=complaint_id)

    if request.method == 'POST':
        form = ComplaintForm(request.POST, request.FILES, instance=complaint)
        if form.is_valid():
            form.save()

            # Delete selected media
            media_to_delete = request.POST.getlist('delete_media')
            for media_id in media_to_delete:
                media = ComplaintMedia.objects.get(id=media_id)
                media.file.delete()  # delete from storage
                media.delete()

            # Save new uploaded media
            for file in request.FILES.getlist('media'):
                ComplaintMedia.objects.create(complaint=complaint, file=file)

            ActivityLog.objects.create(
                user=request.user,
                action="updated",
                object_type="complaint",
                object_name=complaint_id)
            
            return redirect('complaint_list')
    else:
        form = ComplaintForm(instance=complaint)

    media_files = complaint.media_files.all()
    return render(request, 'management/edit_complaint.html', {
        'form': form,
        'complaint': complaint,
        'media_files': media_files,
    })

def delete_complaint(request, complaint_id):
    complaint = get_object_or_404(Complaint, pk=complaint_id)
    complaint.delete()
    messages.success(request, 'Complaint deleted successfully!')
    ActivityLog.objects.create(
                user=request.user,
                action="deleted",
                object_type="complaint",
                object_name=complaint_id)
    return redirect('complaint_list')


def delete_media(request, pk):
    media = get_object_or_404(ComplaintMedia, pk=pk)
    complaint_id = media.complaint.batch_order
    media.file.delete()
    media.delete()
    return redirect('edit_complaint', pk=complaint_id)

import csv
import io
import pandas as pd
from django.http import HttpResponse
from .models import Complaint

@login_required
def export_complaints(request):
    format = request.GET.get('format', 'csv')

    complaints = Complaint.objects.all()

    # Apply filters like in your complaint list view
    if 'status' in request.GET:
        complaints = complaints.filter(status=request.GET['status'])
    if 'case_type' in request.GET:
        complaints = complaints.filter(case_type__name=request.GET['case_type'])
    # Add other filters as needed...

    if format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="complaints.csv"'

        writer = csv.writer(response)
        writer.writerow(['ID', 'Vehicle', 'Status', 'Case Type', 'Created On'])

        for complaint in complaints:
            writer.writerow([
                complaint.complaint_id,
                str(complaint.model),
                complaint.status,
                complaint.case_category if complaint.case_category else '',
                complaint.date
            ])
        return response


# views.py
import csv
from io import TextIOWrapper
from django.contrib import messages
from .forms import UploadCSVForm
from .models import Brand, Model, SubModel, YearRange

def upload_car_csv(request):
    if request.method == "POST":
        form = UploadCSVForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = TextIOWrapper(request.FILES["csv_file"].file, encoding="utf-8")
            reader = csv.DictReader(csv_file)

            new_entries = []
            duplicates = []
            for row in reader:
                brand_name = row.get("brand", "").strip()
                model_name = row.get("model", "").strip()
                sub_model_name = row.get("sub_model", "").strip() or "-"
                year_start = int(row.get("year_start", 0))
                year_end = int(row.get("year_end", 0))
                seats = int(row.get("number_of_seats", 0))
                doors = int(row.get("number_of_doors", 0))
                layout_code = row.get("layout_code", "").strip()

                brand, _ = Brand.objects.get_or_create(name=brand_name)
                model, _ = Model.objects.get_or_create(brand=brand, name=model_name)
                sub_model, _ = SubModel.objects.get_or_create(model=model, name=sub_model_name)

                if YearRange.objects.filter(layout_code=layout_code).exists():
                    duplicates.append(layout_code)
                    continue

                new_entries.append(YearRange(
                    sub_model=sub_model,
                    year_start=year_start,
                    year_end=year_end,
                    number_of_seats=seats,
                    number_of_doors=doors,
                    layout_code=layout_code
                ))

            YearRange.objects.bulk_create(new_entries)

            if duplicates:
                messages.warning(request, f"Skipped {len(duplicates)} duplicate layout codes: {', '.join(duplicates)}")
            messages.success(request, f"Successfully added {len(new_entries)} records.")

            ActivityLog.objects.create(
                user=request.user,
                action="uploaded",
                object_type="Car CSV",
                object_name=f"Uploaded {len(new_entries)} new car records via CSV file"
            )
            return redirect("upload_car_csv")
    else:
        form = UploadCSVForm()

    return render(request, "management/upload_csv.html", {"form": form})

from .forms import SKUForm
from .models import SKU
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from .models import SKU, ActivityLog
from .forms import SKUForm, SKUUploadForm

def add_sku(request):
    form = SKUForm()
    skus = SKU.objects.all().order_by('code')
    upload_feedback = ''

    if request.method == "POST":
        if "add_sku" in request.POST:
            form = SKUForm(request.POST)
            if form.is_valid():
                skus=form.save()
                ActivityLog.objects.create(
                user=request.user,
                action="created",
                object_type="SKU",
                object_name=skus.code)
                return redirect('add_sku')

        elif "upload_csv" in request.POST:
            upload_form = SKUUploadForm(request.POST, request.FILES)
            if upload_form.is_valid():
                csv_file = upload_form.cleaned_data["csv_file"]
                decoded_file = TextIOWrapper(csv_file.file, encoding='utf-8')
                reader = csv.DictReader(decoded_file)

                added = 0
                skipped = 0

                for row in reader:
                    code = row.get('code', '').strip()
                    description = row.get('description', '').strip()
                    region_name = row.get('region', '').strip()

                    if not code:
                        continue  # skip rows with no code

                    if SKU.objects.filter(code=code).exists():
                        skipped += 1
                        continue

                    region = MasterSetting.objects.filter(name=region_name, setting_type='Region').first()

                    SKU.objects.create(
                        code=code,
                        description=description,
                        region=region  # may be None if region doesn't exist
                    )
                    added += 1
                ActivityLog.objects.create(
                user=request.user,
                action="uploaded",
                object_type="SKU CSV",  
                object_name=f"Uploaded {added} new SKUs via CSV file")

                upload_feedback = f"{added} SKUs added. {skipped} duplicates skipped."


    return render(request, 'management/add_skus.html', {
        'form': form,
        'skus': skus,
        'upload_feedback': upload_feedback,
        'upload_form': SKUUploadForm(),
    })

@login_required
def delete_sku(request, sku_id):
    sku = get_object_or_404(SKU, id=sku_id)
    ActivityLog.objects.create(
        user=request.user,
        action="deleted",
        object_type="SKU",
        object_name=sku.code
    )
    sku.delete()
    return redirect('add_sku')
@login_required
def edit_sku(request, sku_id):
    sku = get_object_or_404(SKU, id=sku_id)
    if request.method == 'POST':
        form = SKUForm(request.POST, instance=sku)
        if form.is_valid():
            form.save()
            ActivityLog.objects.create(
                user=request.user,
                action="updated",
                object_type="SKU",
                object_name=sku.code
            )
            return redirect('add_sku')
    else:
        form = SKUForm(instance=sku)

    return render(request, 'management/edit_sku.html', {
        'form': form,
        'sku': sku
    })




@user_passes_test(lambda u: u.is_superuser)
def admin_panel_view(request):
    user_form = UserCreationForm()
    group_form = GroupCreationForm()
    assign_form = AssignUserToGroupForm()

    if request.method == "POST":
        if 'add_user' in request.POST:
            user_form = UserCreationForm(request.POST)
            if user_form.is_valid():
                user = user_form.save(commit=False)
                user.set_password(user_form.cleaned_data['password'])
                user.save()
                ActivityLog.objects.create(
                user=request.user,
                action="created",
                object_type="User",
                object_name=user.username)

        elif 'add_group' in request.POST:
            group_form = GroupCreationForm(request.POST)
            if group_form.is_valid():
                group = group_form.save()
                ActivityLog.objects.create(
                user=request.user,
                action="created",
                object_type="Group",
                object_name=group.name)

        elif 'assign_group' in request.POST:
            assign_form = AssignUserToGroupForm(request.POST)
            if assign_form.is_valid():
                user = assign_form.cleaned_data['user']
                group = assign_form.cleaned_data['group']
                user.groups.add(group)
                ActivityLog.objects.create(
                user=request.user,
                action="assigned",
                object_type="Group",
                object_name=f"{user.username} → {group.name}")
        

    users = User.objects.all()
    groups = Group.objects.prefetch_related('permissions')
    permissions = Permission.objects.all()
    active_users = get_active_users()

    logs = ActivityLog.objects.select_related('user').order_by('-timestamp')[:20]

    return render(request, 'management/admin_panel.html', {
        'user_form': user_form,
        'group_form': group_form,
        'assign_form': assign_form,
        'active_users': active_users,
        'users': users,
        'groups': groups,
        'permissions': permissions,
        'active_sessions': active_users,
        'activity_logs': logs,
    })
@user_passes_test(lambda u: u.is_superuser)
def edit_group(request):
    if request.method == 'POST':
        group_id = request.POST.get('group_id')
        new_name = request.POST.get('name')
        group = get_object_or_404(Group, id=group_id)
        group.name = new_name
        group.save()
        ActivityLog.objects.create(
            user=request.user,
            action="edited",
            object_type="Group",
            object_name=new_name
        )
    return redirect('admin_panel')

@user_passes_test(lambda u: u.is_superuser)
def delete_group(request):
    if request.method == 'POST':
        group_id = request.POST.get('group_id')
        group = get_object_or_404(Group, id=group_id)
        ActivityLog.objects.create(
            user=request.user,
            action="deleted",
            object_type="Group",
            object_name=group.name
        )
        group.delete()
    return redirect('admin_panel')

from django.contrib.auth.models import User
from django.contrib import messages

@user_passes_test(lambda u: u.is_superuser)
def edit_user(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        username = request.POST.get('username')
        email = request.POST.get('email')

        try:
            user = User.objects.get(id=user_id)
            user.username = username
            user.email = email
            user.save()
            ActivityLog.objects.create(
                user=request.user,
                action="edited",
                object_type="User",
                object_name=username
            )
        except User.DoesNotExist:
            messages.error(request, "User not found.")

    return redirect('admin_panel')


@user_passes_test(lambda u: u.is_superuser)
def delete_user(request):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        try:
            user = User.objects.get(id=user_id)
            ActivityLog.objects.create(
                user=request.user,
                action="deleted",
                object_type="User",
                object_name=user.username
            )
            user.delete()
        except User.DoesNotExist:
            messages.error(request, "User not found.")

    return redirect('admin_panel')


from django.contrib.sessions.models import Session
from django.contrib.auth.models import User
from django.utils.timezone import now

def get_active_users():
    sessions = Session.objects.filter(expire_date__gte=now())
    active_users = []

    for session in sessions:
        data = session.get_decoded()
        user_id = data.get('_auth_user_id')
        login_time = data.get('login_time')
        ip_address = data.get('ip_address', 'N/A')

        if user_id:
            try:
                user = User.objects.get(id=user_id)
                active_users.append({
                    'user': user,
                    'login_time': login_time or 'N/A',
                    'ip': ip_address
                })
            except User.DoesNotExist:
                continue

    return active_users

