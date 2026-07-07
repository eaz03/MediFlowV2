from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import transaction

from .forms import UploadExamForm
from .models import Exam, Patient
from ophthalmologist.models import Ophthalmologist

from exam.utils.generate_analysis import generate_analysis_pdf
from exam.utils.text_extraction import extract_multiple, concatenate_pdf_bytes, add_excel_info
from exam.utils.calculate_age import calculate_age
from exam.utils.bulk_insertion_helpers import (
    process_folder_structure,
    save_extracted_patient,
    save_extracted_exam,
    get_new_exam_path,
    save_merged_exam_from_bytes,
)
from exam.services import ExamUploadService

from PyPDF2 import PdfReader, PdfWriter
import os
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
MEDIA_ROOT = settings.MEDIA_ROOT


@login_required
def new_exam(request):
    """
    Two-step exam upload process:
    Step 1: Upload file → Extract data → Show form
    Step 2: Edit/confirm → Validate and save
    """
    service = ExamUploadService()

    if request.method == 'POST':
        if 'new_exam' in request.POST:
            # STEP 1: Extract and save temporary exam
            uploaded_file = request.FILES.get('examFiles')
            if not uploaded_file:
                messages.error(request, 'No file was uploaded')
                return redirect('new_exam')

            doctor_id = request.POST.get('doctor')
            success, response_data = service.step1_extract_and_save(uploaded_file, doctor_id)

            if not success:
                messages.error(request, response_data.get('error', 'Failed to process file'))
                return redirect('new_exam')

            # Render form with extracted data
            exam = Exam.objects.get(id=response_data['exam_id'])
            return render(request, 'exam_form_valid.html', {
                'exam_id': response_data['exam_id'],
                'exam': exam,
                'extracted_data': response_data['extracted_data'],
                'patient_data': response_data['patient'],
                'ophthalmologists': response_data['ophthalmologists'],
            })

        elif 'validate_exam' in request.POST:
            # STEP 2: Validate and save exam
            exam_id = request.POST.get('exam_id')
            if not exam_id:
                messages.error(request, 'Invalid exam ID')
                return redirect('new_exam')

            # Prepare form data
            form_data = {
                'patient_name': request.POST.get('patient_name'),
                'patient_last_name': request.POST.get('patient_last_name'),
                'patient_identification': request.POST.get('patient_id'),
                'patient_email': request.POST.get('patient_email'),
                'patient_phone': request.POST.get('patient_phone'),
                'patient_age': request.POST.get('patient_age'),
                'patient_date_of_birth': request.POST.get('patient_DOB'),
                'patient_gender': request.POST.get('patient_gender'),
                'patient_address': request.POST.get('patient_address'),
                'patient_health_insurance': request.POST.get('patient_health'),
                'patient_doctor': request.POST.get('doctor'),
                'exam_date': request.POST.get('exam_date'),
                'apparatus': request.POST.get('apparatus'),
                'exam_type': request.POST.get('exam_type'),
            }

            success, error_msg = service.step2_validate_and_save(int(exam_id), form_data)

            if not success:
                messages.error(request, error_msg or 'Failed to save exam')
                # Reload form for re-editing
                exam = Exam.objects.get(id=exam_id)
                patient_data = {
                    'id': exam.patient.id,
                    'name': exam.patient.name,
                    'last_name': exam.patient.last_name,
                    'identification': exam.patient.identification,
                    'age': exam.patient.age,
                    'date_of_birth': exam.patient.date_of_birth.isoformat() if exam.patient.date_of_birth else None,
                    'gender': exam.patient.gender,
                    'doctor': exam.patient.doctor.id if exam.patient.doctor else None,
                    'email': exam.patient.email,
                    'address': exam.patient.address,
                    'phone': exam.patient.phone,
                }
                ophthalmologists = [
                    {'id': doc.id, 'name': f"{doc.name} {doc.last_name}"}
                    for doc in Ophthalmologist.objects.all()
                ]
                return render(request, 'exam_form_valid.html', {
                    'exam_id': exam.id,
                    'exam': exam,
                    'extracted_data': form_data,
                    'patient_data': patient_data,
                    'ophthalmologists': ophthalmologists,
                })

            messages.success(request, 'Exam uploaded successfully!')
            return redirect('menu')

    # GET request: show initial upload form
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
        files = request.FILES.getlist('examFolders')
        csv_file = request.FILES.get('patientCSV')
        folder_structure = request.POST.get('folderStructure')
        if not files:
            return JsonResponse({
                'status': 'error',
                'message': 'No exam files were uploaded. Select a folder with PDF files and try again.',
            }, status=400)

        if not csv_file:
            return JsonResponse({
                'status': 'error',
                'message': 'The programming spreadsheet is missing. Upload the XLS/XLSX file before submitting.',
            }, status=400)

        try:
            folder_structure = json.loads(folder_structure or '[]')
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': 'The folder structure could not be read from the browser. Please select the folder again.',
            }, status=400)

        patient_folders = process_folder_structure(folder_structure, files)

        try:
            add_excel_info(csv_file)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'The spreadsheet could not be processed: {e}',
            }, status=400)

        failed_patients = []
        processed_folders = 0
        created_records = 0

        for folder, uploaded_files in patient_folders.items():
            try:
                with transaction.atomic():
                    if not uploaded_files or any(uploaded_file is None for uploaded_file in uploaded_files):
                        raise ValueError('one or more PDFs in this folder could not be matched to the uploaded files')

                    processed_folders += 1

                    # Extract combined data from files belonging to this patient folder
                    patient_info = extract_multiple(uploaded_files)

                    if not patient_info.get('id'):
                        raise ValueError('patient ID was not detected in the PDF files')

                    if not patient_info.get('exam_date'):
                        raise ValueError('exam date was not detected in the PDF files')

                    # Merge PDFs into bytes
                    merged_bytes = concatenate_pdf_bytes(uploaded_files)

                    # Save or update patient
                    success, patient = save_extracted_patient(patient_info)
                    if not success:
                        raise ValueError('patient data could not be extracted or saved')

                    # Save merged PDF to storage and create Exam
                    save_merged_exam_from_bytes(patient, patient_info, merged_bytes, folder)
                    created_records += 1
            except Exception as e:
                failed_patients.append({
                    'folder': folder,
                    'stage': 'processing',
                    'error': str(e),
                    'hint': 'Check that the folder contains only PDFs and that the first page includes the patient ID and exam date.',
                })
                continue

        if failed_patients:
            return JsonResponse({
                'status': 'partial_success',
                'redirect_url': '/',
                'summary': {
                    'processed_folders': processed_folders,
                    'created_records': created_records,
                    'failed_folders': len(failed_patients),
                },
                'failed_patients': failed_patients,
            })

        return JsonResponse({
            'status': 'success',
            'redirect_url': '/',
            'summary': {
                'processed_folders': processed_folders,
                'created_records': created_records,
                'failed_folders': 0,
            },
        })

    return render(request, 'bulk_insertion.html')


@login_required
def download(request, path):
    exam = get_object_or_404(Exam, pk=path)
    exam.result_analysis = exam.result_analysis
    exam.is_analyzed = True
    exam.analysis_date = datetime.now()
    patient = exam.patient
    exam_date_for_name = exam.exam_date.strftime('%Y-%m-%d') if exam.exam_date else datetime.now().date().strftime('%Y-%m-%d')
    
    file_path = f'media/{exam.exam_type}_{patient.name}_{patient.last_name}_{exam_date_for_name}.pdf'
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
