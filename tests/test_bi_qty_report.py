"""
HVDC 수량 중심 8시트 BI 함수 단위 테스트
pytest 기반 테스트 모듈

실행 방법:
    pytest tests/test_bi_qty_report.py -v
    pytest tests/test_bi_qty_report.py::test_monthly_dashboard_qty -v
"""

import pandas as pd
import pytest
import sys
import os
from datetime import datetime, timedelta

# 상위 디렉토리의 모듈 import를 위한 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from hvdc_complete_8sheet_reporter import (
        create_monthly_dashboard_qty, create_supplier_report_qty,
        create_warehouse_report_qty, create_site_report_qty,
        create_inbound_weekday_qty, create_outbound_type_qty,
        create_stock_aging_qty, create_invoice_matching_qty,
        create_monthly_dashboard_qty_v2, create_supplier_report_qty_v2,
        create_warehouse_report_qty_v2, create_site_report_qty_v2,
        prepare_monthly_aggregation
    )
except ImportError as e:
    print(f"⚠️ Import 오류: {e}")
    print("hvdc_complete_8sheet_reporter.py 파일이 상위 디렉토리에 있는지 확인하세요.")

@pytest.fixture
def dummy_df():
    """테스트용 더미 DataFrame 생성"""
    # 60일간 샘플 데이터 (Date, Qty, TxType_Refined 등 필수 컬럼)
    base_date = datetime(2024, 1, 1)
    dates = [base_date + timedelta(days=i*15) for i in range(60)]
    
    data = {
        'hasDate': dates,
        'Date': dates,  # 호환성을 위한 중복 컬럼
        'hasVolume_numeric': [10, 20, 15, 5, 7, 8] * 10,  # 수량 데이터
        'Qty': [10, 20, 15, 5, 7, 8] * 10,  # 호환성을 위한 중복 컬럼
        'hasAmount_numeric': [1000, 2000, 1500, 500, 700, 800] * 10,  # 금액 데이터
        'TxType_Refined': ['IN', 'FINAL_OUT', 'TRANSFER_OUT', 'IN', 'FINAL_OUT', 'TRANSFER_OUT'] * 10,
        'hasCurrentStatus': ['IN', 'OUT', 'TRANSFER', 'IN', 'OUT', 'TRANSFER'] * 10,
        'Location': ['WH1', 'WH2', 'WH3', 'WH1', 'WH2', 'WH3'] * 10,
        'hasSite': ['DSV_Indoor', 'DSV_Outdoor', 'DAS', 'DSV_Al_Markaz', 'DSV_Indoor', 'DSV_Outdoor'] * 10,
        'Target_Warehouse': ['SITE1', 'SITE2', 'SITE1', 'SITE3', 'SITE2', 'SITE1'] * 10,
        'Source_File': ['HITACHI_file.xlsx', 'SIMENSE_file.xlsx'] * 30,
        'Case_No': [f"CASE_{i:04d}" for i in range(60)],
        'Shipment No': [f"SHIP_{i:04d}" for i in range(60)]
    }
    return pd.DataFrame(data)

@pytest.fixture
def all_months_fixture(dummy_df):
    """테스트용 전체 월 범위 생성"""
    _, all_months = prepare_monthly_aggregation(dummy_df.copy())
    return all_months

def test_monthly_dashboard_qty(dummy_df, all_months_fixture):
    """월별_전체현황_수량 함수 테스트"""
    print("\n🧪 테스트: create_monthly_dashboard_qty")
    
    try:
        report = create_monthly_dashboard_qty(dummy_df.copy(), all_months_fixture)
        
        # 기본 검증
        assert not report.empty, "리포트가 비어있음"
        assert len(report.index) > 0, "월별 데이터가 없음"
        assert len(report.columns) > 0, "TxType 컬럼이 없음"
        
        # 전체 월 범위 검증
        for month in all_months_fixture:
            assert month in report.index, f"월 {month}이 누락됨"
        
        print(f"✅ 월별 대시보드 테스트 통과 - 형태: {report.shape}")
        
    except Exception as e:
        print(f"❌ 월별 대시보드 테스트 실패: {e}")
        raise

def test_supplier_report_qty(dummy_df, all_months_fixture):
    """공급사별_월별현황_수량 함수 테스트"""
    print("\n🧪 테스트: create_supplier_report_qty")
    
    try:
        report = create_supplier_report_qty(dummy_df.copy(), all_months_fixture)
        
        assert not report.empty, "공급사별 리포트가 비어있음"
        assert len(report.index) > 0, "공급사 데이터가 없음"
        
        # 전체 월 범위 검증
        for month in all_months_fixture:
            assert month in report.columns, f"월 {month}이 누락됨"
        
        print(f"✅ 공급사별 리포트 테스트 통과 - 형태: {report.shape}")
        
    except Exception as e:
        print(f"❌ 공급사별 리포트 테스트 실패: {e}")
        raise

