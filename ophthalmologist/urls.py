from django.urls import path
from ophthalmologist import views as ophthalmologistViews

urlpatterns = [
    path('', ophthalmologistViews.menu, name='menu'),
    path('patient-panel', ophthalmologistViews.view_patients, name="view_patients"),
    path('new-patient/', ophthalmologistViews.new_patient, name="new_patient"),
    path('edit/<int:pk>/', ophthalmologistViews.view_pdf, name="view_pdf"),
    path('next_exam/', ophthalmologistViews.next_exam, name="next_exam"),
    path('patient-extraction/', ophthalmologistViews.automated_patient_extraction, name="patient_extraction"),
    path('login/', ophthalmologistViews.login_view, name='login'),
    path('logout/', ophthalmologistViews.logout_view, name='logout'),
    path('search/', ophthalmologistViews.search, name="search"),
    path('about/', ophthalmologistViews.about, name="about"),
    path('tutorial/', ophthalmologistViews.tutorial, name="tutorial"),
    path('delete_patient/<int:patient_id>/', ophthalmologistViews.delete_patient, name='ophthalmologist_delete_patient'),
]
