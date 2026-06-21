# MediFlow V2 - Django Style Guide

## General Principles

- **Type Annotations**: All functions, methods, and class attributes must include type hints for parameters and return values.
- **One Class Per File**: Each file should contain exactly one class definition, with the filename matching the class name.
  - Example: `Patient` model → `patient.py`, `ExamForm` → `exam_form.py`
- **No Debug Code**: Never commit code containing `print()` for debugging, `pdb` breakpoints, or `import pdb` statements.

---

## Views (Django View Functions/Classes)

### Responsibility
- Receive information from HTTP requests
- Delegate business logic to services/utils
- Redirect to other views or render templates
- Return a single dictionary of view data

### Structure

```python
# views.py - Example
from typing import Dict, Any
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse

from .services import exam_service  # Logic in separate service
from .models import Exam

@login_required
def analyze_exam(request: HttpRequest, exam_id: int) -> HttpResponse:
    """View to display exam analysis form."""
    try:
        exam: Exam = Exam.objects.get(id=exam_id)
        view_data: Dict[str, Any] = exam_service.prepare_analysis_view(exam)
        return render(request, 'exam/analyze.html', {'view_data': view_data})
    except Exam.DoesNotExist:
        return render(request, 'error.html', {'error_message': 'exam_not_found'})
```

### Rules

1. **Single Data Structure**: Pass all data to templates in a single dictionary named `view_data`.
   ```python
   view_data = {
       'exam': exam,
       'form': form,
       'patients': patients,
       'devices': devices
   }
   return render(request, 'template.html', {'view_data': view_data})
   ```

2. **Delegate Logic**: Move business logic to `services/` or `utils/` modules. Views should be thin.
   ```python
   # GOOD
   from .services import exam_service
   result = exam_service.validate_and_save_analysis(exam, analysis_data)
   
   # AVOID
   # Putting SQL queries, validations, PDF generation directly in view
   ```

3. **No Controller-to-Controller Imports**: Do not import view functions in other view functions.
   ```python
   # AVOID
   from .views import another_view
   ```

4. **Session Storage**: Only store primitive types (strings, integers, booleans, lists of primitives) in session. Never store Django model instances.
   ```python
   # GOOD
   request.session['patient_id'] = patient.id
   request.session['exam_ids'] = [1, 2, 3]
   
   # AVOID
   request.session['patient'] = patient  # Don't serialize objects
   ```

5. **Eager Loading**: Use `select_related()` and `prefetch_related()` to minimize database queries.
   ```python
   # GOOD
   exams = Exam.objects.select_related('patient').filter(is_analyzed=False)
   
   # AVOID
   exams = Exam.objects.all()  # N+1 queries when accessing exam.patient
   ```

6. **Minimal Query Results**: Fetch only the data you need.
   ```python
   # GOOD
   exam = Exam.objects.get(id=exam_id)
   
   # AVOID
   all_exams = Exam.objects.all()  # Then filter manually
   ```

7. **Clear View Naming**: View names must clearly indicate their purpose. No ambiguous names.
   ```python
   # GOOD
   def analyze_exam(request, exam_id):
   def list_pending_exams(request):
   def download_analysis_pdf(request, exam_id):
   
   # AVOID
   def exam(request, exam_id):  # Unclear: list, create, edit, or delete?
   def handle(request):
   ```

---

## Models

### File Structure
- One model per file, filename matches class name.
- Example: `Patient` model → `patient.py`

### Model Documentation

Each model file must include a comment block documenting all attributes:

```python
# patient.py
from django.db import models
from typing import Optional

class Patient(models.Model):
    """
    PATIENT ATTRIBUTES
    - id: int - Primary key (auto-generated)
    - name: str - Patient's first name (max 50 chars)
    - last_name: str - Patient's last name (max 50 chars)
    - identification: str - Unique patient ID (max 50 chars)
    - email: str - Patient's email address (optional)
    - phone: str - Patient's phone number (max 10 chars, optional)
    - age: int - Patient's age (optional)
    - date_of_birth: date - Patient's date of birth (optional)
    - gender: str - Patient's gender (max 50 chars)
    - address: str - Patient's address (max 100 chars, optional)
    - health_insurance: str - Patient's health insurance (max 50 chars)
    - doctor: ForeignKey - Reference to assigned Ophthalmologist
    - created_at: datetime - Timestamp of record creation (auto)
    - updated_at: datetime - Timestamp of last update (auto)
    """
    
    name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    identification = models.CharField(max_length=50, unique=True)
    # ... rest of fields
```

### Fillable/Editable Fields

After the documentation comment, explicitly define fillable fields in a single line:

```python
class Patient(models.Model):
    """
    PATIENT ATTRIBUTES
    ...
    """
    
    FILLABLE = ['name', 'last_name', 'email', 'phone', 'age', 'date_of_birth', 'gender', 'address', 'health_insurance', 'doctor']
    
    name = models.CharField(max_length=50)
    # ...
```

### Validations

All validations for model creation must be in a static method (or class method):