def test_warehouse_report_qty(dummy_df, all_months_fixture):
    """창고별_월별현황_수량 함수 테스트"""
    print("\n🧪 테스트: create_warehouse_report_qty")
    
    try:
        report = create_warehouse_report_qty(dummy_df.copy(), all_months_fixture)
        
        assert not report.empty, "창고별 리포트가 비어있음"
        assert len(report.index) > 0, "창고 데이터가 없음"
        
        print(f"✅ 창고별 리포트 테스트 통과 - 형태: {report.shape}")
        
    except Exception as e:
        print(f"❌ 창고별 리포트 테스트 실패: {e}")
        raise

def test_site_report_qty(dummy_df, all_months_fixture):
    """현장별_월별현황_수량 함수 테스트"""
    print("\n🧪 테스트: create_site_report_qty")
    
    try:
        report, freq = create_site_report_qty(dummy_df.copy(), all_months_fixture)
        
        assert not report.empty, "현장별 리포트가 비어있음"
        assert not freq.empty, "현장별 빈도 리포트가 비어있음"
        
        print(f"✅ 현장별 리포트 테스트 통과 - 형태: {report.shape}, 빈도: {freq.shape}")
        
    except Exception as e:
        print(f"❌ 현장별 리포트 테스트 실패: {e}")
        raise

def test_inbound_weekday_qty(dummy_df, all_months_fixture):
    """입고현황_월별_수량 함수 테스트"""
    print("\n🧪 테스트: create_inbound_weekday_qty")
    
    try:
        report = create_inbound_weekday_qty(dummy_df.copy(), all_months_fixture)
        
        assert not report.empty, "입고 요일별 리포트가 비어있음"
        
        print(f"✅ 입고 요일별 리포트 테스트 통과 - 형태: {report.shape}")
        
    except Exception as e:
        print(f"❌ 입고 요일별 리포트 테스트 실패: {e}")
        raise

def test_outbound_type_qty(dummy_df, all_months_fixture):
    """출고현황_월별_수량 함수 테스트"""
    print("\n🧪 테스트: create_outbound_type_qty")
    
    try:
        report = create_outbound_type_qty(dummy_df.copy(), all_months_fixture)
        
        assert not report.empty, "출고 유형별 리포트가 비어있음"
        
        print(f"✅ 출고 유형별 리포트 테스트 통과 - 형태: {report.shape}")
        
    except Exception as e:
        print(f"❌ 출고 유형별 리포트 테스트 실패: {e}")
        raise

def test_stock_aging_qty(dummy_df, all_months_fixture):
    """재고현황_월별_수량 함수 테스트"""
    print("\n🧪 테스트: create_stock_aging_qty")
    
    try:
        report = create_stock_aging_qty(dummy_df.copy(), all_months_fixture)
        
        assert not report.empty, "재고 Aging 리포트가 비어있음"
        assert 'Mean_Aging' in report.columns, "Mean_Aging 컬럼이 없음"
        
        print(f"✅ 재고 Aging 리포트 테스트 통과 - 형태: {report.shape}")
        
    except Exception as e:
        print(f"❌ 재고 Aging 리포트 테스트 실패: {e}")
        raise

def test_invoice_matching_qty(dummy_df, all_months_fixture):
    """청구매칭_검증_수량 함수 테스트"""
    print("\n🧪 테스트: create_invoice_matching_qty")
    
    try:
        # 임시 송장 데이터 (실제로는 별도 df_invoice 필요)
        df_invoice = dummy_df.copy()
        df_invoice['Shipment No'] = df_invoice['Case_No']
        
        match, match_month = create_invoice_matching_qty(df_invoice, dummy_df.copy(), all_months_fixture)
        
        assert not match.empty, "매칭 결과가 비어있음"
        assert not match_month.empty, "월별 매칭율이 비어있음"
        
        print(f"✅ 청구매칭 검증 테스트 통과 - 매칭: {match.shape}, 월별: {match_month.shape}")
        
    except Exception as e:
        print(f"❌ 청구매칭 검증 테스트 실패: {e}")
        raise

# ===============================================================================
# 개선된 v2 함수들 테스트
# ===============================================================================

