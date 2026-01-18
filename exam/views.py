from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import JsonResponse

from .forms import * # Importación de los formularios
from .forms import UploadExamForm # Importación de los formularios

from .models import Exam, Patient
from ophthalmologist.models import Ophthalmologist

from exam.utils.generate_analysis import generate_analysis_pdf
from exam.utils.text_extraction import text_extraction, extract_multiple, concatenate_pdf, add_excel_info
from exam.utils.calculate_age import calculate_age
from exam.utils.bulk_insertion_helpers import process_folder_structure, save_extracted_patient, save_extracted_exam, get_new_exam_path

from PyPDF2 import PdfReader, PdfWriter
import os
import json
from datetime import datetime

MEDIA_ROOT = settings.MEDIA_ROOT

@login_required
def new_exam(request):
    if request.method == 'POST':
        if 'new_exam' in request.POST:
            request.session.pop('patient_data', None)
            request.session.pop('exam_data', None)
            files = request.FILES.getlist('examFiles')

            if not files:
                messages.error(request, 'No files were uploaded')
                return redirect('new_exam')
            
            file_content = files[0].read()
            extracted_data = text_extraction(file_content)
            print(extracted_data)

            identification = extracted_data['id']
            birthdate = extracted_data['birthdate']
            exam_date = extracted_data['exam_date']
            gender = extracted_data['gender']
            name = extracted_data['name']
            last_name = extracted_data['last_name']

            if birthdate:
                age = calculate_age(birthdate)
            else:
                age = None

            ophthalmologists = Ophthalmologist.objects.all()
            
            existing_patient = Patient.objects.filter(identification=identification).first()
            if existing_patient:
                patient = existing_patient
            else:
                doctor_id = request.POST.get('doctor')
                doctor = Ophthalmologist.objects.get(id=doctor_id) if doctor_id else None
                email=request.POST.get('patient_email', ""),
                address=request.POST.get('patient_address', ""),
                phone=request.POST.get('patient_phone', "")

                if birthdate != '':
                    patient = Patient(
                        name=name, 
                        last_name=last_name, 
                        identification=identification, 
                        age=age, 
                        date_of_birth=birthdate, 
                        gender=gender, 
                        doctor=doctor,
                        email=email,
                        address=address,
                        phone=phone
                        )
                else:
                    patient = Patient(
                        name=name, 
                        last_name=last_name, 
                        identification=identification, 
                        age=age,
                        gender=gender, 
                        doctor=doctor,
                        email=email,
                        address=address,
                        phone=phone
                        )
                patient.save()

            if exam_date != '':
                exam = Exam(patient=patient, exam_date=exam_date, file=files[0])            
            else:
                exam = Exam(patient=patient, file=files[0])
            exam.save()

            exam_new  = exam
            patient_new = patient

            patient_data = {
                "name": patient.name,
                "last_name": patient.last_name,
                "identification": patient.identification,
                "age": patient.age,
                "date_of_birth": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
                "gender": patient.gender,
                "doctor": patient.doctor.id if patient.doctor else None,
                "email": patient.email,
                "address": patient.address,
                "phone": patient.phone,
            }

            exam_data = {
                "id": exam.id,
                "date": exam.exam_date.isoformat() if exam.exam_date else None,
                "file": exam.file.name,
                "exam_type": exam.exam_type,
                "is_analyzed": exam.is_analyzed,
                "result_analysis": exam.result_analysis
            }

            exam.delete()
            patient.delete()

            request.session['patient_data'] = patient_data
            request.session['exam_data'] = exam_data

            print("Patient data: ", patient_data)
            print(request.session['patient_data'])
            print(request.session.get('patient_data'))

            return render(request, 'exam_form_valid.html', {'patient': patient_new, 'exam': exam_new, 'ophthalmologists': ophthalmologists})

        elif 'validate_exam' in request.POST:

            # Get the previous patient
            old_patient = request.session.get('patient_data')
            old_exam = request.session.get('exam_data')

            name = request.POST.get('patient_name', old_patient["name"])
            last_name = request.POST.get('patient_last_name', old_patient["last_name"])

            identification = request.POST.get('patient_id', old_patient["identification"])

            if identification == '':
                messages.error(request, 'Identification is required')
                return render(request, 'exam_form_valid.html', {'patient': old_patient, 'exam': old_exam, 'ophthalmologists': ophthalmologists})
            elif Patient.objects.filter(identification=identification).exists():
                print("Patient exists")
                messages.error(request, 'Identification already exists')
                return render(request, 'exam_form_valid.html', {'patient': old_patient, 'exam': old_exam, 'ophthalmologists': ophthalmologists})

            date_of_birth = request.POST.get('patient_DOB', old_patient["date_of_birth"])
            age = request.POST.get('patient_age', old_patient["age"])
            gender = request.POST.get('patient_gender', old_patient["gender"])
            health_insurance = request.POST.get('patient_health', "")
            email=request.POST.get('patient_email', "")
            address=request.POST.get('patient_address', "")
            phone=request.POST.get('patient_phone', "")
            doctor_id = request.POST.get('doctor')
            doctor = Ophthalmologist.objects.get(id=doctor_id) if doctor_id else None

            date = request.POST.get('exam_date', old_exam["date"])

            exam_type = request.POST.get('exam_type', old_exam["exam_type"])
            file = old_exam["file"]
            apparatus = request.POST.get('apparatus', "")

            patient = Patient(
                name=name, 
                last_name=last_name, 
                identification=identification, 
                age=age, 
                date_of_birth=date_of_birth, 
                gender=gender, 
                health_insurance=health_insurance,
                email=email,
                address=address,
                phone=phone,
                doctor=doctor
                )
            patient.save()
            exam = Exam(patient=patient, exam_date=date, file=file, exam_type=exam_type, apparatus=apparatus)
            exam.save()
            print(exam.file.url)

            return redirect('menu')
    return render(request, 'new_exam.html')