```python
class Patient(models.Model):
    # ... fields ...
    
    @staticmethod
    def validate_create(data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate patient creation data.
        
        Args:
            data: Dictionary containing patient fields
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not data.get('name'):
            return False, 'name_required'
        if not data.get('identification'):
            return False, 'identification_required'
        if Patient.objects.filter(identification=data['identification']).exists():
            return False, 'identification_already_exists'
        return True, None
```

### Getters and Setters

All attributes (except `id` and timestamps) must have getters and setters:

```python
class Patient(models.Model):
    # ... fields ...
    
    def get_name(self) -> str:
        """Get patient's first name."""
        return self.name
    
    def set_name(self, value: str) -> None:
        """Set patient's first name."""
        if not value or len(value) == 0:
            raise ValueError('Name cannot be empty')
        self.name = value
    
    def get_full_name(self) -> str:
        """Get patient's full name."""
        return f"{self.name} {self.last_name}"
    
    # Do NOT include setter for id
```

### Relations

For one-to-many relationships, use foreign keys with constraints:

```python
class Exam(models.Model):
    """
    EXAM ATTRIBUTES
    - id: int - Primary key
    - patient: ForeignKey - Reference to Patient (one-to-many)
    - exam_date: date - Date of exam
    - is_analyzed: bool - Whether exam has been analyzed
    """
    
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='exams'  # For reverse access: patient.exams.all()
    )
    exam_date = models.DateField(null=True, blank=True)
    is_analyzed = models.BooleanField(default=False)
    
    def get_patient(self) -> Patient:
        """Get associated patient."""
        return self.patient
    
    def set_patient(self, patient: Patient) -> None:
        """Set associated patient."""
        if not isinstance(patient, Patient):
            raise ValueError('Must be a Patient instance')
        self.patient = patient
```

### Type Annotations

Use type hints in all model methods:

```python
class Exam(models.Model):
    def get_id(self) -> int:
        return self.id
    
    def get_analysis(self) -> str:
        return self.result_analysis
    
    def set_analysis(self, analysis: str) -> None:
        self.result_analysis = analysis
    
    @classmethod
    def get_pending_exams(cls) -> models.QuerySet[Exam]:
        """Get all exams that haven't been analyzed."""
        return cls.objects.filter(is_analyzed=False)
```

---

## Forms

### File Structure
- One form per file, filename matches class name.
- Example: `ExamAnalysisForm` → `exam_analysis_form.py`

### Form Rules

```python
# exam_analysis_form.py
from django import forms
from typing import Dict, Any
from .models import Exam

class ExamAnalysisForm(forms.ModelForm):
    """Form for analyzing exams."""
    
    result_analysis = forms.CharField(
        widget=forms.Textarea,
        label='exam_analysis_label',  # Use lang key, not hardcoded text
        required=False
    )
    
    class Meta:
        model = Exam
        fields = ['exam_type', 'apparatus', 'result_analysis']
    
    def clean(self) -> Dict[str, Any]:
        """Custom validation logic."""
        cleaned_data = super().clean()
        
        if not cleaned_data.get('exam_type'):
            self.add_error('exam_type', 'exam_type_required')
        
        return cleaned_data
```

### Rules

1. **Always use `@csrf_token`** in templates with forms.
2. **Use lang keys** for labels, help text, and error messages. Never hardcode text.
3. **Separate form files** - don't put multiple forms in one file.

---

## Templates

### File Structure
- One template per view function, organized by app.
- Example: `exam/analyze.html`, `patient/list.html`

### Template Rules

```html
<!-- exam/analyze.html -->
{% extends "base.html" %}

{% block title %}
    {% trans "exam_analysis_title" %}
{% endblock %}

{% block content %}
    <div class="container">
        <h1>{% trans "exam_analysis_heading" %}</h1>
        
        <form method="POST" action="{% url 'analyze_exam' view_data.exam.id %}">
            {% csrf_token %}
            
            <div class="form-group">
                <label for="analysis">{% trans "analysis_label" %}</label>
                <textarea id="analysis" name="result_analysis">{{ view_data.exam.result_analysis }}</textarea>
            </div>
            
            <button type="submit">{% trans "save_button" %}</button>
        </form>
    </div>
{% endblock %}
```

### Rules

1. **All templates extend base layout**: `{% extends "base.html" %}`
2. **No raw PHP/Python in templates**: Use Blade syntax and template tags only.
3. **All text uses lang/translation**: `{% trans "key_name" %}` for all user-facing text.
   - Exception: Only use variables for dynamic data from view_data.
4. **Always include `{% csrf_token %}`** in POST forms.
5. **Use getters for data**: Access data through view_data dictionary.
   ```html
   <!-- GOOD -->
   {{ view_data.exam.get_analysis }}
   
   <!-- AVOID -->
   {{ view_data.exam.result_analysis }}
   ```

---

## URLs/Routing

### File Structure
- One `urls.py` per app, included in main `mediflow/urls.py`
- Example: `exam/urls.py`, `ophthalmologist/urls.py`

### Routing Rules

