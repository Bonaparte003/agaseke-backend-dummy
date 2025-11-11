"""Shared utility functions for report generation"""
import csv
from datetime import datetime
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

def generate_csv_report(data, filename, headers):
    """Generate CSV report from data"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(headers)
    writer.writerows(data)
    
    return response

def generate_pdf_report(data, filename, title, headers, summary_data=None):
    """Generate PDF report from data"""
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
    
    # Create the PDF object
    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []
    
    # Get styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    # Add title
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 20))
    
    # Add summary if provided
    if summary_data:
        summary_style = ParagraphStyle(
            'Summary',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=20
        )
        for key, value in summary_data.items():
            elements.append(Paragraph(f"<b>{key}:</b> {value}", summary_style))
        elements.append(Spacer(1, 20))
    
    # Create table
    if data:
        table = Table([headers] + data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(table)
    
    # Build PDF
    doc.build(elements)
    return response

def get_token_user(request):
    """Helper function to get user from JWT token authentication"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header.replace('Bearer ', '')
    try:
        # Decode JWT token
        from rest_framework_simplejwt.tokens import AccessToken
        from users.models import User
        
        # Validate and decode the token
        access_token = AccessToken(token)
        user_id = access_token['user_id']
        
        # Get user from database
        user = User.objects.get(id=user_id)
        return user
    except Exception as e:
        # Token is invalid, expired, or user doesn't exist
        print(f"Token validation error: {str(e)}")  # For debugging
        return None

