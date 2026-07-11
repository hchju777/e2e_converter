"""대시보드 데이터로부터 PPTX 프레젠테이션을 생성하는 모듈."""

from datetime import datetime
from pathlib import Path

import pandas as pd
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor


def generate_pptx(
    output_path: str,
    period: str,
    respondents: int,
    metrics_df: pd.DataFrame,
    banner_names: list[str] = None,
) -> Path:
    """지표 결과로부터 PPTX 프레젠테이션을 생성한다.
    
    Args:
        output_path: 생성할 PPTX 파일 경로
        period: 보고 차수 (예: "26년 6차")
        respondents: 응답자 수
        metrics_df: 지표 계산 결과 DataFrame
        banner_names: 배너 이름 리스트 (기본값: 설정에서 자동 감지)
    
    Returns:
        생성된 PPTX 파일 경로
    """
    if banner_names is None:
        banner_names = ["전체", "동적", "순진", "스위칭", "유지", "T1", "T2", "T3"]
    
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    
    # PPTX 프레젠테이션 생성
    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(7.5)
    
    # 색상 정의
    GREEN = RGBColor(0, 142, 78)  # #008e4e
    DARK_GRAY = RGBColor(23, 35, 60)  # #17233c
    LIGHT_GRAY = RGBColor(113, 128, 154)  # #71809a
    
    def add_title_slide(title, subtitle):
        """제목 슬라이드 추가"""
        slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank layout
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = GREEN
        
        # 제목
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(2.5), Inches(9), Inches(1.5))
        title_frame = title_box.text_frame
        title_frame.word_wrap = True
        p = title_frame.paragraphs[0]
        p.text = title
        p.font.size = Pt(54)
        p.font.bold = True
        p.font.color.rgb = RGBColor(255, 255, 255)
        p.alignment = PP_ALIGN.CENTER
        
        # 부제목
        subtitle_box = slide.shapes.add_textbox(Inches(0.5), Inches(4.2), Inches(9), Inches(1))
        subtitle_frame = subtitle_box.text_frame
        p = subtitle_frame.paragraphs[0]
        p.text = subtitle
        p.font.size = Pt(28)
        p.font.color.rgb = RGBColor(255, 255, 255)
        p.alignment = PP_ALIGN.CENTER
        
        return slide
    
    def add_content_slide(title, content_func):
        """컨텐츠 슬라이드 추가"""
        slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank layout
        
        # 제목
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(9), Inches(0.8))
        title_frame = title_box.text_frame
        p = title_frame.paragraphs[0]
        p.text = title
        p.font.size = Pt(40)
        p.font.bold = True
        p.font.color.rgb = GREEN
        
        # 구분선
        line = slide.shapes.add_shape(1, Inches(0.5), Inches(1.3), Inches(9), Inches(0))
        line.line.color.rgb = GREEN
        line.line.width = Pt(2)
        
        # 컨텐츠 영역
        content_box = slide.shapes.add_textbox(Inches(0.7), Inches(1.7), Inches(8.6), Inches(5.3))
        content_frame = content_box.text_frame
        content_frame.word_wrap = True
        
        content_func(content_frame)
        
        return slide
    
    # 슬라이드 1: 제목 페이지
    add_title_slide("PsO H-Biologics Tracker", f"지표 계산 리포트\n({period})")
    
    # 슬라이드 2: 개요
    def overview_content(text_frame):
        p = text_frame.paragraphs[0]
        p.text = "📊 보고서 개요"
        p.font.size = Pt(24)
        p.font.bold = True
        p.font.color.rgb = DARK_GRAY
        p.space_after = Pt(18)
        
        overview_data = [
            f"📅 보고 차수: {period}",
            f"👥 응답자 수: {respondents:,}명",
            f"📈 총 지표: {len(metrics_df)}개",
            f"⏰ 생성일시: {datetime.now().strftime('%Y년 %m월 %d일')}",
        ]
        
        for item in overview_data:
            p = text_frame.add_paragraph()
            p.text = item
            p.font.size = Pt(16)
            p.font.color.rgb = DARK_GRAY
            p.level = 0
            p.space_after = Pt(10)
    
    add_content_slide("개요", overview_content)
    
    # 슬라이드 3: 배너별 요약
    def banner_summary_content(text_frame):
        p = text_frame.paragraphs[0]
        p.text = "🎯 배너별 계산 결과"
        p.font.size = Pt(22)
        p.font.bold = True
        p.font.color.rgb = DARK_GRAY
        p.space_after = Pt(14)
        
        for banner in banner_names:
            banner_data = metrics_df[metrics_df["배너조건"] == banner]
            if banner_data.empty:
                continue
            
            error_count = int((banner_data["오류"] != "").sum())
            warning_count = int((banner_data["경고"] != "").sum())
            success_count = len(banner_data) - error_count
            
            p = text_frame.add_paragraph()
            p.text = f"{banner}"
            p.font.size = Pt(14)
            p.font.bold = True
            p.font.color.rgb = GREEN
            p.space_after = Pt(4)
            
            p = text_frame.add_paragraph()
            p.text = f"  ✓ 성공: {success_count} | ⚠️ 경고: {warning_count} | ❌ 오류: {error_count}"
            p.font.size = Pt(12)
            p.font.color.rgb = LIGHT_GRAY
            p.level = 1
            p.space_after = Pt(8)
    
    add_content_slide("배너별 요약", banner_summary_content)
    
    # 슬라이드 4: 오류 현황
    error_data = metrics_df[metrics_df["오류"] != ""]
    if not error_data.empty:
        def error_content(text_frame):
            p = text_frame.paragraphs[0]
            p.text = f"❌ 계산 오류 ({len(error_data)}건)"
            p.font.size = Pt(22)
            p.font.bold = True
            p.font.color.rgb = RGBColor(180, 37, 37)
            p.space_after = Pt(14)
            
            for idx, (_, row) in enumerate(error_data.head(10).iterrows()):
                p = text_frame.add_paragraph()
                p.text = f"• {row.get('항목', 'N/A')} | {row.get('문항', 'N/A')}"
                p.font.size = Pt(11)
                p.font.color.rgb = DARK_GRAY
                p.space_after = Pt(4)
                
                p = text_frame.add_paragraph()
                error_msg = str(row.get('오류', 'N/A'))[:60]
                p.text = f"  → {error_msg}"
                p.font.size = Pt(10)
                p.font.color.rgb = LIGHT_GRAY
                p.level = 1
                p.space_after = Pt(10)
            
            if len(error_data) > 10:
                p = text_frame.add_paragraph()
                p.text = f"... 외 {len(error_data) - 10}건 (CSV 참고)"
                p.font.size = Pt(10)
                p.font.italic = True
                p.font.color.rgb = LIGHT_GRAY
        
        add_content_slide("오류 현황", error_content)
    
    # 슬라이드 5: 경고 현황
    warning_data = metrics_df[metrics_df["경고"] != ""]
    if not warning_data.empty:
        def warning_content(text_frame):
            p = text_frame.paragraphs[0]
            p.text = f"⚠️ 계산 경고 ({len(warning_data)}건)"
            p.font.size = Pt(22)
            p.font.bold = True
            p.font.color.rgb = RGBColor(192, 120, 20)
            p.space_after = Pt(14)
            
            for idx, (_, row) in enumerate(warning_data.head(8).iterrows()):
                p = text_frame.add_paragraph()
                p.text = f"• {row.get('항목', 'N/A')}"
                p.font.size = Pt(11)
                p.font.color.rgb = DARK_GRAY
                p.space_after = Pt(2)
                
                p = text_frame.add_paragraph()
                warning_msg = str(row.get('경고', 'N/A'))[:70]
                p.text = f"  → {warning_msg}"
                p.font.size = Pt(10)
                p.font.color.rgb = LIGHT_GRAY
                p.level = 1
                p.space_after = Pt(12)
            
            if len(warning_data) > 8:
                p = text_frame.add_paragraph()
                p.text = f"... 외 {len(warning_data) - 8}건 (CSV 참고)"
                p.font.size = Pt(10)
                p.font.italic = True
                p.font.color.rgb = LIGHT_GRAY
        
        add_content_slide("경고 현황", warning_content)
    
    # 슬라이드 6: 추가 정보
    def footer_content(text_frame):
        p = text_frame.paragraphs[0]
        p.text = "📋 추가 정보"
        p.font.size = Pt(22)
        p.font.bold = True
        p.font.color.rgb = DARK_GRAY
        p.space_after = Pt(20)
        
        footer_text = [
            "✓ 상세 결과는 CSV 파일을 참고하세요",
            "✓ 대시보드 HTML에서 인터랙티브 차트를 확인할 수 있습니다",
            "✓ 경고 사항은 데이터 검증 시 참고해주세요",
            "✓ 추가 질문이나 오류 보고는 담당자에게 연락하세요",
        ]
        
        for text in footer_text:
            p = text_frame.add_paragraph()
            p.text = text
            p.font.size = Pt(14)
            p.font.color.rgb = DARK_GRAY
            p.space_after = Pt(12)
    
    add_content_slide("추가 정보", footer_content)
    
    # PPTX 저장
    prs.save(str(output))
    
    return output
