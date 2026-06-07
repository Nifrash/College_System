import os
from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def generate_payment_invoice(payment):
    buffer = BytesIO()

    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    student = payment.student
    user = student.user
    course = payment.course

    p.setFont("Helvetica-Bold", 18)
    p.drawString(50, height - 60, "Europe Campus Management")
    p.setFont("Helvetica", 11)
    p.drawString(50, height - 80, "Payment Invoice")

    p.line(50, height - 95, width - 50, height - 95)

    y = height - 130

    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "Invoice Details")
    y -= 25

    p.setFont("Helvetica", 10)
    p.drawString(50, y, f"Invoice No: {payment.reference_no}")
    y -= 20
    p.drawString(50, y, f"Payment Date: {payment.payment_date}")
    y -= 20
    p.drawString(50, y, f"Payment Method: {payment.payment_method}")
    y -= 20
    p.drawString(50, y, f"Status: {payment.status}")

    y -= 40

    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "Student Details")
    y -= 25

    p.setFont("Helvetica", 10)
    p.drawString(50, y, f"Student ID: {student.student_id}")
    y -= 20
    p.drawString(50, y, f"Student Name: {user.get_full_name() or user.username}")
    y -= 20
    p.drawString(50, y, f"Email: {user.email or '-'}")
    y -= 20
    p.drawString(50, y, f"Phone: {user.phone or '-'}")

    y -= 40

    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "Course & Payment Details")
    y -= 25

    p.setFont("Helvetica", 10)
    p.drawString(50, y, f"Course: {course.course_code} - {course.course_name}")
    y -= 20
    p.drawString(50, y, f"Paid Amount: {payment.amount}")
    y -= 20
    p.drawString(50, y, f"Installment: {payment.installment_number}/{payment.total_installments}")

    y -= 50

    p.line(50, y, width - 50, y)
    y -= 25

    p.setFont("Helvetica-Oblique", 9)
    p.drawString(50, y, "This is a system-generated invoice.")

    p.showPage()
    p.save()

    buffer.seek(0)

    filename = f"invoice_{payment.reference_no}.pdf"
    payment.invoice_pdf.save(
        filename,
        ContentFile(buffer.read()),
        save=False
    )