```python
# exam/urls.py
from django.urls import path
from typing import List, Tuple
from . import views

# Path constants
EXAM_NEW = 'exam/'
EXAM_ANALYZE = 'exam/analyze/'
EXAM_DOWNLOAD = 'exam/download/'

urlpatterns: List[Tuple] = [
    path('new', views.new_exam, name='exam_new'),
    path('analyze/<int:exam_id>/', views.analyze_exam, name='exam_analyze'),
    path('download/<int:exam_id>/', views.download_analysis_pdf, name='exam_download'),
]
```

### Rules

1. **All routes must reference a view function**, not inline code.
2. **Single responsibility per route**: No two routes with identical paths but different HTTP methods.
3. **Define path constants** at the top of `urls.py` file.
4. **Route names should match controller names**: `exam_new`, `exam_analyze`, not just `new`, `analyze`.
5. **Use descriptive names**: Route names must clearly indicate action and resource.
   ```python
   # GOOD
   path('analyze/<int:exam_id>/', views.analyze_exam, name='exam_analyze')
   path('download/<int:exam_id>/', views.download_analysis_pdf, name='exam_download')
   
   # AVOID
   path('detail/<int:exam_id>/', views.exam, name='exam')  # Unclear what action
   ```

---

## Services/Utils

### File Structure
- Organize business logic in `services/` or `utils/` modules.
- One primary service/class per file.
- Example: `exam/services/exam_service.py`

### Rules

```python
# exam/services/exam_service.py
from typing import Dict, Any, Optional, List
from exam.models import Exam
from exam.utils.text_extraction import extract_text_from_pdf

class ExamService:
    """Service for exam-related business logic."""
    
    @staticmethod
    def prepare_analysis_view(exam: Exam) -> Dict[str, Any]:
        """
        Prepare data for exam analysis view.
        
        Args:
            exam: Exam instance to analyze
            
        Returns:
            Dictionary containing all data for view template
        """
        return {
            'exam': exam,
            'form': ExamAnalysisForm(instance=exam),
            'devices': ['OCT', 'Fundus Camera'],
            'exam_types': get_exam_presets()
        }
    
    @staticmethod
    def save_analysis(exam: Exam, analysis_data: Dict[str, str]) -> tuple[bool, Optional[str]]:
        """
        Save exam analysis.
        
        Args:
            exam: Exam to save
            analysis_data: Dictionary with analysis fields
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            exam.set_analysis(analysis_data.get('result_analysis', ''))
            exam.set_analysis_date(datetime.now().date())
            exam.set_is_analyzed(True)
            exam.save()
            return True, None
        except Exception as e:
            return False, str(e)
```

### Rules

1. **Type hints required** for all parameters and return values.
2. **Stateless services**: Services should not maintain state; use static methods where possible.
3. **Single responsibility**: Each service handles one domain (exams, patients, PDFs, etc.).
4. **No direct view access**: Services should not import or call views.
5. **Return tuples for errors**: Use `(success: bool, error_message: Optional[str])` for operations that can fail.

---

## Logging and Error Handling

### Error Tracking

Create an `ErrorLog` model to track failures:

```python
# error_log.py
from django.db import models
from typing import Optional

class ErrorLog(models.Model):
    """
    ERROR LOG ATTRIBUTES
    - id: int - Primary key
    - operation: str - Name of failed operation (e.g., 'bulk_insert_exam')
    - error_message: str - Error description
    - error_code: str - Categorized error code
    - created_at: datetime - When error occurred
    """
    
    OPERATION_CHOICES = [
        ('bulk_insert', 'Bulk Insert'),
        ('pdf_generation', 'PDF Generation'),
        ('text_extraction', 'Text Extraction'),
    ]
    
    operation = models.CharField(max_length=50, choices=OPERATION_CHOICES)
    error_message = models.TextField()
    error_code = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def get_error_message(self) -> str:
        return self.error_message
```

### Logging Utility

```python
# utils/logger.py
from typing import Optional
from .error_log import ErrorLog

class Logger:
    """Centralized logging for all operations."""
    
    @staticmethod
    def log_error(operation: str, error_message: str, error_code: str) -> None:
        """Log an error to database."""
        ErrorLog.objects.create(
            operation=operation,
            error_message=error_message,
            error_code=error_code
        )
    
    @staticmethod
    def get_errors_for_operation(operation: str, limit: Optional[int] = 100) -> List[ErrorLog]:
        """Retrieve logged errors for an operation."""
        return ErrorLog.objects.filter(operation=operation).order_by('-created_at')[:limit]
```

---

## Summary Checklist

- [ ] All functions have type annotations
- [ ] One class per file, filename matches class name
- [ ] No `print()` or debug code in commits
- [ ] Views delegate logic to services/utils
- [ ] All view data passed in single `view_data` dictionary
- [ ] Session stores only primitives, not objects
- [ ] Models have attribute documentation comments
- [ ] All attributes access via getters/setters
- [ ] Eager loading used (`select_related`, `prefetch_related`)
- [ ] Minimal queries (only fetch needed data)
- [ ] Form labels and help text use lang keys, not hardcoded
- [ ] Templates use `{% trans %}` for all user-facing text
- [ ] All POST forms include `{% csrf_token %}`
- [ ] Routes clearly named and mapped to views
- [ ] Business logic in services, not views
- [ ] Error handling with logging to database
