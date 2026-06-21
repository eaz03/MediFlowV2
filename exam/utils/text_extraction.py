import os
import pandas as pd
import pdfplumber
import io
import re
import datetime
import PyPDF2
from exam.models import Patient


def text_extraction(file_content):
    with pdfplumber.open(io.BytesIO(file_content)) as pdf:
        first_page = pdf.pages[0]
        text = first_page.extract_text()

        id = re.search("(?:(?<=ID:)|(?<=ID de paciente))\\s?[0-9]+", text)
        name = re.search("(?<=Name:)\\s?.* .*, \\w+|(?<=Nombre:)\\s?.* .*, .*?(?=OD|OS)|([A-Za-záéíóúüñ ]+),\\s+([A-Za-záéíóúüñ ]+)(?=\\s+Paciente)", text)
        birthdate = re.search("(?<=DOB:)\\s?..-...-..|(?<=Fecha de nacimiento:)\\s?[0-9]{1,2}/[0-9]{2}/[0-9]{4}|(?<=DOB)\\s?[0-9]{1,2}/[0-9]{2}/[0-9]{4}", text)
        exam_date = re.search("(?<=Exam Date:)\\s?..-...-..|(?<=Fecha de examen:)\\s?[0-9]{1,2}/[0-9]{2}/[0-9]{4}", text)
        gender = re.search("(?<=Gender:)\\s?\\w+|(?<=Sexo:)\\s?\\w+|(?<=Género)\\s?\\w+", text)
        name = name.group().strip() if name else '' 
        id = id.group().strip() if id else ''
        birthdate = birthdate.group().strip() if birthdate else ''
        exam_date = exam_date.group().strip() if exam_date else ''
        gender = gender.group().strip().capitalize() if gender else ''

        try:
            birthdate = datetime.datetime.strptime(birthdate, '%d-%b-%y').date() if birthdate else ''
            exam_date = datetime.datetime.strptime(exam_date, '%d-%b-%y').date() if exam_date else ''
        except: 
            try:
                birthdate = datetime.datetime.strptime(birthdate, '%d/%m/%Y').date() if birthdate else ''
                exam_date = datetime.datetime.strptime(exam_date, '%d/%m/%Y').date() if exam_date else ''
            except:
                birthdate = ''
                exam_date = ''

        try:
            last_name = name.split(", ")[0].strip().capitalize() if name else ''
            last_name = ' '.join(word.capitalize() for word in last_name.split())

            name = name.split(", ")[1].strip().capitalize() if name else ''
            name = ' '.join(word.capitalize() for word in name.split() if word != 'de' or word != 'la' or word != 'del')
        except:
            last_name = ''
            name = name

        return {
            "id": id,
            "name": name,
            "last_name": last_name,
            "birthdate": birthdate,
            "exam_date": exam_date,
            "gender": gender
        }
        
def extract_multiple(files):
    extracted_data = {"id":set(), "name":set(), "last_name":set(), "birthdate":set(), "exam_date":set(), "gender":set()}
    for file in files:
        if file.name.lower().endswith('.pdf'):
            file_data = text_extraction(file.read())
            #print(file_data)

            extracted_data["id"].add(file_data["id"]) if file_data["id"] != '' else None
            extracted_data["name"].add(file_data["name"]) if file_data["name"] != '' else None
            extracted_data["last_name"].add(file_data["last_name"]) if file_data["last_name"] != '' else None
            extracted_data["birthdate"].add(file_data["birthdate"]) if file_data["birthdate"] != '' else None
            extracted_data["exam_date"].add(file_data["exam_date"]) if file_data["exam_date"] != '' else None
            extracted_data["gender"].add(file_data["gender"]) if file_data["gender"] != '' else None
        
    #print(extracted_data)
    for key, value in extracted_data.items():
        if len(value) > 1:
            print(f"Error: {key} has more than one value")
            for val in value:
                print(val)
    
    first_elements = {key: next(iter(value)) for key, value in extracted_data.items() if value}
    #print(first_elements)
    return first_elements 
    #iterate through extracted data and where there is more than one value, compute levenshtein distance if very different, then add to list of errors

def concatenate_pdf(files, output_path):
    merger = PyPDF2.PdfMerger()

    # Iterate through the PDF files
    for file in files:
        if file.name.lower().endswith('.pdf'):
            merger.append(file)

    # Save the output concatenated PDF
    with open(output_path, "wb") as output_pdf:
        merger.write(output_pdf)

def extract_folders(folders_path):
    folders = [os.path.join(folders_path, folder) for folder in os.listdir(folders_path)]
    print("folders",folders)
    for folder in folders:
        patient_exam_info = extract_multiple([os.path.join(folder, file) for file in os.listdir(folder)])
        print(folder,patient_exam_info)
        name_good = folder.split("/")[-1].capitalize() == (patient_exam_info["name"] + " " + patient_exam_info["last_name"])
        print(folder,patient_exam_info, name_good)
        #save_patient(patient_exam_info)
        if name_good:
            print(f"Patient {patient_exam_info['name']} {patient_exam_info['last_name']} has been saved")
        else:
            print(f"Patient {patient_exam_info['name']} {patient_exam_info['last_name']} has not been saved")

def add_excel_info(file_content):
    df = pd.read_excel(io.BytesIO(file_content.read()))
    df.columns = df.columns.str.strip()
    for index, row in df.iterrows():

        identification=row['Identificación'].split('-')[1].strip()
        health_insurance=row['Entidad'].strip()
        
        existing_patient = Patient.objects.filter(identification=identification).exists()

        if not existing_patient:
            name=row['Nombre del paciente']
            print(name)
            print(name.strip("()").split(" "))
            last_name=""
            age=row['Edad']
            patient = Patient(name=name, last_name=last_name, identification=identification, age=age, health_insurance=health_insurance)
            patient.save()
        else:
            patient = Patient.objects.filter(identification=identification).first()
            patient.health_insurance = health_insurance
            patient.save()
