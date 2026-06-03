from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from io import BytesIO
import os
from django.conf import settings


BROWN = colors.HexColor("#3d2008")
GOLD = colors.HexColor("#c9a84c")
LIGHT_GREY = colors.HexColor("#f5f5f5")


def generate_invoice_pdf(booking):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    bold_style = ParagraphStyle("bold", parent=normal, fontName="Helvetica-Bold")

    heading = ParagraphStyle("heading", parent=normal, fontSize=20, fontName="Helvetica-Bold",
                             textColor=BROWN, spaceAfter=4)
    subheading = ParagraphStyle("subheading", parent=normal, fontSize=10, textColor=GOLD,
                                fontName="Helvetica-Bold", spaceAfter=2)
    right_style = ParagraphStyle("right", parent=normal, alignment=TA_RIGHT)
    right_bold = ParagraphStyle("right_bold", parent=normal, alignment=TA_RIGHT,
                                fontName="Helvetica-Bold", fontSize=11)
    small = ParagraphStyle("small", parent=normal, fontSize=8, textColor=colors.grey)
    center = ParagraphStyle("center", parent=normal, alignment=TA_CENTER, fontSize=8, textColor=colors.grey)

    story = []

    # --- Header: logo + company info ---
    logo_path = os.path.join(settings.BASE_DIR, "rentals", "static", "rentals", "logo.jpg")
    company_lines = [
        Paragraph("Prairie Skies RV Rentals Ltd", heading),
        Paragraph("Yorkton, Saskatchewan", normal),
        Paragraph("Call or Text: 306-520-2420", normal),
        Paragraph("Prairie.skies@gmail.com", normal),
    ]

    if os.path.exists(logo_path):
        from reportlab.platypus import Image
        logo = Image(logo_path, width=1.3 * inch, height=1.3 * inch)
        header_table = Table([[logo, company_lines]], colWidths=[1.5 * inch, 4.5 * inch])
        header_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(header_table)
    else:
        for line in company_lines:
            story.append(line)

    story.append(Spacer(1, 0.1 * inch))
    story.append(HRFlowable(width="100%", thickness=2, color=BROWN))
    story.append(Spacer(1, 0.15 * inch))

    # --- Invoice title + number ---
    invoice_info = [
        [Paragraph("INVOICE", ParagraphStyle("inv", parent=normal, fontSize=22,
                                              fontName="Helvetica-Bold", textColor=BROWN)),
         Paragraph(f"Invoice #INV-{booking.pk:04d}", right_bold)],
        ["", Paragraph(f"Date: {booking.created_at.strftime('%B %d, %Y')}", right_style)],
        ["", Paragraph(f"Status: {'PAID' if booking.status == 'completed' else 'PENDING'}", right_style)],
    ]
    inv_table = Table(invoice_info, colWidths=[3.5 * inch, 3.5 * inch])
    inv_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(inv_table)
    story.append(Spacer(1, 0.2 * inch))

    # --- Bill to ---
    story.append(Paragraph("BILL TO", subheading))
    story.append(Paragraph(booking.customer.full_name, bold_style))
    story.append(Paragraph(booking.customer.email, normal))
    story.append(Paragraph(booking.customer.phone, normal))
    story.append(Spacer(1, 0.2 * inch))

    # --- Booking details ---
    story.append(Paragraph("BOOKING DETAILS", subheading))
    details = [
        ["RV", booking.rv.name],
        ["Dates", f"{booking.start_date} → {booking.end_date}"],
        ["Duration", f"{booking.num_days} day{'s' if booking.num_days != 1 else ''}"],
        ["Pickup / Delivery",
         f"Delivery to {booking.delivery_address} ({booking.delivery_distance_km} km)"
         if booking.is_delivery else "Customer Pickup — Yorkton, SK"],
    ]
    det_table = Table(details, colWidths=[2 * inch, 5 * inch])
    det_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT_GREY),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, LIGHT_GREY]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(det_table)
    story.append(Spacer(1, 0.25 * inch))

    # --- Charges ---
    story.append(Paragraph("CHARGES", subheading))

    charge_rows = [
        [Paragraph("Description", bold_style), Paragraph("Amount", ParagraphStyle("rb", parent=normal, fontName="Helvetica-Bold", alignment=TA_RIGHT))],
        [f"RV Rental — {booking.rv.name} ({booking.num_days} days × ${booking.rv.price_per_day}/day)",
         Paragraph(f"${booking.rental_total}", right_style)],
    ]

    if booking.is_delivery:
        charge_rows.append([
            f"Delivery Charge ({booking.delivery_distance_km} km × 2 trips × $2.50/km)",
            Paragraph(f"${booking.delivery_charge}", right_style),
        ])

    charge_rows += [
        ["GST (5%)", Paragraph(f"${booking.gst_amount}", right_style)],
        ["PST (6%)", Paragraph(f"${booking.pst_amount}", right_style)],
        ["Damage Deposit (refundable)", Paragraph(f"${booking.damage_deposit}", right_style)],
    ]

    # Total row
    charge_rows.append([
        Paragraph("TOTAL DUE", ParagraphStyle("tot", parent=normal, fontName="Helvetica-Bold", fontSize=11)),
        Paragraph(f"${booking.total_charged}", ParagraphStyle("totr", parent=normal, fontName="Helvetica-Bold", fontSize=11, alignment=TA_RIGHT, textColor=BROWN)),
    ])

    charge_table = Table(charge_rows, colWidths=[5 * inch, 2 * inch])
    charge_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BROWN),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, LIGHT_GREY]),
        ("BACKGROUND", (0, -1), (-1, -1), LIGHT_GREY),
        ("LINEABOVE", (0, -1), (-1, -1), 1.5, BROWN),
        ("GRID", (0, 0), (-1, -2), 0.5, colors.lightgrey),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(charge_table)
    story.append(Spacer(1, 0.3 * inch))

    # --- Notes ---
    if booking.special_requests:
        story.append(Paragraph("NOTES", subheading))
        story.append(Paragraph(booking.special_requests, normal))
        story.append(Spacer(1, 0.2 * inch))

    # --- Footer ---
    story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph("Thank you for choosing Prairie Skies RV Rentals Ltd!", center))
    story.append(Paragraph("Questions? Call or text 306-520-2420 or email Prairie.skies@gmail.com", center))

    doc.build(story)
    buffer.seek(0)
    return buffer


