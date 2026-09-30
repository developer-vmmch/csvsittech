import os
import io
import qrcode
from typing import Optional
from django.conf import settings
from django.utils import timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image as RLImage,
    Table, TableStyle, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.graphics.barcode import code128
from reportlab.graphics.shapes import Drawing


class PatientPdfGenerator:
    """
    Generates an official, publication-quality A4 PDF for OP & Review slips.
    Includes VMMC hospital emblem, NABH Pre-accredited badge, scannable Code128 barcode,
    patient demographic details, and the secure public QR reference.
    """

    def __init__(self, token_obj):
        self.token_obj = token_obj
        self.patient = token_obj.patient
        self.visit = token_obj.visit
        self.print_type = (token_obj.print_type or 'OP').upper()

    def generate_pdf(self) -> bytes:
        buffer = io.BytesIO()

        # Page setup: A4 with neat 12mm margins
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=12 * mm,
            rightMargin=12 * mm,
            topMargin=12 * mm,
            bottomMargin=12 * mm,
            title=f"OP_Slip_{self.patient.patient_id}",
            author="Vinayaka Missions Medical College & Hospital"
        )

        styles = getSampleStyleSheet()

        # Custom paragraph styles
        style_h1 = ParagraphStyle(
            'HospitalTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=12,
            leading=14,
            alignment=TA_CENTER,
            textColor=colors.black
        )

        style_address = ParagraphStyle(
            'HospitalAddress',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=7.5,
            leading=10,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1e293b')
        )

        style_hfrid = ParagraphStyle(
            'HFRIDText',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=7,
            leading=8.5,
            alignment=TA_CENTER,
            textColor=colors.black
        )

        style_banner_mid = ParagraphStyle(
            'BannerMiddle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=11,
            leading=13,
            alignment=TA_CENTER,
            textColor=colors.black
        )

        style_banner_dept = ParagraphStyle(
            'BannerDept',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=12,
            alignment=TA_RIGHT,
            textColor=colors.black
        )

        style_caption = ParagraphStyle(
            'QRCaption',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=7.5,
            leading=9,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#0f172a')
        )

        elements = []

        # ----------------------------------------------------
        # 1. Header (3 Columns: Logo Left | Center Info | NABH Right)
        # ----------------------------------------------------
        static_dir = getattr(settings, 'STATICFILES_DIRS', [settings.BASE_DIR / 'static'])[0]
        vmmc_logo_path = os.path.join(static_dir, 'images', 'vmmc_logo.png')
        nabh_logo_path = os.path.join(static_dir, 'images', 'nabh_logo.png')

        logo_img = RLImage(vmmc_logo_path, width=18 * mm, height=18 * mm) if os.path.exists(vmmc_logo_path) else Paragraph("<b>VMMC</b>", style_h1)

        center_text = [
            Paragraph("<b>VINAYAKA MISSIONS MEDICAL COLLEGE &amp; HOSPITAL</b>", style_h1),
            Spacer(1, 1 * mm),
            Paragraph("Keezhakasakudy Medu, Karaikal Pin : 609609<br/>Phone No: 04368 - 263277 , 263338<br/>www.vmmckl.edu.in", style_address)
        ]

        if os.path.exists(nabh_logo_path):
            # NABH image aspect ratio: original is 800x693
            nabh_w = 20 * mm
            nabh_h = 20 * mm * (693.0 / 800.0)
            nabh_img = RLImage(nabh_logo_path, width=nabh_w, height=nabh_h)
            right_cell = [
                nabh_img,
                Spacer(1, 1 * mm),
                Paragraph("HFRID : IN3410000736", style_hfrid)
            ]
        else:
            right_cell = [Paragraph("<b>NABH PRE-ACCREDITED</b><br/>HFRID : IN3410000736", style_hfrid)]

        header_table = Table(
            [[logo_img, center_text, right_cell]],
            colWidths=[24 * mm, 138 * mm, 24 * mm]
        )
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('ALIGN', (2, 0), (2, 0), 'CENTER'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 2.5 * mm))

        # ----------------------------------------------------
        # 2. UH ID Line
        # ----------------------------------------------------
        uhid_text = f"<b>UH ID : {self.patient.patient_id}</b>"
        elements.append(Paragraph(uhid_text, ParagraphStyle('UHID', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, leading=12)))
        elements.append(Spacer(1, 1.5 * mm))

        # ----------------------------------------------------
        # 3. Banner Bar: Barcode (Left) | OUT PATIENT - NEW/REVIEW (Middle) | Department (Right)
        # ----------------------------------------------------
        # Draw Code128 barcode
        from reportlab.graphics.barcode import createBarcodeDrawing
        bc_val = str(self.patient.patient_id).strip()
        bc_drawing = createBarcodeDrawing('Code128', value=bc_val, barHeight=7 * mm, barWidth=1.0, humanReadable=False)

        slip_title = "OUT PATIENT - REVIEW" if self.print_type == 'REVIEW' else "OUT PATIENT - NEW"
        dept_name = ((self.visit.department if self.visit and self.visit.department else self.patient.department) or "GENERAL MEDICINE").upper()

        banner_table = Table(
            [[bc_drawing, Paragraph(f"<b>{slip_title}</b>", style_banner_mid), Paragraph(f"<b>{dept_name}</b>", style_banner_dept)]],
            colWidths=[55 * mm, 75 * mm, 56 * mm]
        )
        banner_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 1 * mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1 * mm),
            ('LEFTPADDING', (0, 0), (-1, -1), 1 * mm),
            ('RIGHTPADDING', (0, 0), (-1, -1), 1 * mm),
            ('LINEBELOW', (0, 0), (-1, -1), 0.75, colors.black),
            ('LINEABOVE', (0, 0), (-1, -1), 0.75, colors.black),
        ]))
        elements.append(banner_table)
        elements.append(Spacer(1, 2 * mm))

        # ----------------------------------------------------
        # 4. Demographics Section
        # ----------------------------------------------------
        op_num = self.patient.op_number or self.patient.patient_id
        if self.visit and self.visit.visit_date:
            v_date = self.visit.visit_date
        elif self.patient.created_at:
            v_date = self.patient.created_at
        else:
            v_date = timezone.now()
        date_str = v_date.strftime('%d/%b/%Y %H:%M:%S')

        p_name = f"{self.patient.title}.{self.patient.name}".upper()
        p_guardian = (self.patient.guardian_name or "--").upper()
        p_age = f"{self.patient.age_years} Yr(s) / {self.patient.gender}"

        # Row 1: HR Number & Regn.Date
        demo_row1 = Table(
            [
                [
                    Paragraph(f"<b>HR Number :</b> <b>{op_num}</b>", ParagraphStyle('HR', parent=styles['Normal'], fontSize=9, fontName='Helvetica')),
                    Paragraph(f"<b>Regn.Date :</b> <b>{date_str}</b>", ParagraphStyle('RegDate', parent=styles['Normal'], fontSize=9, fontName='Helvetica', alignment=TA_RIGHT))
                ]
            ],
            colWidths=[93 * mm, 93 * mm]
        )
        demo_row1.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#94a3b8')),
            ('TOPPADDING', (0, 0), (-1, -1), 1.5 * mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5 * mm),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(demo_row1)
        elements.append(Spacer(1, 1.5 * mm))

        # Row 2: Name, Guardian, Age
        demo_row2 = Table(
            [
                [
                    Paragraph(f"<b>Name :</b> <font color='#1d4ed8'><b>{p_name}</b></font>", ParagraphStyle('DName', parent=styles['Normal'], fontSize=9, fontName='Helvetica')),
                    Paragraph(f"<b>Guardian :</b> {p_guardian}", ParagraphStyle('DGuard', parent=styles['Normal'], fontSize=9, fontName='Helvetica')),
                    Paragraph(f"<b>Age :</b> {p_age}", ParagraphStyle('DAge', parent=styles['Normal'], fontSize=9, fontName='Helvetica'))
                ]
            ],
            colWidths=[70 * mm, 60 * mm, 56 * mm]
        )
        demo_row2.setStyle(TableStyle([
            ('TOPPADDING', (0, 0), (-1, -1), 1 * mm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5 * mm),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(demo_row2)
        elements.append(Spacer(1, 4 * mm))

        # ----------------------------------------------------
        # 5. Bottom Center QR Code (Encodes Secure Public URL)
        # ----------------------------------------------------
        qr_url = self.token_obj.get_public_url()
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=4,
            border=1
        )
        qr.add_data(qr_url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        qr_buffer = io.BytesIO()
        qr_img.save(qr_buffer, format="PNG")
        qr_buffer.seek(0)

        qr_rl_img = RLImage(qr_buffer, width=22 * mm, height=22 * mm)

        qr_block = Table(
            [
                [qr_rl_img],
                [Spacer(1, 1 * mm)],
                [Paragraph("SCAN FOR STICKER / PRINT VIEW", style_caption)]
            ],
            colWidths=[186 * mm]
        )
        qr_block.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(KeepTogether(qr_block))

        # Build document into buffer
        doc.build(elements)
        return buffer.getvalue()
