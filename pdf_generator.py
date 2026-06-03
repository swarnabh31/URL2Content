import markdown
import logging
from datetime import datetime
from weasyprint import HTML, CSS

logger = logging.getLogger(__name__)

def generate_professional_pdf(markdown_content: str, title: str = "Generated Content") -> bytes:
    """
    Convert markdown to styled PDF with full Unicode support using WeasyPrint.
    
    Args:
        markdown_content: The markdown content to convert to PDF
        title: Title for the PDF document
        
    Returns:
        bytes: PDF file content as bytes
    """
    try:
        # Convert markdown to HTML
        html_content = markdown.markdown(markdown_content, extensions=[
            'tables', 'fenced_code', 'toc'
        ])
        
        # Create full HTML document with styling
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                @page {{ size: A4; margin: 2.5cm; }}
                body {{ 
                    font-family: 'Segoe UI', system-ui, sans-serif; 
                    line-height: 1.6; 
                    color: #2d3748;
                }}
                h1 {{ 
                    color: #2563eb; 
                    border-bottom: 2px solid #2563eb; 
                    padding-bottom: 0.3em; 
                    margin-top: 0;
                }}
                h2 {{ 
                    color: #374151; 
                    margin-top: 1.5em; 
                    border-left: 4px solid #2563eb;
                    padding-left: 0.5em;
                }}
                h3 {{ 
                    color: #4b5563; 
                    margin-top: 1.25em;
                }}
                code {{ 
                    background: #f3f4f6; 
                    padding: 0.2em 0.4em; 
                    border-radius: 3px; 
                    font-family: 'Courier New', monospace;
                }}
                pre {{ 
                    background: #f3f4f6; 
                    padding: 1em; 
                    border-radius: 6px; 
                    overflow-x: auto;
                    margin: 1em 0;
                }}
                blockquote {{ 
                    border-left: 4px solid #2563eb; 
                    margin: 1.5em 0; 
                    padding-left: 1em; 
                    color: #6b7280;
                    font-style: italic;
                }}
                ul, ol {{ margin: 1em 0; padding-left: 2em; }}
                li {{ margin: 0.5em 0; }}
                a {{ color: #2563eb; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
                table {{ 
                    width: 100%; 
                    border-collapse: collapse; 
                    margin: 1em 0;
                }}
                th, td {{ 
                    border: 1px solid #e2e8f0; 
                    padding: 0.75em; 
                    text-align: left;
                }}
                th {{ 
                    background-color: #f8fafc; 
                    font-weight: 600;
                }}
                tr:nth-child(even) {{ background-color: #f8fafc; }}
                hr {{ 
                    border: 0; 
                    height: 1px; 
                    background: #e2e8f0; 
                    margin: 2em 0;
                }}
            </style>
        </head>
        <body>
            <h1>{title}</h1>
            <p style="color: #6b7280; font-size: 0.9em; margin-top: 1em;">
                Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')} 
                via YouTube Content Creator
            </p>
            {html_content}
        </body>
        </html>
        """
        
        # Generate PDF
        pdf_bytes = HTML(string=full_html).write_pdf()
        logger.info(f"Generated professional PDF ({len(pdf_bytes)} bytes)")
        return pdf_bytes
        
    except Exception as e:
        logger.error(f"Failed to generate PDF: {e}")
        # Return empty bytes if PDF generation fails
        return b""

# Fallback function for when weasyprint is not available
def generate_professional_pdf_fallback(markdown_content: str, title: str = "Generated Content") -> bytes:
    """
    Fallback PDF generation using reportlab when weasyprint is not available.
    This maintains Unicode support but with less sophisticated styling.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import io
        
        logger.info("Using fallback PDF generation with reportlab")
        
        # Create a byte buffer
        buffer = io.BytesIO()
        
        # Create the PDF document
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                              rightMargin=72, leftMargin=72,
                              topMargin=72, bottomMargin=18)
        
        # Get styles and add custom styles
        styles = getSampleStyleSheet()
        
        # Add custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#2563eb'),
            alignment=1  # Center
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=18,
            spaceAfter=12,
            textColor=colors.HexColor('#374151'),
            leftIndent=0
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=12,
            textColor=colors.black,
            leading=14
        )
        
        # Build the document content
        story = []
        
        # Add title
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 12))
        
        # Add generation info
        gen_info = f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')} via YouTube Content Creator"
        story.append(Paragraph(gen_info, styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Simple markdown parsing (basic implementation)
        lines = markdown_content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                story.append(Spacer(1, 6))
                continue
                
            # Handle headers
            if line.startswith('# '):
                story.append(Paragraph(line[2:], heading_style))
                story.append(Spacer(1, 12))
            elif line.startswith('## '):
                story.append(Paragraph(line[3:], styles['Heading2']))
                story.append(Spacer(1, 10))
            elif line.startswith('### '):
                story.append(Paragraph(line[4:], styles['Heading3']))
                story.append(Spacer(1, 8))
            # Handle code blocks (simple)
            elif line.startswith('```'):
                # Skip code block markers for simplicity
                continue
            # Handle blockquotes
            elif line.startswith('> '):
                story.append(Paragraph(line[2:], styles['Italic']))
                story.append(Spacer(1, 6))
            # Handle lists
            elif line.startswith('- ') or line.startswith('* '):
                story.append(Paragraph(f"• {line[2:]}", normal_style))
                story.append(Spacer(1, 4))
            elif line[0].isdigit() and '. ' in line:
                story.append(Paragraph(line, normal_style))
                story.append(Spacer(1, 4))
            # Regular paragraph
            else:
                story.append(Paragraph(line, normal_style))
                story.append(Spacer(1, 6))
        
        # Build PDF
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        logger.info(f"Generated fallback PDF ({len(pdf_bytes)} bytes)")
        return pdf_bytes
        
    except ImportError:
        logger.error("Reportlab not available for fallback PDF generation")
        return b""
    except Exception as e:
        logger.error(f"Failed to generate fallback PDF: {e}")
        return b""

def generate_pdf(markdown_content: str, title: str = "Generated Content") -> bytes:
    """
    Generate PDF from markdown content, trying weasyprint first then falling back to reportlab.
    
    Args:
        markdown_content: The markdown content to convert to PDF
        title: Title for the PDF document
        
    Returns:
        bytes: PDF file content as bytes
    """
    # Try weasyprint first (preferred)
    try:
        return generate_professional_pdf(markdown_content, title)
    except Exception as e:
        logger.warning(f"WeasyPrint PDF generation failed, trying fallback: {e}")
        # Fallback to reportlab
        return generate_professional_pdf_fallback(markdown_content, title)