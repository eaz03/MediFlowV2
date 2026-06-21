# FR-1: Upload Exams (PDF/Image) in 3-Step Process

## Requirement
Upload medical exams in PDF or image format to be read by the doctor in the time and effort expected of a traditional file upload (three steps).

---

## Current Implementation

### Files Involved
- **View**: `exam/views.py` - `new_exam()` function (lines 26-202)
- **Template Step 1**: `exam/templates/new_exam.html` - Upload form
- **Template Step 2**: `exam/templates/exam_form_valid.html` - Confirmation/edit form
- **Model**: `exam/models.py` - `Exam` class
- **Forms**: `exam/forms.py` - `UploadExamForm`, `UploadFileForm`
- **Utilities**: `exam/utils/text_extraction.py` - PDF text extraction

### Three-Step Flow
1. **Step 1 (Upload)**: User uploads file → `new_exam()` with 'new_exam' button
   - File read into memory
   - Text extraction via regex on first PDF page
   - Extracted data: id, name, last_name, birthdate, exam_date, gender
   - Temporary patient/exam created in DB then deleted
   - Session stores extracted data

2. **Step 2 (Edit)**: Shows `exam_form_valid.html` form
   - Pre-fills with extracted data
   - User can edit all fields
   - Doctor selection dropdown
   - Form submission triggers Step 3

3. **Step 3 (Validate & Save)**: `new_exam()` with 'validate_exam' button
   - Retrieves session data
   - Creates final patient record (if new) or uses existing
   - Creates final exam record
   - Redirects to menu

---

## Issues Found

### 🔴 **CRITICAL ISSUES**

#### 1. **Unnecessary Save-Delete Cycle (Lines 96-106)**
```python
exam.save()      # Line 96 - Save to DB
patient.save()   # Line 89 - Save to DB
# ... 
exam.delete()    # Line 106 - Delete immediately
patient.delete() # Line 105 - Delete immediately
```
**Problem**: Creates DB records just to discard them
- Wastes database I/O
- File uploaded to `media/uploads/` but orphaned on delete
- Disk bloat from orphaned files
**Impact**: Performance degradation, storage waste

#### 2. **Session-Based State (Lines 109-121, 161-165)**
```python
request.session['patient_data'] = patient_data
request.session['exam_data'] = exam_data
```
**Problem**: Multi-step process relies on volatile session
- Session expires after inactivity (default 2 weeks)
- Browser close loses data
- No persistence if user navigates away
- Cannot recover partial uploads
**Impact**: Data loss, poor UX on browser crashes

#### 3. **File Reference Lost in Step 3 (Line 191)**
```python
file = old_exam["file"]  # Stored as string filename
exam = Exam(..., file=file, ...)  # Expects UploadedFile
```
**Problem**: File stored as string, not as proper UploadedFile object
- Step 2 form passes filename as string
- Step 3 tries to assign string to FileField
- May cause file reference corruption
**Impact**: File may not save correctly

#### 4. **Fragile Text Extraction (Line 40)**
```python
extracted_data = text_extraction(file_content)
```
**Problem**: PDF regex patterns are hardcoded and layout-specific
- Different PDF formats fail silently
- Returns empty dicts: `{'id': '', 'name': '', ...}`
- Empty extracted data cascades through form
- No error feedback to user
**Impact**: Garbage data saved, confusing user experience

#### 5. **Debug Print Statements (Lines 40, 121-123, 149)**
```python
print(extracted_data)
print("Patient data: ", patient_data)
print(request.session['patient_data'])
print("Patient exists")
print(exam.file.url)
```
**Problem**: Debug code left in production
- Violates STYLE_GUIDE.md
- Clutters console output
- Should be replaced with logging
**Impact**: Code quality, maintainability

#### 6. **No Transaction Wrapping**
**Problem**: Multi-step DB operations unprotected
- Step 1: Save patient/exam, then delete
- Step 3: Create new patient/exam
- If Step 3 fails partway, DB left in inconsistent state
- No rollback mechanism
**Impact**: Data integrity issues

---

## Issues by Severity

| Severity | Issue | Line(s) | Impact |
|----------|-------|---------|--------|
| 🔴 Critical | Save-delete cycle | 96-106 | Disk waste, orphaned files |
| 🔴 Critical | Session fragility | 109-121, 161 | Data loss on timeout |
| 🔴 Critical | No transaction | 26-202 | DB inconsistency |
| 🟠 Major | Fragile extraction | 40 | Garbage data saved |
| 🟠 Major | File reference issue | 191 | File not saved correctly |
| 🟡 Minor | Debug prints | 40, 121-123, 149 | Code quality |
| 🟡 Minor | Missing file validation | N/A | No size/format checks |

---

## Required Fixes (Priority Order)

### Phase 1: Immediate (Fix Logic)
1. **Remove save-delete cycle** 
   - Add `is_validated=False` field to Exam model
   - Store temp exam with this flag instead of deleting

2. **Replace session with DB storage**
   - Temp exam record persists across steps
   - Session only stores exam ID, not data

3. **Fix file handling**
   - Pass file reference correctly through steps
   - Use proper UploadedFile objects

### Phase 2: Robustness (Error Handling)
4. **Add transaction wrapping**
   - Wrap Steps 1-3 in `@transaction.atomic()`
   - Rollback on any failure

5. **Add error logging**
   - Replace `print()` with logging module
   - Log extraction failures with details

6. **Add file validation**
   - Check file format (PDF/image only)
   - Check file size (max 50MB)
   - Check for duplicates

### Phase 3: Polish (UX/DX)
7. **Improve error messages**
   - Show extraction confidence
   - Explain which fields couldn't be extracted
   - Offer manual retry option

---

## Implementation Plan

**To be completed in order:**
- [ ] Add `is_validated` field to Exam model
- [ ] Refactor `new_exam()` to use temp exam records
- [ ] Remove session-based storage
- [ ] Add file validation utility
- [ ] Replace print() with proper logging
- [ ] Add transaction wrapping with error recovery
- [ ] Test: upload → edit → save flow
- [ ] Test: re-upload after validation failure
- [ ] Test: extraction error handling

---

## Related Requirements
- FR-2: Exam analysis (depends on exam being saved correctly)
- FR-3: PDF generation (depends on exam file reference)
- FR-10: Add patients (interacts with patient creation in Step 3)
- FR-16: Error logging (needs proper error tracking)

