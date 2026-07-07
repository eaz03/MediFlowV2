from exam.models import Exam, Patient
from exam.utils.calculate_age import calculate_age
from datetime import datetime
import os

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

MEDIA_ROOT = settings.MEDIA_ROOT


# Takes a list of dictionaries that correspond to a filename and relative filepath and the InMemoryUploadedFile file objects
# Creates a folder structure with the InMemoryUploadedFile file objects organized by patient folder
def process_folder_structure(folder_structure, files):
    patient_folders = {}
    print(folder_structure)
    for element in folder_structure:
        print(len(folder_structure))
        print(element)
        folder = '/'.join(element['path'].split('/')[0:-1])
        file = element['name']
        size = element.get('size')
        print(folder, file)
        # Match by name and size when possible to avoid collisions across folders
        uploaded_file = next((f for f in files if f.name == file and (not size or getattr(f, 'size', None) == size)), None)
        if not uploaded_file:
            # Fallback: match by name only
            uploaded_file = next((f for f in files if f.name == file), None)
        print(folder, file, uploaded_file)

        if folder not in patient_folders:
            patient_folders[folder] = [uploaded_file]
        else:
            patient_folders[folder].append(uploaded_file)

    return patient_folders

def save_extracted_patient(patient_info):
    if not patient_info.get('id'):
        print("Patient info not found")
        return False, patient_info
    else:
        patient = Patient.objects.filter(identification=patient_info['id']).first()
        print("searching patient")
        if not patient:
            print("Patient not found")
            patient = Patient(
                    name=patient_info.get('name', None),
                    last_name=patient_info.get('last_name', None),
                    identification=patient_info.get('id', None), 
                    age=calculate_age(patient_info.get('birthdate')) if patient_info.get('birthdate') else None,
                    date_of_birth=patient_info.get('birthdate', None),
                    gender=patient_info.get('gender', None)
                )
            patient.save()
        else:
            print("Patient found, editing")
            patient.name = patient_info.get('name', patient.name)
            patient.last_name = patient_info.get('last_name', patient.last_name)
            patient.age = calculate_age(patient_info.get('birthdate')) if patient_info.get('birthdate') else patient.age
            patient.date_of_birth = patient_info.get('birthdate', patient.date_of_birth)
            patient.save()

        return True, patient

def save_extracted_exam(patient, patient_info, exam_path):
    # Not used in new flow. Kept for compatibility.
    exam = Exam.objects.filter(patient=patient, file=exam_path).first()
    if not exam:
        exam = Exam(patient=patient, exam_date=patient_info.get('exam_date'))
        # exam_path may be a storage path or file-like
        try:
            if isinstance(exam_path, bytes):
                filename = get_new_exam_filename(patient_info)
                exam.file.save(filename, ContentFile(exam_path))
            else:
                exam.file = exam_path
        except Exception:
            exam.file = exam_path
        exam.save()
    elif exam.exam_date != patient_info.get('exam_date'):
        exam.exam_date = patient_info.get('exam_date')
        exam.save()
    return exam


def save_merged_exam_from_bytes(patient, patient_info, pdf_bytes, folder_name=""):
    """Save merged PDF bytes to Django storage and create or update Exam."""
    filename = get_new_exam_filename(patient_info, folder_name)
    exam = Exam.objects.filter(patient=patient, exam_date=patient_info.get('exam_date')).first()
    if not exam:
        exam = Exam(patient=patient, exam_date=patient_info.get('exam_date'))

    exam.file.save(filename, ContentFile(pdf_bytes), save=False)
    exam.save()
    return exam

def get_new_exam_path(patient_info, folder):
    # Deprecated: previously returned local filesystem path. Keep for compatibility.
    patient_folder_name = folder.split("/")[-1]
    try:
        exam_file_name = f"{patient_info.get('name','')}_ {patient_info.get('last_name','')}_{patient_info.get('exam_date').strftime('%Y-%m-%d')}.pdf"
    except Exception:
        exam_file_name = f"{patient_folder_name}_{datetime.now().strftime('%Y-%m-%d')}.pdf"
    return os.path.join('uploads', exam_file_name)


def get_new_exam_filename(patient_info, folder_name=""):
    try:
        safe_name = f"{patient_info.get('name','').strip()}_{patient_info.get('last_name','').strip()}_{patient_info.get('exam_date').strftime('%Y-%m-%d')}.pdf"
    except Exception:
        safe_name = f"{folder_name}_{datetime.now().strftime('%Y-%m-%d')}.pdf"
    # sanitize
    return safe_name.replace(' ', '_')
