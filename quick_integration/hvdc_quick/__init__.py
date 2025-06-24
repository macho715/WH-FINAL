"""
HVDC Quick Integration Module
============================

빠른 통합을 위한 모듈

사용법:
    import hvdc_quick
    
    # 데이터 처리
    result = hvdc_quick.process_warehouse_data("data.xlsx")
    
    # 보고서 생성
    report = hvdc_quick.generate_report(result, "report.xlsx")
"""

from .core import HVDCProcessor
from .utils import quick_load, quick_report, quick_inventory

__version__ = "0.5.1-quick"
__all__ = ["HVDCProcessor", "quick_load", "quick_report", "quick_inventory"]

# 빠른 사용을 위한 글로벌 함수들
process_warehouse_data = HVDCProcessor().process
generate_report = quick_report
calculate_inventory = quick_inventory
load_data = quick_load
