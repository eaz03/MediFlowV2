from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from .forms import * # Importación de los formularios
from .forms import Patient, LoginForm
from exam.models import Exam

from ophthalmologist.models import Ophthalmologist
from django.conf import settings
from django.contrib import messages
from .forms import UploadFileForm, AddPatientForm # Importación de los formularios
from exam.utils.generate_analysis import generate_analysis_pdf
import pandas as pd
from datetime import datetime
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib.auth.forms import PasswordChangeForm
from django.core.paginator import Paginator
from django.db import transaction
import os

from exam.utils.text_extraction import add_excel_info

from media.clinic_information.exam_types import exam_types
from media.clinic_information.devices import devices
import json

# Create your views here.
def register_view(request):
    if request.user.is_authenticated:
        return redirect('menu')

    if request.method == 'POST':
        form = RegisterDoctorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Registration completed. You can now log in.')
            return redirect('login')
    else:
        form = RegisterDoctorForm()

    return render(request, 'register.html', {'form': form})


def login_view(request):
    error_message = ""
    if request.method == 'POST':
        error_message = "Invalid e-mail or password. Please verify and try again."
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            # Autenticamos el usuario
            user = authenticate(email=email, password=password)

            if user is not None:
                auth_login(request, user)

                return redirect('menu')  # Redirige al home o vista regular
            else:
                return render(request, 'login.html', {'form': form, 'error_message': error_message})
    else:
        form = LoginForm()

    return render(request, 'login.html', {'form': form, 'error_message': error_message})

def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def view_patients(request):
    searchPatient = request.GET.get('searchPatient', '')
    selected_doctor_id = request.GET.get('doctor', '')

    # Single user type: all authenticated users share the same patient view.
    patients = Patient.objects.all()
    doctors = Ophthalmologist.objects.all()

    if selected_doctor_id:
        patients = patients.filter(doctor_id=selected_doctor_id)

    if searchPatient:
        try:
            search_id = int(searchPatient)
            patients = patients.filter(identification__icontains=str(search_id))
        except ValueError:
            patients = patients.filter(name__icontains=searchPatient) | patients.filter(last_name__icontains=searchPatient)

    paginator_patients = Paginator(patients, 10)
    files = Exam.objects.all()
    page_number = request.GET.get('page')
    page_patients = paginator_patients.get_page(page_number)
    return render(request, 'view_patients.html', {'files':files, 'patients': patients, 'searchPatient': searchPatient, 'page_patients': page_patients, 'doctors': doctors, 'selected_doctor_id': selected_doctor_id})

def search(searchPatient, doctor):
    if not doctor:
        return Patient.objects.none()

    if searchPatient:
        try:
            search_id = int(searchPatient)
            patients = Patient.objects.filter(identification__icontains=str(search_id), doctor=doctor)
        except ValueError:
            patients = Patient.objects.filter(
                name__icontains=searchPatient, doctor=doctor
            )
            if not patients.exists():
                patients = Patient.objects.filter(
                    last_name__icontains=searchPatient, doctor=doctor
                )
    else:
        patients = Patient.objects.filter(doctor=doctor)

    return patients

@login_required
def new_patient(request):
    if request.method == 'POST':
        form = AddPatientForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Patient created successfully!')
            return redirect("menu") # Redirigir a una página de éxito
        else:
            messages.error(request, 'Something went wrong. Please verify and try again.')
    else:
        form = AddPatientForm()
    return render(request, 'new_patient.html', {'form': form})

@login_required
def automated_patient_extraction(request):
    # NOTE: removed destructive global delete to prevent catastrophic data loss.
    # Previous implementation deleted all Patient and Exam records before
    # processing the uploaded batch. That is unsafe and has been removed.
    if request.method == 'POST':
        try:
            patient_list = request.FILES.get('patient_list')

            add_excel_info(patient_list)
#            df = pd.read_excel(patient_list)
#
#            df.columns = df.columns.str.strip()
#            for index, row in df.iterrows():
#                print(index)
#                existing_patient = Patient.objects.filter(identification=row['Identificación']).exists()
#                if not existing_patient:
#                    patient = Patient(
#                        name=row['Nombre del paciente'],
#                        last_name="",
#                        identification=row['Identificación'],
#                        age=row['Edad'],
#                        health_insurance=row['Entidad'])
#                    patient.save()
        except Exception as e:
            return render(request, 'automated_extraction.html', {'error': "Error al procesar el archivo"})

        return redirect("menu") # Redirigir a una página de éxito
    else:
        return render(request, 'automated_extraction.html', {'error': ""})