@login_required
def multiple_exams(request):
    if request.method == 'POST':
        patient_list = request.FILES.get('patient_list')
        if form.is_valid():
            form.save()
            return redirect("menu") # Redirigir a una página de éxito
    else:
        form = UploadExamForm()
    return render(request, 'multiple_exams.html')

@login_required
def bulk_insertion(request):
    if request.method == 'POST':
        print("RECIBI POST")
        files = request.FILES.getlist('examFolders')
        csv_file = request.FILES.get('patientCSV')
        folder_structure = request.POST.get('folderStructure')
        print("Folder structure:", folder_structure)
        # ophtalmologist = request.user.ophtalmologist

        folder_structure = json.loads(folder_structure)
        patient_folders = process_folder_structure(folder_structure, files)

        add_excel_info(csv_file)
        failed_patients = []

        for folder in patient_folders.keys():
            patient_info = extract_multiple(patient_folders[folder])
            print(patient_info)

            exam_path = get_new_exam_path(patient_info, folder)

            if os.path.exists(exam_path):
                print("File already exists")
            concatenate_pdf(patient_folders[folder], exam_path)
            # Change so that I can add multiple times and it overwrites the file

            success, patient = save_extracted_patient(patient_info)

            if not success:
                failed_patients.append(patient_info)
            else:
                print("save exam")
                exam = save_extracted_exam(patient, patient_info, exam_path)

        print("fdieogwengortnmgortkgm")
        return JsonResponse({'status': 'success', 'redirect_url': '/'}) # Redirigir a una página de éxito

    return render(request, 'bulk_insertion.html')


@login_required
def download(request, path):
    exam = get_object_or_404(Exam, pk=path)
    exam.result_analysis = exam.result_analysis
    exam.is_analyzed = True
    exam.analysis_date = datetime.now()
    patient = exam.patient
    exam_date = exam.exam_date.strftime('%d/%m/%Y')
    
    file_path = f'media/{exam.exam_type}_{patient.name}_{patient.last_name}_{exam.exam_date}.pdf'
    generate_analysis_pdf(exam, patient, file_path, patient.doctor)

    exam.save()

    with open(file_path, "rb") as fh:
        response = HttpResponse(fh.read(), content_type="applicaction/pdf")
        response['Content-Disposition'] = 'inline; filename=' + os.path.basename(file_path)
        return response
    
def add_password_to_pdf(input_pdf, output_pdf, password):
    reader = PdfReader(input_pdf)
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    writer.encrypt(user_password=password)

    with open(output_pdf, 'wb') as output_file:
        writer.write(output_file)
