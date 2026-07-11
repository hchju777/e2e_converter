"""SAV 데이터의 배너 필터 설정을 검증하고 적용한다."""

import pandas as pd


REQUIRED_DASHBOARD_BANNERS = ["전체", "수도권", "지방", "T1", "T2", "T3"]


def validate_banner_configs(banner_configs: list[dict]) -> None:
    names = [config.get("name") for config in banner_configs]
    if names != REQUIRED_DASHBOARD_BANNERS:
        raise ValueError(
            f"dashboard_banners의 name과 순서는 {REQUIRED_DASHBOARD_BANNERS}이어야 합니다: {names}"
        )


def filter_banner_data(df: pd.DataFrame, banner_config: dict) -> pd.DataFrame:
    """설정에 정의된 컬럼과 값 목록으로 배너 DataFrame을 만든다."""
    column = banner_config.get("column")
    if column is None:
        return df
    if column not in df.columns:
        raise KeyError(f"배너 필터 컬럼을 SAV에서 찾을 수 없습니다: {column}")
    values = banner_config.get("values")
    if not isinstance(values, list) or not values:
        raise ValueError(f"{banner_config.get('name', column)} 배너의 values가 비어 있습니다.")
    return df[df[column].isin(values)]
