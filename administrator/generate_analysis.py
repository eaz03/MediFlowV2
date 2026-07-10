from fpdf import FPDF
import pypdfium2 as pdfium
from ophthalmologist.models import Ophthalmologist, Patient
from exam.models import Exam
def generate_analysis_pdf(exam, output_file, doctor=Ophthalmologist(name="John", last_name="Doe", email="johndoe@example.com", medical_license="1234567890", title="Ophthalmologist", address="123 Main St"), patient = Patient(name='Pepito', last_name='Perez', email='eldestrozador@example.com', phone='1234567890', age=30, date_of_birth='1990-01-01', gender='M', address='123 Main St', health_insurance='ABC Insurance'), logo="media/logo_clinica.png"):
    class PDF(FPDF):
        def header(self):
            self.image(logo, 10, 8, 33)
            self.set_font('helvetica', 'B', 12)

    #PDF Creation and Document Data
    pdf_data = {
        "orientation": "P",
        "unit": "mm",
        "format": "letter",
        "font": "helvetica",
        "style": "B",
        "header_size": 10,
        "text_size": 12,
        "subtitle_size": 14,
        "margin": 15,
        "title_size": 15
    }

    pdf = PDF(orientation=pdf_data["orientation"], unit=pdf_data["unit"], format=pdf_data["format"]
    )

    pdf.set_auto_page_break(auto=True, margin=pdf_data["margin"])
    pdf.set_line_width(0.1)

    """ PATIENT INFORMATION """

    pdf.set_font(family=pdf_data["font"], style=pdf_data["style"], size=pdf_data["header_size"])
    pdf.set_margin(pdf_data["margin"])

    # Examination Device
    pdf.add_page()
    pdf.cell(150)
    #pdf.cell(0,20, txt=f"{exam.apparatus}", align="R")
    pdf.ln(20)

    # Style line
    pdf.line(x1=pdf_data["margin"], y1=30, x2=(pdf.w - pdf_data["margin"]), y2=30)

    # Patient name and health provider
    pdf.cell(30)
    pdf.cell(0, 0, f"PACIENTE: {patient.name}", 0, 0, "L")
    pdf.cell(60)
    pdf.cell(0, 0, f"{patient.health_insurance}", 0, 0, "R")
    pdf.ln(5)

    # Patient ID, age and date
    pdf.cell(30)
    pdf.cell(0, 0, f"FECHA: {exam.date}", 0, 0, "L")
    pdf.cell(20)
    pdf.cell(0, 0, f"EDAD: {patient.age} años", 0, 0, "L")
    pdf.cell(20)
    pdf.cell(0, 0, f"{patient.id}", 0, 0, "R")
    pdf.ln(20)

    # Style line
    pdf.line(x1=pdf_data["margin"], y1=50, x2=(pdf.w - pdf_data["margin"]), y2=50)

    pdf.set_font(pdf_data["font"], pdf_data["style"], pdf_data["title_size"])

    """ EXAMINATION INFORMATION """

    #pdf.cell(w=0, text=f"{exam.exam_type}",  align="C")
    pdf.ln(15)

    pdf.set_font(style=pdf_data["style"],size=pdf_data["subtitle_size"])

    pdf.cell(0, 0, "CONCLUSIONES", 0, 0, "L")
    pdf.ln(10)

    # Examination results
    pdf.set_font(size=pdf_data["text_size"])
    pdf.multi_cell(0, pdf_data["text_size"]/2, exam.result_analysis, 0, "L")
    pdf.ln(10)

    # Doctor information
    pdf.set_font(pdf_data["font"], pdf_data["style"], pdf_data["subtitle_size"])
    pdf.cell(0, 0, doctor.name, 0, 0, "L")
    pdf.ln(5)
    pdf.cell(0, 0, doctor.medical_license, 0, 0, "L")
    pdf.ln(5)
    pdf.cell(0, 0, doctor.title, 0, 0, "L")

    pdf.output(output_file)
    return {"status": "success", "message": "PDF created successfully"}

    # Images of the examination
"""     exams = exam.exam_files
    for exam_idx in range(len(exams)):
        print(f"Adding exam {exams[exam_idx]}")
        image_pdf = pdfium.PdfDocument(exams[exam_idx])
        for i in range(0, len(image_pdf)):
            page = image_pdf[i]
            image = page.render(scale=4).to_pil()

            pdf.add_page()
            pdf.image(image, x = 0, y = 30, w=200) 
    """