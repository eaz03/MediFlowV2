from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from .forms import * # Importación de los formularios
from .forms import *
from exam.models import Exam
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm
from django.core.paginator import Paginator

@login_required
def create_user(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('menu')  
    else:
        form = CustomUserCreationForm()

    return render(request, 'user_create.html', {'form': form})

@login_required
def administrator(request):
    searchDoctor = request.GET.get('searchDoctor', '')
    doctors = search_doctor(searchDoctor)
    searchPatient = request.GET.get('searchPatient', '')
    patients = search_patient(searchPatient)
    paginator_patients = Paginator(patients, 10)
    files = Exam.objects.all()
    paginator_doctors = Paginator(doctors, 10)
    page_number = request.GET.get('page')
    page_patients = paginator_patients.get_page(page_number)
    page_doctors = paginator_doctors.get_page(page_number)
    return render(request, 'administrator.html', {'patients': patients, 'files': files, 
    'doctors': doctors, 'serachDoctor': searchDoctor, 'searchPatient': searchPatient, 
    'page_patients': page_patients, 'page_doctors': page_doctors})

@login_required
def new_ophthalmologist(request):
    if request.method == 'POST':
        form = AddOphthalmologistForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ophthalmologist created successfully!')
            return redirect("administrator")
        else:
            messages.error(request, 'Something went wrong. Please verify and try again.')
    else:
        form = AddOphthalmologistForm()
    return render(request, 'new_ophthalmologist.html', {'form': form})

@login_required
def delete_ophthalmologist(request, medical_license):
    if request.method == 'POST':
        ophthalmologist = Ophthalmologist.objects.get(medical_license=medical_license)
        if ophthalmologist:
            ophthalmologist.delete()
            messages.success(request, f'Ophthalmologist with medical license {medical_license} deleted successfully!')
        else:
            messages.error(request, f'Ophthalmologist with medical license {medical_license} not found.')
        return redirect('administrator')

    return redirect('administrator')

@login_required
def delete_patient(request, identification):
    if request.method == 'POST':
        patient = Patient.objects.filter(identification=identification).first()
        if patient:
            patient.delete()
            messages.success(request, f'Patient with ID {identification} deleted successfully!')
        else:
            messages.error(request, f'Patient with ID {identification} not found.')
        return redirect('administrator')

    return redirect('administrator')

@login_required
def edit_ophthalmologist(request, medical_license):
    doctor = get_object_or_404(Ophthalmologist, medical_license=medical_license)
    
    if request.method == 'POST':
        form = EditOphthalmologistForm(request.POST, instance=doctor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ophthalmologist updated successfully!')
            return redirect('administrator')
        else:
            messages.error(request, 'Something went wrong. Please verify and try again.')
    else:
        form = EditOphthalmologistForm(instance=doctor)
    
    return render(request, 'edit_ophthalmologist.html', {'form': form})

@login_required
def edit_patient(request, identification):
    patient = get_object_or_404(Patient, identification=identification)
    
    if request.method == 'POST':
        form = EditPatientForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, 'Patient updated successfully!')
            return redirect('administrator')
        else:
            messages.error(request, 'Something went wrong. Please verify and try again.')
    else:
        form = EditPatientForm(instance=patient)
    
    return render(request, 'edit_patient.html', {'form': form})

def search_patient(searchPatient):
    try:
        search_id = int(searchPatient)
        patients = Patient.objects.filter(identification__icontains = str(search_id))
    except ValueError:
        if searchPatient:
            patients = Patient.objects.filter(name__icontains = searchPatient)
            if not patients:
                patients = Patient.objects.filter(last_name__icontains = searchPatient)
        else:
            patients = Patient.objects.all()
    return patients

def search_doctor(searchDoctor):
    try:
        search_id = int(searchDoctor)
        doctors = Ophthalmologist.objects.filter(medical_license__icontains = str(search_id))
    except ValueError:
        if searchDoctor:
            doctors = Ophthalmologist.objects.filter(name__icontains = searchDoctor)
            if not doctors:
                doctors = Ophthalmologist.objects.filter(last_name__icontains = searchDoctor)
        else:
            doctors = Ophthalmologist.objects.all()
    return doctors