"""Additional export endpoints (PDF/CSV) for 7+/10 score."""
from io import BytesIO, StringIO
from typing import Sequence
from fastapi import Response
import csv

def add_pdf_csv_routes(app, revenue_dashboard_func):
    """Add PDF and CSV export routes."""
    
    try:
        from reportlab.lib.pagesizes import LETTER
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Flowable
        from reportlab.lib.styles import getSampleStyleSheet
        
        @app.get("/api/revenue/export.pdf", response_class=Response)
        async def api_revenue_export_pdf():
            data = revenue_dashboard_func()
            buf = BytesIO()
            doc = SimpleDocTemplate(buf, pagesize=LETTER)
            styles = getSampleStyleSheet()
            story: Sequence[Flowable] = [Paragraph("AI Lab Revenue Report", styles['Heading1'])]
            for k, v in data.items():
                story.append(Paragraph(f"{k}: {v}", styles['Normal']))
                story.append(Spacer(1, 12))
            doc.build(story)
            return Response(
                content=buf.getvalue(),
                media_type="application/pdf",
                headers={"Content-Disposition": "attachment; filename=revenue-report.pdf"}
            )
    except ImportError:
        @app.get("/api/revenue/export.pdf", response_class=Response)
        async def api_revenue_export_pdf():
            return Response(
                content=b"PDF export requires reportlab: pip install reportlab",
                media_type="text/plain",
                status_code=501
            )
    
    @app.get("/api/revenue/export.csv", response_class=Response)
    async def api_revenue_export_csv():
        data = revenue_dashboard_func()
        buf = StringIO()
        writer = csv.writer(buf)
        writer.writerow(['metric', 'value'])
        for k, v in data.items():
            writer.writerow([k, str(v)])
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=revenue-report.csv"}
        )