def generate_quote_pdf(quote):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=0.75*inch, leftMargin=0.75*inch,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)

    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    bold_style = ParagraphStyle("bold", parent=normal, fontName="Helvetica-Bold")
    heading = ParagraphStyle("heading", parent=normal, fontSize=20, fontName="Helvetica-Bold", textColor=BROWN, spaceAfter=4)
    subheading = ParagraphStyle("subheading", parent=normal, fontSize=10, textColor=GOLD, fontName="Helvetica-Bold", spaceAfter=2)
    right_style = ParagraphStyle("right", parent=normal, alignment=TA_RIGHT)
    right_bold = ParagraphStyle("right_bold", parent=normal, alignment=TA_RIGHT, fontName="Helvetica-Bold", fontSize=11)
    center = ParagraphStyle("center", parent=normal, alignment=TA_CENTER, fontSize=8, textColor=colors.grey)

    story = []

    # Header
    logo_path = os.path.join(settings.BASE_DIR, "rentals", "static", "rentals", "logo.jpg")
    company_lines = [
        Paragraph("Prairie Skies RV Rentals Ltd", heading),
        Paragraph("Yorkton, Saskatchewan", normal),
        Paragraph("Call or Text: 306-520-2420", normal),
        Paragraph("Prairie.skies@gmail.com", normal),
    ]
    if os.path.exists(logo_path):
        from reportlab.platypus import Image
        logo = Image(logo_path, width=1.3*inch, height=1.3*inch)
        header_table = Table([[logo, company_lines]], colWidths=[1.5*inch, 4.5*inch])
        header_table.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "MIDDLE")]))
        story.append(header_table)
    else:
        for line in company_lines:
            story.append(line)

    story.append(Spacer(1, 0.1*inch))
    story.append(HRFlowable(width="100%", thickness=2, color=BROWN))
    story.append(Spacer(1, 0.15*inch))

    # Quote title
    quote_info = [
        [Paragraph("QUOTE", ParagraphStyle("q", parent=normal, fontSize=22, fontName="Helvetica-Bold", textColor=BROWN)),
         Paragraph(f"Quote #QT-{quote.pk:04d}", right_bold)],
        ["", Paragraph(f"Date: {quote.created_at.strftime('%B %d, %Y')}", right_style)],
        ["", Paragraph(f"Valid until: {quote.expires_at.strftime('%B %d, %Y %I:%M %p')}", right_style)],
    ]
    qt = Table(quote_info, colWidths=[3.5*inch, 3.5*inch])
    qt.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP")]))
    story.append(qt)
    story.append(Spacer(1, 0.2*inch))

    # Prepared for
    story.append(Paragraph("PREPARED FOR", subheading))
    story.append(Paragraph(quote.customer_name, bold_style))
    story.append(Paragraph(quote.customer_email, normal))
    story.append(Paragraph(quote.customer_phone, normal))
    story.append(Spacer(1, 0.2*inch))

    # Quote details
    story.append(Paragraph("QUOTE DETAILS", subheading))
    details = [
        ["RV", quote.rv.name],
        ["Dates", f"{quote.start_date} → {quote.end_date}"],
        ["Duration", f"{quote.num_days} day{'s' if quote.num_days != 1 else ''}"],
        ["Pickup / Delivery",
         f"Delivery to {quote.delivery_address} ({quote.delivery_distance_km} km)"
         if quote.is_delivery else "Customer Pickup — Yorkton, SK"],
    ]
    det_table = Table(details, colWidths=[2*inch, 5*inch])
    det_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,-1), LIGHT_GREY),
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.white, LIGHT_GREY]),
        ("GRID", (0,0), (-1,-1), 0.5, colors.lightgrey),
        ("PADDING", (0,0), (-1,-1), 5),
    ]))
    story.append(det_table)
    story.append(Spacer(1, 0.25*inch))

    # Estimated charges
    story.append(Paragraph("ESTIMATED CHARGES", subheading))
    charge_rows = [
        [Paragraph("Description", bold_style), Paragraph("Amount", ParagraphStyle("rb", parent=normal, fontName="Helvetica-Bold", alignment=TA_RIGHT))],
        [f"RV Rental — {quote.rv.name} ({quote.num_days} days × ${quote.rv.price_per_day}/day)",
         Paragraph(f"${quote.rental_total}", right_style)],
    ]
    if quote.is_delivery:
        charge_rows.append([
            f"Delivery Charge ({quote.delivery_distance_km} km × 2 trips × $2.50/km)",
            Paragraph(f"${quote.delivery_charge}", right_style),
        ])
    charge_rows += [
        ["GST (5%)", Paragraph(f"${quote.gst_amount}", right_style)],
        ["PST (6%)", Paragraph(f"${quote.pst_amount}", right_style)],
        ["Damage Deposit (refundable)", Paragraph(f"${quote.damage_deposit}", right_style)],
        [Paragraph("ESTIMATED TOTAL", ParagraphStyle("tot", parent=normal, fontName="Helvetica-Bold", fontSize=11)),
         Paragraph(f"${quote.total_estimate}", ParagraphStyle("totr", parent=normal, fontName="Helvetica-Bold", fontSize=11, alignment=TA_RIGHT, textColor=BROWN))],
    ]
    charge_table = Table(charge_rows, colWidths=[5*inch, 2*inch])
    charge_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), BROWN),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS", (0,1), (-1,-2), [colors.white, LIGHT_GREY]),
        ("BACKGROUND", (0,-1), (-1,-1), LIGHT_GREY),
        ("LINEABOVE", (0,-1), (-1,-1), 1.5, BROWN),
        ("GRID", (0,0), (-1,-2), 0.5, colors.lightgrey),
        ("PADDING", (0,0), (-1,-1), 6),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(charge_table)
    story.append(Spacer(1, 0.2*inch))

    # Disclaimer
    story.append(Paragraph(
        "This quote is an estimate only and does not reserve the dates. "
        "Prices are valid for 24 hours from the date of issue. "
        "Dates are subject to availability at time of booking.",
        ParagraphStyle("disc", parent=normal, fontSize=8, textColor=colors.grey)
    ))

    if quote.notes:
        story.append(Spacer(1, 0.15*inch))
        story.append(Paragraph("NOTES", subheading))
        story.append(Paragraph(quote.notes, normal))

    story.append(Spacer(1, 0.2*inch))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("Thank you for considering Prairie Skies RV Rentals Ltd!", center))
    story.append(Paragraph("Questions? Call or text 306-520-2420 or email Prairie.skies@gmail.com", center))

    doc.build(story)
    buffer.seek(0)
    return buffer