def test_monthly_dashboard_qty_v2(dummy_df, all_months_fixture):
    """개선된 월별_전체현황_수량_v2 함수 테스트"""
    print("\n🧪 테스트: create_monthly_dashboard_qty_v2")
    
    try:
        report = create_monthly_dashboard_qty_v2(dummy_df.copy(), all_months_fixture)
        
        assert not report.empty, "v2 월별 대시보드가 비어있음"
        assert len(report.index) > 0, "v2 월별 데이터가 없음"
        
        print(f"✅ v2 월별 대시보드 테스트 통과 - 형태: {report.shape}")
        
    except Exception as e:
        print(f"❌ v2 월별 대시보드 테스트 실패: {e}")
        raise

def test_supplier_report_qty_v2(dummy_df, all_months_fixture):
    """개선된 공급사별_월별현황_수량_v2 함수 테스트"""
    print("\n🧪 테스트: create_supplier_report_qty_v2")
    
    try:
        report = create_supplier_report_qty_v2(dummy_df.copy(), all_months_fixture)
        
        assert not report.empty, "v2 공급사별 리포트가 비어있음"
        
        print(f"✅ v2 공급사별 리포트 테스트 통과 - 형태: {report.shape}")
        
    except Exception as e:
        print(f"❌ v2 공급사별 리포트 테스트 실패: {e}")
        raise

def test_warehouse_report_qty_v2(dummy_df, all_months_fixture):
    """개선된 창고별_월별현황_수량_v2 함수 테스트"""
    print("\n🧪 테스트: create_warehouse_report_qty_v2")
    
    try:
        report = create_warehouse_report_qty_v2(dummy_df.copy(), all_months_fixture)
        
        assert not report.empty, "v2 창고별 리포트가 비어있음"
        
        print(f"✅ v2 창고별 리포트 테스트 통과 - 형태: {report.shape}")
        
    except Exception as e:
        print(f"❌ v2 창고별 리포트 테스트 실패: {e}")
        raise

def test_site_report_qty_v2(dummy_df, all_months_fixture):
    """개선된 현장별_월별현황_수량_v2 함수 테스트"""
    print("\n🧪 테스트: create_site_report_qty_v2")
    
    try:
        report, freq = create_site_report_qty_v2(dummy_df.copy(), all_months_fixture)
        
        assert not report.empty, "v2 현장별 리포트가 비어있음"
        assert not freq.empty, "v2 현장별 빈도가 비어있음"
        
        print(f"✅ v2 현장별 리포트 테스트 통과 - 형태: {report.shape}, 빈도: {freq.shape}")
        
    except Exception as e:
        print(f"❌ v2 현장별 리포트 테스트 실패: {e}")
        raise

# ===============================================================================
# 통합 테스트
# ===============================================================================

def test_full_pipeline_integration(dummy_df):
    """전체 파이프라인 통합 테스트"""
    print("\n🧪 통합 테스트: 전체 파이프라인")
    
    try:
        # 1. 월별 집계 준비
        df_processed, all_months = prepare_monthly_aggregation(dummy_df.copy())
        
        assert not df_processed.empty, "전처리된 DataFrame이 비어있음"
        assert len(all_months) > 0, "전체 월 범위가 비어있음"
        
        # 2. 각 함수 실행 (에러 없이 실행되는지만 확인)
        dashboard = create_monthly_dashboard_qty(df_processed.copy(), all_months)
        supplier = create_supplier_report_qty(df_processed.copy(), all_months)
        warehouse = create_warehouse_report_qty(df_processed.copy(), all_months)
        
        assert not dashboard.empty and not supplier.empty and not warehouse.empty
        
        print("✅ 전체 파이프라인 통합 테스트 통과")
        
    except Exception as e:
        print(f"❌ 전체 파이프라인 통합 테스트 실패: {e}")
        raise

if __name__ == "__main__":
    """직접 실행 시 간단한 테스트"""
    print("🧪 HVDC 수량 중심 8시트 BI 함수 단위 테스트")
    print("=" * 80)
    
    # 더미 데이터로 간단 테스트
    dummy = pd.DataFrame({
        'hasDate': pd.date_range('2024-01-01', periods=10),
        'hasVolume_numeric': range(10),
        'hasSite': ['WH1'] * 10
    })
    
    processed, months = prepare_monthly_aggregation(dummy)
    print(f"📊 테스트 데이터: {processed.shape}, 월 범위: {len(months)}")
    
    print("\n✅ 기본 테스트 완료!")
    print("전체 테스트 실행: pytest tests/test_bi_qty_report.py -v") 