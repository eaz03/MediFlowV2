from django import forms
from .models import Patient
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