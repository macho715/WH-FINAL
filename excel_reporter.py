"""excel_reporter.py – v0.5.1 (2025‑06‑24)

HVDC Warehouse 월별 재무·재고 리포트 생성기
=========================================

변경 사항
---------
* **워크북·워크시트 스타일링** 시 `writer.book` 과 `writer.sheets[sheet_name]` 를 분리 사용하도록 수정.
* `_style_worksheet(ws, workbook, nrows, ncols)` 시그니처로 워크북 객체를 인자로 전달.
* `generate_financial_report()` 와 `generate_full_dashboard()` 모두 새 시그니처 적용.

Dependencies: pandas, xlsxwriter

"""
from __future__ import annotations

from pathlib import Path
from typing import Union

import pandas as pd

from core.inventory_engine import InventoryEngine

# -----------------------------------------------------------------------------
# 내부 헬퍼
# -----------------------------------------------------------------------------

def _style_worksheet(ws, workbook, nrows: int, ncols: int) -> None:  # noqa: ANN001
    """공통 시트 스타일: 숫자 서식 + 3‑Color Scale.

    Parameters
    ----------
    ws : xlsxwriter.worksheet.Worksheet
        서식 적용 대상 워크시트.
    workbook : xlsxwriter.workbook.Workbook
        서식(Format) 객체를 생성하기 위해 필요.
    nrows : int
        데이터가 끝나는 마지막 행 번호 (헤더 포함).
    ncols : int
        데이터가 끝나는 마지막 열 번호.
    """
    num_fmt = workbook.add_format({"num_format": "#,##0.00"})
    ws.set_column(0, ncols - 1, 16, num_fmt)

    # 마지막 열(금액) 3‑Color Scale 조건부 서식 – 최대(녹) / 중간(노랑) / 최소(빨)
    ws.conditional_format(1, ncols - 1, nrows, ncols - 1, {
        "type": "3_color_scale",
        "min_color": "#F8696B",
        "mid_color": "#FFEB84",
        "max_color": "#63BE7B",
    })


# -----------------------------------------------------------------------------
# 리포트 생성 API
# -----------------------------------------------------------------------------

def generate_financial_report(raw_df: pd.DataFrame, output_path: Union[str, Path]) -> Path:
    """BillingMonth × Category 피벗으로 Total_Amount 집계 후 Excel 저장."""

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Pivot (BillingMonth × StorageType)
    fin_pivot = (
        raw_df
        .pivot_table(index="Billing month", columns="Category", values="Amount", aggfunc="sum", fill_value=0)
        .reset_index()
    )

    with pd.ExcelWriter(out_path, engine="xlsxwriter") as writer:
        fin_pivot.to_excel(writer, sheet_name="FinancialSummary", index=False)
        workbook = writer.book
        ws = writer.sheets["FinancialSummary"]
        _style_worksheet(ws, workbook, fin_pivot.shape[0] + 1, fin_pivot.shape[1])

    return out_path


def generate_full_dashboard(raw_df: pd.DataFrame, output_path: Union[str, Path] = "warehouse_fin_report.xlsx") -> Path:
    """KPI + FinancialSummary 시트를 포함한 종합 대시보드 생성."""

    dashboard_path = generate_financial_report(raw_df, output_path)

    # KPI 계산
    engine = InventoryEngine(raw_df)
    kpi_df = engine.calculate_monthly_summary()

    with pd.ExcelWriter(dashboard_path, engine="xlsxwriter", mode="a") as writer:
        kpi_df.to_excel(writer, sheet_name="KPI_Summary", index=False)
        workbook = writer.book
        ws = writer.sheets["KPI_Summary"]
        _style_worksheet(ws, workbook, kpi_df.shape[0] + 1, kpi_df.shape[1])

    return Path(dashboard_path)


if __name__ == "__main__":
    import argparse
    from warehouse_loader import load_hvdc_warehouse_file

    parser = argparse.ArgumentParser(description="Generate HVDC Warehouse financial report")
    parser.add_argument("excel", help="Raw HVDC Warehouse Excel file path")
    parser.add_argument("--out", default="warehouse_fin_report.xlsx", help="Output Excel file")
    args = parser.parse_args()

    raw_df = load_hvdc_warehouse_file(args.excel)
    path = generate_full_dashboard(raw_df, args.out)
    print(f"✅ Financial report created: {path}") 