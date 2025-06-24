"""warehouse_loader.py

HVDC Warehouse Excel 전용 로더.

* 역할
    1. HVDC‑ADOPT Warehouse 템플릿(Outdoor / Indoor) 시트를 자동 감지하여 `pandas.DataFrame` 으로 로드.
    2. 원본 컬럼명을 표준 필드명으로 매핑하고 타입을 변환한다.
    3. 결측·N/A 문자열을 NaN → 0 으로 전처리.
    4. 파싱된 DataFrame 은 후속 온톨로지 매핑 및 재고 계산 엔진에서 직접 사용된다.

사용 예시::

    from warehouse_loader import load_hvdc_warehouse_file
    df = load_hvdc_warehouse_file('HVDC_WAREHOUSE_2024Q1.xlsx')

Author: GPT‑Assistant (2025‑06‑24)
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import List, Tuple, Union

import pandas as _pd

# ----------------------------------------------------------------------------
# 내부 상수 및 컬럼 매핑
# ----------------------------------------------------------------------------

# 원본 컬럼명 → 표준 필드명(dict key = lower‑stripped 원본)
_COL_MAP = {
    "operation month": "operation_month",
    "shipment no": "shipment_no",
    "category": "category",
    "20dc": "twenty_dc",
    "20fr": "twenty_fr",
    "40dc": "forty_dc",
    "40fr": "forty_fr",
    "cntr no.": "container_count",
    "cntr unstuffing q'ty": "cntr_q_in",
    "cntr stuffing q'ty": "cntr_q_out",
    "start": "start_date",
    "finish": "finish_date",
    "pkgs": "pkgs",
    "weight (kg)": "weight_kg",
    "cbm": "cbm",
    "handling in freight ton": "handling_in_ft",
    "handling out freight ton": "handling_out_ft",
    "sqm": "sqm",
    "amount": "amount",
    "handling in": "handling_in_cost",
    "handling out": "handling_out_cost",
    "unstuffing": "unstuffing_cost",
    "stuffing": "stuffing_cost",
    "folk lift": "forklift_cost",
    "crane": "crane_cost",
    "total": "total_cost",
    "billing month": "billing_month",
}

_DATE_COLS = ["operation_month", "start_date", "finish_date", "billing_month"]
_FLOAT_COLS = [
    "twenty_dc",
    "twenty_fr",
    "forty_dc",
    "forty_fr",
    "container_count",
    "cntr_q_in",
    "cntr_q_out",
    "pkgs",
    "weight_kg",
    "cbm",
    "handling_in_ft",
    "handling_out_ft",
    "sqm",
    "amount",
    "handling_in_cost",
    "handling_out_cost",
    "unstuffing_cost",
    "stuffing_cost",
    "forklift_cost",
    "crane_cost",
    "total_cost",
]

_NA_VALUES = ["n/a", "na", "N/A", "NA", "-"]

# ----------------------------------------------------------------------------
# 공개 API
# ----------------------------------------------------------------------------

def load_hvdc_warehouse_file(  # noqa: D401
    path: Union[str, Path],
    *,
    sheet_name: Union[str, int, None] = 0,
    header: Union[int, List[int]] = 0,
) -> _pd.DataFrame:
    """단일 Excel 파일을 로드해 표준화된 :class:`pandas.DataFrame` 을 반환한다.

    Parameters
    ----------
    path: str | Path
        대상 Excel 파일 경로.
    sheet_name: str | int | None
        판다스 sheet 선택 파라미터. 기본 0.
    header: int | list[int]
        헤더 행 인덱스. 기본 0.

    Returns
    -------
    pandas.DataFrame
        표준화 및 타입 변환 완료된 데이터프레임.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Excel file not found: {path}")

    df_raw = _pd.read_excel(
        path,
        sheet_name=sheet_name,
        header=header,
        na_values=_NA_VALUES,
        dtype=str,  # 일단 문자열로 읽은 뒤 변환
    )

    # 컬럼명 정규화 (소문자 + strip) 후 매핑
    df_raw.columns = [str(c).strip().lower() for c in df_raw.columns]
    missing_cols: List[str] = [c for c in _COL_MAP if c not in df_raw.columns]
    if missing_cols:
        raise ValueError(f"Required columns not found in {path.name}: {missing_cols}")

    df = df_raw.rename(columns=_COL_MAP)

    # dtype 변환
    for col in _DATE_COLS:
        df[col] = _pd.to_datetime(df[col], errors="coerce").dt.date

    for col in _FLOAT_COLS:
        df[col] = _pd.to_numeric(df[col], errors="coerce").fillna(0)

    # 카테고리 문자열 정규화
    df["category"] = (
        df["category"].str.strip().str.lower().replace({"indoor(m44)": "indoor", "outdoor": "outdoor"})
    )

    # 파생 컬럼: transaction_type (IN / OUT) 판별 – 컨테이너 수량 기준
    df["transaction_type"] = _pd.np.where(df["cntr_q_in"] > 0, "IN", "OUT")

    # 결측치 0 처리 후 반환
    return df.fillna(0)


def load_hvdc_warehouse_dir(directory: Union[str, Path]) -> _pd.DataFrame:
    """디렉터리 내 모든 Excel 파일을 로드 후 단일 DataFrame 으로 concat.

    * 확장자: .xlsx, .xls

    Returns
    -------
    pandas.DataFrame
    """
    directory = Path(directory)
    if not directory.is_dir():
        raise NotADirectoryError(directory)

    frames: List[_pd.DataFrame] = []
    for fp in directory.glob("*.xls*"):
        try:
            frames.append(load_hvdc_warehouse_file(fp))
        except Exception as exc:  # pylint: disable=broad-except
            print(f"[WARN] {fp.name}: {exc}")
    if not frames:
        raise RuntimeError(f"No valid Excel files found in {directory}")
    return _pd.concat(frames, ignore_index=True)


# ----------------------------------------------------------------------------
# CLI 테스트 실행
# ----------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    import argparse

    parser = argparse.ArgumentParser(description="HVDC Warehouse Excel Loader")
    parser.add_argument("excel", type=Path, help="Target Excel file or directory")
    args = parser.parse_args()

    path_arg: Path = args.excel
    if path_arg.is_dir():
        df_out = load_hvdc_warehouse_dir(path_arg)
    else:
        df_out = load_hvdc_warehouse_file(path_arg)

    print(df_out.head()) 