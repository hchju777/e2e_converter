"""PDF/PPTX 리포트에 포함할 대시보드 장표 순서와 배너 조합을 정의한다.

참고 리포트(PsO H-Biologics Tracker)의 페이지 구성과 동일하게, 각 page-section마다
캡처할 배너 탭을 순서대로 나열한다. banner가 None이면 탭 클릭 없이(고정 Total 등)
그대로 캡처한다.
"""

# (page-section id, banner 탭 data-f 값 또는 None)
REPORT_PAGES: list[tuple[str, str | None]] = [
    # PsO 환자 규모 (의사 1인 당 평균 환자 수) — 전체/지역/Tier
    ("p5", "전체"),
    ("p5", "수도권"),
    ("p5", "지방"),
    ("p5", "T1"),
    ("p5", "T2"),
    ("p5", "T3"),
    # 생물학적 제제 처방 비율
    ("p11", None),
    # 건선 환자 타입별 구성
    ("p12", None),
    ("p13", None),
    # 생물학적 제제 브랜드별 처방 비율
    ("p14", None),
    ("p15", None),
    ("p16", None),
    ("p17", None),
    ("p18", None),
    ("p19", None),
    ("p20", None),
    ("p21", None),
    ("p22", None),
    ("p23", None),
    # Share of Voice — Detailing
    ("p24", None),
    ("p25", None),
    ("p26", None),
    ("p27", None),
    ("p28", None),
    ("p29", None),
    # Share of Voice — Brand Activity / Symposium
    ("p30", None),
    ("p31", None),
    ("p32", None),
    ("p33", None),
]
