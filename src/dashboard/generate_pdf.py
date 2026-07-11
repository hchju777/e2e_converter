"""대시보드 데이터로부터 PDF 리포트를 생성하는 모듈."""

from datetime import datetime
from pathlib import Path
from io import BytesIO

import pandas as pd
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak,
    Image as RLImage
)
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


def generate_pdf(
    output_path: str,
    period: str,
    respondents: int,
    metrics_df: pd.DataFrame,
    banner_names: list[str] = None,
) -> Path:
    """지표 결과로부터 PDF 보고서를 생성한다.
    
    Args:
        output_path: 생성할 PDF 파일 경로
        period: 보고 차수 (예: "26년 6차")
        respondents: 응답자 수
        metrics_df: 지표 계산 결과 DataFrame
        banner_names: 배너 이름 리스트 (기본값: 설정에서 자동 감지)
    
    Returns:
        생성된 PDF 파일 경로
    """
    if banner_names is None:
        banner_names = ["전체", "동적", "순진", "스위칭", "유지", "T1", "T2", "T3"]
    
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    
    # PDF 생성
    doc = SimpleDocTemplate(str(output), pagesize=A4)
    styles = getSampleStyleSheet()
    
    # 커스텀 스타일
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#008e4e'),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#008e4e'),
        spaceAfter=10,
        spaceBefore=10,
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6,
        alignment=TA_LEFT,
    )
    
    elements = []
    
    # 제목 페이지
    elements.append(Spacer(1, 1.5 * inch))
    elements.append(Paragraph("PsO H-Biologics Tracker", title_style))
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Paragraph(f"지표 계산 보고서 ({period})", heading_style))
    elements.append(Spacer(1, 0.5 * inch))
    
    # 기본 정보
    summary_data = [
        ["항목", "값"],
        ["보고 차수", period],
        ["응답자 수", str(respondents)],
        ["생성 일시", datetime.now().strftime("%Y년 %m월 %d일 %H:%M:%S")],
        ["총 지표 수", str(len(metrics_df))],
    ]
    summary_table = Table(summary_data, colWidths=[2 * inch, 2 * inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#008e4e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(summary_table)
    elements.append(PageBreak())
    
    # 배너별 요약
    elements.append(Paragraph("배너별 요약", heading_style))
    elements.append(Spacer(1, 0.2 * inch))
    
    for banner in banner_names:
        banner_data = metrics_df[metrics_df["배너조건"] == banner]
        if banner_data.empty:
            continue
        
        error_count = int((banner_data["오류"] != "").sum())
        warning_count = int((banner_data["경고"] != "").sum())
        
        banner_row = [
            [banner],
            [f"지표: {len(banner_data)}개 | 오류: {error_count}개 | 경고: {warning_count}개"],
        ]
        elements.append(Paragraph(f"• {banner} 배너", normal_style))
        elements.append(Spacer(1, 0.1 * inch))
    
    elements.append(Spacer(1, 0.2 * inch))
    elements.append(PageBreak())
    
    # 오류 및 경고 요약
    error_data = metrics_df[metrics_df["오류"] != ""]
    warning_data = metrics_df[metrics_df["경고"] != ""]
    
    if not error_data.empty or not warning_data.empty:
        elements.append(Paragraph("오류 및 경고", heading_style))
        elements.append(Spacer(1, 0.2 * inch))
        
        if not error_data.empty:
            elements.append(Paragraph("❌ 계산 오류", normal_style))
            error_rows = [["항목", "문항", "오류 메시지"]]
            for _, row in error_data.iterrows():
                error_rows.append([
                    str(row.get("항목", ""))[:20],
                    str(row.get("문항", ""))[:20],
                    str(row.get("오류", ""))[:40],
                ])
            
            error_table = Table(error_rows, colWidths=[1.5 * inch, 1.5 * inch, 2 * inch])
            error_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightcoral),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ]))
            elements.append(error_table)
            elements.append(Spacer(1, 0.3 * inch))
        
        if not warning_data.empty:
            elements.append(Paragraph("⚠️ 계산 경고", normal_style))
            warning_rows = [["항목", "문항", "경고 메시지"]]
            for _, row in warning_data.head(15).iterrows():  # 처음 15개만
                warning_rows.append([
                    str(row.get("항목", ""))[:20],
                    str(row.get("문항", ""))[:20],
                    str(row.get("경고", ""))[:40],
                ])
            
            warning_table = Table(warning_rows, colWidths=[1.5 * inch, 1.5 * inch, 2 * inch])
            warning_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0cf7a')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightyellow]),
            ]))
            elements.append(warning_table)
    
    elements.append(Spacer(1, 0.2 * inch))
    elements.append(PageBreak())
    
    # 상세 결과 (전체 배너만)
    total_data = metrics_df[metrics_df["배너조건"] == "전체"]
    if not total_data.empty:
        elements.append(Paragraph("전체 배너 상세 지표 (상위 30개)", heading_style))
        elements.append(Spacer(1, 0.2 * inch))
        
        detail_rows = [["구분", "항목", "문항", "결과", "경고"]]
        for _, row in total_data.head(30).iterrows():
            detail_rows.append([
                str(row.get("구분", ""))[:10],
                str(row.get("항목", ""))[:15],
                str(row.get("문항", ""))[:15],
                str(row.get("결과", ""))[:10],
                "⚠️" if row.get("경고") else "✓",
            ])
        
        detail_table = Table(detail_rows, colWidths=[0.8 * inch, 1.2 * inch, 1.2 * inch, 0.8 * inch, 0.5 * inch])
        detail_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#008e4e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f5ff')]),
        ]))
        elements.append(detail_table)
    
    # PDF 생성
    doc.build(elements)
    
    return output
