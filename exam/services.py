"""
Exam service layer - handles exam creation, validation, and data extraction.
Follows dependency inversion: extraction strategy is injected, not hardcoded.
"""
from typing import Dict, Any, Optional, Tuple
from django.db import transaction
from django.core.files.uploadedfile import UploadedFile
import logging

from exam.models import Exam
from ophthalmologist.models import Patient, Ophthalmologist
from exam.extractors import TextExtractor
from exam.utils.calculate_age import calculate_age

logger = logging.getLogger(__name__)


class ExamUploadService:
    """
    Service for uploading and validating exams.
    Handles the two-step process: upload → validate/save.
    """

    def __init__(self, text_extractor: Optional[TextExtractor] = None):
        """
        Initialize with a text extraction strategy.
        If none provided, uses default regex-based extractor.
        """
        self.text_extractor = text_extractor or TextExtractor()

    def step1_extract_and_save(
        self,
        uploaded_file: UploadedFile,
        doctor_id: Optional[int] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Step 1: Extract data from file and save temporary exam record.

        Args:
            uploaded_file: Django UploadedFile from form
            doctor_id: ID of ophthalmologist (optional)

        Returns:
            Tuple of (success: bool, response_data: dict)
            response_data contains: exam_id, extracted_data, ophthalmologists list
        """
        try:
            # Validate file
            is_valid, error_msg = self._validate_file(uploaded_file)
            if not is_valid:
                return False, {'error': error_msg}

            # Extract data from file
            extracted_data = self.text_extractor.extract(uploaded_file)
            if not extracted_data:
                return False, {'error': 'Failed to extract data from file'}

            # Get or create patient
            patient_result = self._get_or_create_patient(extracted_data, doctor_id)
            if not patient_result[0]:
                return False, {'error': patient_result[1]}

            patient = patient_result[1]

            # Create temporary exam record (is_validated=False)
            exam = self._create_temp_exam(patient, uploaded_file, extracted_data)

            # Prepare response
            response_data = {
                'exam_id': exam.id,
                'extracted_data': extracted_data,
                'file_url': exam.file.url,
                'patient': {
                    'id': patient.id,
                    'name': patient.name,
                    'last_name': patient.last_name,
                    'identification': patient.identification,
                    'age': patient.age,
                    'date_of_birth': patient.date_of_birth.isoformat() if patient.date_of_birth else None,
                    'gender': patient.gender,
                    'doctor': patient.doctor.id if patient.doctor else None,
                    'email': patient.email,
                    'address': patient.address,
                    'phone': patient.phone,
                },
                'ophthalmologists': [
                    {'id': doc.id, 'name': f"{doc.name} {doc.last_name}"}
                    for doc in Ophthalmologist.objects.all()
                ],
            }

            logger.info(f"Step 1 complete: Exam {exam.id} created for patient {patient.identification}")
            return True, response_data

        except Exception as e:
            logger.error(f"Step 1 failed: {str(e)}", exc_info=True)
            return False, {'error': 'An error occurred while processing the file'}

    def step2_validate_and_save(
        self,
        exam_id: int,
        form_data: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """
        Step 2: Validate user edits and finalize exam record.

        Args:
            exam_id: ID of exam to update
            form_data: Form POST data with edited patient/exam info

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            exam = Exam.objects.select_related('patient').get(id=exam_id)

            # Validate form data
            is_valid, error_msg = self._validate_form_data(form_data, exam.patient)
            if not is_valid:
                return False, error_msg

            # Update patient with form data
            self._update_patient(exam.patient, form_data)

            # Update exam with form data
            self._update_exam(exam, form_data)

            # Mark as validated
            exam.is_validated = True
            exam.save()

            logger.info(f"Step 2 complete: Exam {exam.id} validated")
            return True, None

        except Exam.DoesNotExist:
            error_msg = f"Exam {exam_id} not found"
            logger.error(error_msg)
            return False, error_msg

        except Exception as e:
            logger.error(f"Step 2 failed: {str(e)}", exc_info=True)
            return False, f"An error occurred: {str(e)}"

    # ===== PRIVATE HELPER METHODS =====

    def _validate_file(self, uploaded_file: UploadedFile) -> Tuple[bool, Optional[str]]:
        """Validate file format and size."""
        # Check file format
        if not uploaded_file.name.lower().endswith('.pdf'):
            return False, 'Only PDF files are supported'

        # Check file size (max 50MB)
        if uploaded_file.size > 50 * 1024 * 1024:
            return False, 'File size exceeds 50MB limit'

        return True, None

    def _get_or_create_patient(
        self,
        extracted_data: Dict[str, Any],
        doctor_id: Optional[int] = None,
    ) -> Tuple[bool, Any]:
        """
        Get existing patient or create new one.
        Returns: (success: bool, patient_or_error: Patient or str)
        """
        identification = extracted_data.get('id')

        if not identification:
            return False, "Could not extract patient ID from file"

        # Check if patient already exists
        existing_patient = Patient.objects.filter(identification=identification).first()
        if existing_patient:
            return True, existing_patient

        # Create new patient
        try:
            doctor = None
            if doctor_id:
                doctor = Ophthalmologist.objects.get(id=doctor_id)

            age = None
            if extracted_data.get('birthdate'):
                age = calculate_age(extracted_data['birthdate'])

            patient = Patient.objects.create(
                name=extracted_data.get('name', ''),
                last_name=extracted_data.get('last_name', ''),
                identification=identification,
                age=age,
                date_of_birth=extracted_data.get('birthdate'),
                gender=extracted_data.get('gender', ''),
                health_insurance=extracted_data.get('health_insurance', ''),
                doctor=doctor,
            )

            logger.info(f"Created new patient: {patient.identification}")
            return True, patient

        except Exception as e:
            logger.error(f"Failed to create patient: {str(e)}")
            return False, f"Failed to create patient: {str(e)}"

    def _create_temp_exam(
        self,
        patient: Patient,
        uploaded_file: UploadedFile,
        extracted_data: Dict[str, Any],
    ) -> Exam:
        """Create temporary exam record (not validated yet)."""
        exam = Exam.objects.create(
            patient=patient,
            file=uploaded_file,
            exam_date=extracted_data.get('exam_date'),
            is_validated=False,
        )
        return exam

    def _validate_form_data(
        self,
        form_data: Dict[str, Any],
        patient: Patient,
    ) -> Tuple[bool, Optional[str]]:
        """Validate form data before saving."""
        identification = form_data.get('patient_identification')

        if not identification:
            return False, 'Patient ID is required'

        # Check if ID matches current patient or is unique
        if identification != patient.identification:
            if Patient.objects.filter(identification=identification).exists():
                return False, 'This patient ID is already in use'

        return True, None

    def _update_patient(self, patient: Patient, form_data: Dict[str, Any]) -> None:
        """Update patient record with form data."""
        patient.name = form_data.get('patient_name', patient.name)
        patient.last_name = form_data.get('patient_last_name', patient.last_name)
        patient.email = form_data.get('patient_email', patient.email)
        patient.phone = form_data.get('patient_phone', patient.phone)
        patient.age = form_data.get('patient_age', patient.age)
        patient.date_of_birth = form_data.get('patient_date_of_birth', patient.date_of_birth)
        patient.gender = form_data.get('patient_gender', patient.gender)
        patient.address = form_data.get('patient_address', patient.address)
        patient.health_insurance = form_data.get('patient_health_insurance', patient.health_insurance)

        # Update doctor if provided
        doctor_id = form_data.get('patient_doctor')
        if doctor_id:
            try:
                patient.doctor = Ophthalmologist.objects.get(id=doctor_id)
            except Ophthalmologist.DoesNotExist:
                pass

        patient.save()

    def _update_exam(self, exam: Exam, form_data: Dict[str, Any]) -> None:
        """Update exam record with form data."""
        exam.exam_date = form_data.get('exam_date', exam.exam_date)
        exam.apparatus = form_data.get('apparatus', exam.apparatus)
        exam.exam_type = form_data.get('exam_type', exam.exam_type)
        exam.save()
