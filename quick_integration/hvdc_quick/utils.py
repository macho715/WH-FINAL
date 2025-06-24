"""
HVDC 유틸리티 함수들
"""

import pandas as pd
from pathlib import Path
from typing import Union, Dict, Any, Optional
from .core import HVDCProcessor

# 전역 프로세서 인스턴스
_processor = HVDCProcessor()

def quick_load(file_path: Union[str, Path]) -> pd.DataFrame:
    """
    빠른 데이터 로드
    
    Args:
        file_path: Excel 파일 경로
    
    Returns:
        pandas.DataFrame
    """
    result = _processor.process(file_path)
    if result["success"]:
        return result["data"]
    else:
        raise Exception(f"데이터 로드 실패: {result['error']}")

def quick_report(df: pd.DataFrame, output_path: str) -> str:
    """
    빠른 보고서 생성
    
    Args:
        df: 데이터프레임
        output_path: 출력 파일 경로
    
    Returns:
        생성된 파일 경로
    """
    try:
        from excel_reporter import generate_full_dashboard
        report_path = generate_full_dashboard(df, output_path)
        return str(report_path)
    except Exception as e:
        raise Exception(f"보고서 생성 실패: {e}")

def quick_inventory(df: pd.DataFrame) -> Dict[str, Any]:
    """
    빠른 재고 계산
    
    Args:
        df: 데이터프레임
    
    Returns:
        재고 요약 정보
    """
    try:
        from core.inventory_engine import InventoryEngine
        
        engine = InventoryEngine(df)
        monthly_summary = engine.calculate_monthly_summary()
        
        return {
            "total_incoming": monthly_summary["Incoming"].sum(),
            "total_outgoing": monthly_summary["Outgoing"].sum(),
            "end_inventory": monthly_summary["End_Inventory"].iloc[-1],
            "total_amount": monthly_summary["Total_Amount"].sum(),
            "monthly_data": monthly_summary.to_dict("records")
        }
    except Exception as e:
        raise Exception(f"재고 계산 실패: {e}")

def quick_test() -> Dict[str, Any]:
    """통합 테스트"""
    test_results = {
        "processor_init": _processor.is_initialized,
        "modules_available": True,
        "sample_data_test": False,
        "report_generation": False
    }
    
    try:
        # 샘플 데이터 테스트
        sample_data = pd.DataFrame({
            "Incoming": [10, 20, 30],
            "Outgoing": [5, 10, 15],
            "Amount": [1000, 2000, 3000],
            "Category": ["Indoor", "Outdoor", "Indoor"],
            "Billing month": ["2024-01", "2024-01", "2024-02"]
        })
        
        inventory_result = quick_inventory(sample_data)
        test_results["sample_data_test"] = True
        test_results["inventory_total"] = inventory_result["total_amount"]
        
        print("✅ 샘플 데이터 테스트 통과")
        
    except Exception as e:
        test_results["sample_data_error"] = str(e)
        print(f"❌ 샘플 데이터 테스트 실패: {e}")
    
    return test_results

# 편의 함수들
def process_file(file_path: str, generate_report: bool = True) -> Dict[str, Any]:
    """파일 처리 + 보고서 생성 원스톱"""
    result = _processor.process(file_path)
    
    if result["success"] and generate_report:
        output_name = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        try:
            report_path = quick_report(result["data"], output_name)
            result["report_generated"] = report_path
        except Exception as e:
            result["report_error"] = str(e)
    
    return result

def get_status() -> Dict[str, Any]:
    """현재 상태 확인"""
    return {
        "processor_ready": _processor.is_initialized,
        "last_processing": _processor.get_summary(),
        "version": "0.5.1-quick"
    }