@login_required
def next_exam(request):
    if request.method == 'POST':
        next_exams = Exam.objects.filter(is_analyzed=False)
        next_exam = next_exams.first()
        if next_exam:
            return redirect('view_pdf', pk=next_exam.id)
        else:
            return redirect('view_patients')
    else:
        return render(request, 'next_exam.html')

@login_required
def view_pdf(request, pk):
    exam = get_object_or_404(Exam, pk=pk)
    exam_types_json = json.dumps(exam_types)
    exam_types_list = list(exam_types.keys())
    ophthalmologists = Ophthalmologist.objects.all()

    default_analysis = ''
    if request.method == 'POST':
        required_fields = {
            'patient_name': 'Patient name',
            'patient_last_name': 'Patient last name',
            'patient_age': 'Patient age',
            'patient_gender': 'Patient gender',
            'patient_date_of_birth': 'Date of birth',
            'patient_health_insurance': 'Health insurance',
            'exam_date': 'Test result date',
            'exam_type': 'Exam type',
            'apparatus': 'Device/Apparatus',
            'result_analysis': 'Test result analysis',
        }

        missing_fields = [label for key, label in required_fields.items() if not (request.POST.get(key) or '').strip()]
        if missing_fields:
            messages.error(request, f"Please fill in all fields before saving: {', '.join(missing_fields)}.")
            return render(request, 'view_pdf.html', {
                'file': exam,
                'exam_types': exam_types_json,
                'exam_types_list': exam_types_list,
                'devices_list': devices,
                'ophthalmologists': ophthalmologists,
                'default_analysis': default_analysis,
            })

        try:
            with transaction.atomic():
            # Update patient data
                patient = exam.patient
                patient.name = request.POST.get('patient_name') or patient.name
                patient.last_name = request.POST.get('patient_last_name') or patient.last_name
                patient.email = request.POST.get('patient_email') or patient.email
                patient.phone = request.POST.get('patient_phone') or patient.phone
                patient.age = request.POST.get('patient_age') or patient.age
                patient.date_of_birth = request.POST.get('patient_date_of_birth') or patient.date_of_birth
                patient.gender = request.POST.get('patient_gender') or patient.gender
                patient.address = request.POST.get('patient_address') or patient.address
                patient.health_insurance = request.POST.get('patient_health_insurance') or patient.health_insurance

                doctor_id = request.POST.get('patient_doctor')
                if doctor_id:
                    try:
                        patient.doctor = Ophthalmologist.objects.get(id=doctor_id)
                    except Ophthalmologist.DoesNotExist:
                        messages.error(request, 'The selected doctor does not exist.')
                        raise

                patient.save()

                # Update exam data
                exam.result_analysis = request.POST.get('result_analysis') or ''
                exam_type = request.POST.get('exam_type') or exam.exam_type or ''
                exam.exam_type = exam_type.capitalize() if exam_type else exam.exam_type
                exam.apparatus = request.POST.get('apparatus') or exam.apparatus
                exam_date_value = request.POST.get('exam_date')
                if exam_date_value:
                    exam.exam_date = datetime.strptime(exam_date_value, '%Y-%m-%d').date()
                exam.is_analyzed = True
                exam.analysis_date = datetime.now().date()

                # Crear un PDF con el resultado del análisis
                pdf_path = f'media/results/{exam.exam_type}_{patient.name}_{patient.last_name}.pdf'
                generate_analysis_pdf(exam, patient, pdf_path, patient.doctor)

                exam.save()

            messages.success(request, 'Analysis and patient data saved successfully!')
            return redirect('view_patients')
        except Exception:
            messages.error(request, 'Could not save the analysis. Please review the data and try again.')
    return render(request, 'view_pdf.html', {
        'file': exam, 
        'exam_types': exam_types_json, 
        'exam_types_list': exam_types_list, 
        'devices_list': devices,
        'ophthalmologists': ophthalmologists,
        'default_analysis': default_analysis
    })

@login_required
def delete_patient(request, patient_id):
    try:
        patient = Patient.objects.get(id=patient_id)
    except Patient.DoesNotExist:
        messages.error(request, 'Patient not found.')
        return redirect('view_patients')
    
    if request.method == 'POST':
        patient_name = f"{patient.name} {patient.last_name}"
        patient.delete()
        messages.success(request, f'Patient {patient_name} deleted successfully!')
        return redirect('view_patients')
    else:
        return redirect('view_patients')

@login_required
def menu(request):
    return render(request, 'menu.html')

def about(request):
    return render(request, 'about.html')

def tutorial(request):
    return render(request, 'tutorial.html')
