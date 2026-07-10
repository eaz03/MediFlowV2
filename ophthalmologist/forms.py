from django import forms
from .models import Patient
from .models import Ophthalmologist
from exam.models import Exam
from administrator.models import CustomUser
from django.contrib.auth.forms import AuthenticationForm

class LoginForm(forms.Form):
    email = forms.CharField(max_length=255, widget=forms.TextInput(attrs={
        'class': 'form-control',
       'placeholder': 'Enter your email address',
        'id': 'username',
        'name': 'username'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter your password',
        'id': 'password',
        'name': 'password'
    }))

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        password = cleaned_data.get("password")

        if not CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("User does not exist")

        user = CustomUser.objects.filter(email=email).first()
        if not user.check_password(password):
            raise forms.ValidationError("Incorrect password")

class UploadFileForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ['file']

    def __init__(self, *args, **kwargs):
        super(UploadFileForm, self).__init__(*args, **kwargs)
        self.fields['file'].widget.attrs.update({'accept': 'application/pdf'})  # Accept only PDFs

class UploadExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ['file', 'exam_date', 'apparatus', 'exam_type', 'patient']
        widgets = {
            'exam_date': forms.DateInput(attrs={'type': 'date'})
        }

    def __init__(self, *args, **kwargs):
        super(UploadExamForm, self).__init__(*args, **kwargs)
        self.fields['file'].widget.attrs.update({'accept': 'application/pdf', 
            'multiple': True })  # Accept only PDFs

class AddPatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = ['identification', 'name', 'last_name', 'email', 'phone', 'date_of_birth', 'gender', 'address', 'health_insurance', 'doctor']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }
    def __init__(self, *args, **kwargs):
        super(AddPatientForm, self).__init__(*args, **kwargs)
        self.fields['doctor'].required = False
        self.fields['health_insurance'].required = False


class RegisterDoctorForm(forms.Form):
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    email = forms.EmailField(max_length=255)
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)
    medical_license = forms.CharField(max_length=50)
    specialty = forms.CharField(max_length=50)

    def clean_email(self):
        email = self.cleaned_data['email']
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean_medical_license(self):
        medical_license = self.cleaned_data['medical_license']
        if Ophthalmologist.objects.filter(medical_license=medical_license).exists():
            raise forms.ValidationError('This medical license is already registered.')
        return medical_license

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError('Passwords do not match.')
        return cleaned_data

    def save(self):
        ophthalmologist = Ophthalmologist.objects.create(
            name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            email=self.cleaned_data['email'],
            medical_license=self.cleaned_data['medical_license'],
            specialty=self.cleaned_data['specialty'],
        )
        user = CustomUser.objects.create_user(
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            ophthalmologist=ophthalmologist,
        )
        return user