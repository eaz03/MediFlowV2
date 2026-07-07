"""
Text extraction abstraction - supports multiple extraction strategies.
Dependency inversion: Views don't know about specific extraction implementations.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
from django.core.files.uploadedfile import UploadedFile
import io
import re
import datetime
import logging

import pdfplumber

logger = logging.getLogger(__name__)


class ExtractorStrategy(ABC):
    """Abstract base class for text extraction strategies."""

    @abstractmethod
    def extract(self, file_content: bytes) -> Dict[str, Any]:
        """
        Extract data from file content.

        Args:
            file_content: Raw file bytes

        Returns:
            Dict with keys: id, name, last_name, birthdate, exam_date, gender
        """
        pass


class RegexTextExtractor(ExtractorStrategy):
    """
    Extract text from PDF using regex patterns.
    Handles Spanish and English formats.
    """

    def extract(self, file_content: bytes) -> Dict[str, Any]:
        """Extract text using regex patterns."""
        try:
            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                if not pdf.pages:
                    logger.warning("PDF has no pages")
                    return self._empty_result()

                first_page = pdf.pages[0]
                text = first_page.extract_text()

                if not text:
                    logger.warning("Could not extract text from PDF")
                    return self._empty_result()

                return {
                    'id': self._extract_id(text),
                    'name': self._extract_name(text),
                    'last_name': self._extract_last_name(text),
                    'birthdate': self._extract_birthdate(text),
                    'exam_date': self._extract_exam_date(text),
                    'gender': self._extract_gender(text),
                }
        except Exception as e:
            logger.error(f"Regex extraction failed: {str(e)}", exc_info=True)
            return self._empty_result()

    def _extract_id(self, text: str) -> str:
        """Extract patient ID."""
        match = re.search(r"(?:(?<=ID:)|(?<=ID de paciente))\s?[0-9]+", text)
        return match.group().strip() if match else ''

    def _extract_name(self, text: str) -> str:
        """Extract first name."""
        match = re.search(
            r"(?<=Name:)\s?.* .*, \w+|(?<=Nombre:)\s?.* .*, .*?(?=OD|OS)|([A-Za-záéíóúüñ ]+),\s+([A-Za-záéíóúüñ ]+)(?=\s+Paciente)",
            text
        )
        if not match:
            return ''

        name_str = match.group().strip()
        try:
            parts = name_str.split(", ")
            if len(parts) >= 2:
                return ' '.join(word.capitalize() for word in parts[1].split() if word != 'de' and word != 'la' and word != 'del')
        except:
            pass

        return name_str

    def _extract_last_name(self, text: str) -> str:
        """Extract last name."""
        match = re.search(
            r"(?<=Name:)\s?.* .*, \w+|(?<=Nombre:)\s?.* .*, .*?(?=OD|OS)|([A-Za-záéíóúüñ ]+),\s+([A-Za-záéíóúüñ ]+)(?=\s+Paciente)",
            text
        )
        if not match:
            return ''

        name_str = match.group().strip()
        try:
            parts = name_str.split(", ")
            last_name = parts[0].strip().capitalize()
            return ' '.join(word.capitalize() for word in last_name.split())
        except:
            pass

        return ''

    def _extract_birthdate(self, text: str) -> datetime.date:
        """Extract date of birth."""
        match = re.search(
            r"(?<=DOB:)\s?..-...-..|(?<=Fecha de nacimiento:)\s?[0-9]{1,2}/[0-9]{2}/[0-9]{4}|(?<=DOB)\s?[0-9]{1,2}/[0-9]{2}/[0-9]{4}",
            text
        )
        if not match:
            return None

        date_str = match.group().strip()
        try:
            return datetime.datetime.strptime(date_str, '%d-%b-%y').date()
        except ValueError:
            try:
                return datetime.datetime.strptime(date_str, '%d/%m/%Y').date()
            except ValueError:
                logger.warning(f"Could not parse birthdate: {date_str}")
                return None

    def _extract_exam_date(self, text: str) -> datetime.date:
        """Extract exam date."""
        match = re.search(
            r"(?<=Exam Date:)\s?..-...-..|(?<=Fecha de examen:)\s?[0-9]{1,2}/[0-9]{2}/[0-9]{4}",
            text
        )
        if not match:
            return None

        date_str = match.group().strip()
        try:
            return datetime.datetime.strptime(date_str, '%d-%b-%y').date()
        except ValueError:
            try:
                return datetime.datetime.strptime(date_str, '%d/%m/%Y').date()
            except ValueError:
                logger.warning(f"Could not parse exam date: {date_str}")
                return None

    def _extract_gender(self, text: str) -> str:
        """Extract gender."""
        match = re.search(r"(?<=Gender:)\s?\w+|(?<=Sexo:)\s?\w+|(?<=Género)\s?\w+", text)
        if match:
            return match.group().strip().capitalize()
        return ''

    def _empty_result(self) -> Dict[str, Any]:
        """Return empty extraction result."""
        return {
            'id': '',
            'name': '',
            'last_name': '',
            'birthdate': None,
            'exam_date': None,
            'gender': '',
        }


class TextExtractor:
    """
    Main text extractor - delegates to specific strategies.
    Can be easily extended with new strategies (OCR, ML, etc.)
    """

    def __init__(self, strategy: ExtractorStrategy = None):
        """
        Initialize with extraction strategy.
        Defaults to regex-based extraction.
        """
        self.strategy = strategy or RegexTextExtractor()

    def extract(self, uploaded_file: UploadedFile) -> Dict[str, Any]:
        """
        Extract text from uploaded file.
        
        Args:
            uploaded_file: Django UploadedFile object
            
        Returns:
            Dict with extracted data
        """
        try:
            file_content = uploaded_file.read()
            uploaded_file.seek(0)  # Reset file pointer for potential re-reads
            return self.strategy.extract(file_content)
        except Exception as e:
            logger.error(f"Text extraction failed: {str(e)}", exc_info=True)
            return self._empty_result()

    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result on failure."""
        return {
            'id': '',
            'name': '',
            'last_name': '',
            'birthdate': None,
            'exam_date': None,
            'gender': '',
        }
