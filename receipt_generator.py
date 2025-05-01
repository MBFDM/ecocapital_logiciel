from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.units import inch
from datetime import datetime
import os

def generate_receipt_pdf(transaction_data, client_data, iban_data, company_name, 
                        logo_path=None, receipt_title="REÇU DE TRANSACTION", 
                        additional_notes="", include_signature=True):
    # Créer le dossier de sortie s'il n'existe pas
    os.makedirs("receipts", exist_ok=True)
    pdf_path = f"receipts/receipt_{transaction_data['id']}.pdf"
    
    # Créer le document
    doc = SimpleDocTemplate(pdf_path, pagesize=letter,
                           rightMargin=72, leftMargin=72,
                           topMargin=72, bottomMargin=72)
    
    styles = getSampleStyleSheet()
    
    # Style personnalisé
    styles.add(ParagraphStyle(
        name='ReceiptTitle',
        fontSize=16,
        leading=20,
        alignment=1,  # Centré
        spaceAfter=20,
        fontName='Helvetica-Bold'
    ))
    
    styles.add(ParagraphStyle(
        name='ReceiptHeader',
        fontSize=12,
        leading=15,
        fontName='Helvetica-Bold',
        spaceAfter=12
    ))
    
    styles.add(ParagraphStyle(
        name='ReceiptText',
        fontSize=10,
        leading=12,
        spaceAfter=6
    ))
    
    # Éléments du PDF
    elements = []
    
    # En-tête avec logo
    if logo_path and os.path.exists(logo_path):
        logo = Image(logo_path, width=1.5*inch, height=0.75*inch)
        elements.append(logo)
    
    # Titre
    elements.append(Paragraph(receipt_title, styles['ReceiptTitle']))
    elements.append(Paragraph(company_name, styles['ReceiptHeader']))
    elements.append(Spacer(1, 0.25*inch))
    
    # Informations de la transaction
    transaction_date = datetime.strptime(transaction_data['date'], '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y %H:%M')
    
    transaction_info = [
        ["Référence", transaction_data['id']],
        ["Date", transaction_date],
        ["Type", transaction_data['type']],
        ["Montant", f"{transaction_data['amount']:,.2f} {iban_data['currency']}"],
        ["IBAN", iban_data['iban']],
        ["Description", transaction_data['description'] or "N/A"]
    ]
    
    t = Table(transaction_info, colWidths=[1.5*inch, 4*inch])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#555555')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
    ]))
    
    elements.append(t)
    elements.append(Spacer(1, 0.25*inch))
    
    # Informations client
    client_header = Paragraph("Informations Client", styles['ReceiptHeader'])
    elements.append(client_header)
    
    client_info = [
        ["Nom", f"{client_data['first_name']} {client_data['last_name']}"],
        ["Type de Client", client_data['type']],
        ["Email", client_data['email'] or "N/A"],
        ["Téléphone", client_data['phone'] or "N/A"]
    ]
    
    t = Table(client_info, colWidths=[1.5*inch, 4*inch])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#555555')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
    ]))
    
    elements.append(t)
    elements.append(Spacer(1, 0.25*inch))
    
    # Notes additionnelles
    if additional_notes:
        notes_header = Paragraph("Notes", styles['ReceiptHeader'])
        elements.append(notes_header)
        notes_text = Paragraph(additional_notes.replace('\n', '<br/>'), styles['ReceiptText'])
        elements.append(notes_text)
        elements.append(Spacer(1, 0.25*inch))
    
    # Signature
    if include_signature:
        signature_line = Table([["", "Signature"]], colWidths=[4*inch, 1.5*inch])
        signature_line.setStyle(TableStyle([
            ('LINEABOVE', (1, 0), (1, 0), 1, colors.black),
            ('FONTSIZE', (1, 0), (1, 0), 10),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('VALIGN', (1, 0), (1, 0), 'TOP'),
        ]))
        elements.append(Spacer(1, 0.5*inch))
        elements.append(signature_line)
    
    # Pied de page
    elements.append(Spacer(1, 0.25*inch))
    footer = Paragraph(
        f"Reçu généré le {datetime.now().strftime('%d/%m/%Y %H:%M')} • {company_name}",
        ParagraphStyle(
            name='Footer',
            fontSize=8,
            textColor=colors.HexColor('#777777'),
            alignment=1
        )
    )
    elements.append(footer)
    
    # Générer le PDF
    doc.build(elements)
    return pdf_path