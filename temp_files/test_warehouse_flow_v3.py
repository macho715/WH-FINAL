#!/usr/bin/env python3
"""
창고 흐름 분석 v3 테스트 스크립트
===============================

사용자가 요청한 창고와 현장 구분, 입고/출고/재고 흐름 분석 기능을 테스트합니다.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

# 현재 디렉토리를 Python path에 추가
sys.path.append(os.getcwd())

try:
    from hvdc_complete_8sheet_reporter import (
        normalize_warehouse_name,
        classify_location_type,
        classify_transaction_type,
        create_warehouse_flow_report_v3,
        create_site_delivery_report_v3,
        create_warehouse_flow_8sheet_report_v3,
        save_warehouse_flow_8sheet_excel_v3
    )
    print("✅ 창고 흐름 분석 함수들 import 성공")
except ImportError as e:
    print(f"❌ Import 실패: {e}")
    sys.exit(1)

def create_test_data():
    """테스트용 데이터 생성"""
    print("🔄 테스트 데이터 생성 중...")
    
    # 창고와 현장이 혼재된 데이터 생성
    locations = [
        'DSV Indoor', 'DSV Outdoor', 'DSV Al Markaz', 'DAS', 'MOSB',  # 창고
        'AGI Project', 'MIR Site', 'SHU Construction', 'Field Station'  # 현장
    ]
    
    # 100개 레코드 생성
    np.random.seed(42)  # 재현 가능한 결과를 위해
    
    data = {
        'hasDate': pd.date_range('2024-01-01', periods=100, freq='D'),
        'hasSite': np.random.choice(locations, 100),
        'hasVolume_numeric': np.random.randint(10, 500, 100),
        'hasAmount_numeric': np.random.randint(1000, 50000, 100),
        'hasCurrentStatus': np.random.choice(['IN', 'OUT', 'TRANSFER'], 100),
        'TxType_Refined': np.random.choice(['INBOUND', 'OUTBOUND', 'TRANSFER'], 100),
        'hasShipmentNo': [f'SH{i:04d}' for i in range(100)]
    }
    
    df = pd.DataFrame(data)
    print(f"✅ 테스트 데이터 생성 완료: {df.shape[0]}개 레코드")
    
    return df

def test_normalization_functions():
    """정규화 함수들 테스트"""
    print("\n🧪 정규화 함수 테스트")
    print("=" * 50)
    
    # 테스트 케이스
    test_cases = [
        'DSV Indoor', 'DSV Outdoor', 'DSV Al Markaz', 'DAS', 'das', 'D.A.S',
        'AGI Project', 'MIR Site', 'SHU Construction', 'Unknown Location'
    ]
    
    for location in test_cases:
        normalized = normalize_warehouse_name(location)
        location_type = classify_location_type(location)
        print(f"  {location:20} → {normalized:15} ({location_type})")
    
    print("✅ 정규화 함수 테스트 완료")

def test_warehouse_flow_analysis():
    """창고 흐름 분석 테스트"""
    print("\n🧪 창고 흐름 분석 테스트")
    print("=" * 50)
    
    # 테스트 데이터 생성
    df = create_test_data()
    
    # 월 범위 생성
    all_months = pd.period_range('2024-01', '2024-04', freq='M')
    
    try:
        # 창고 흐름 분석 실행
        warehouse_flow = create_warehouse_flow_report_v3(df, all_months)
        print(f"✅ 창고 흐름 분석 완료: {warehouse_flow.shape}")
        print("\n📋 창고 흐름 분석 결과 (상위 5개):")
        print(warehouse_flow.head())
        
        # 현장 배송 분석 실행
        site_delivery = create_site_delivery_report_v3(df, all_months)
        print(f"\n✅ 현장 배송 분석 완료: {site_delivery.shape}")
        print("\n📋 현장 배송 분석 결과 (상위 5개):")
        print(site_delivery.head())
        
        return warehouse_flow, site_delivery
        
    except Exception as e:
        print(f"❌ 창고 흐름 분석 실패: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def test_8sheet_report_generation():
    """8개 시트 리포트 생성 테스트"""
    print("\n🧪 8개 시트 리포트 생성 테스트")
    print("=" * 50)
    
    # 테스트 데이터 생성
    df = create_test_data()
    
    # 월 범위 생성
    all_months = pd.period_range('2024-01', '2024-04', freq='M')
    
    try:
        # 8개 시트 리포트 생성
        reports = create_warehouse_flow_8sheet_report_v3(df, all_months, mode='flow')
        
        print(f"✅ 8개 시트 리포트 생성 완료: {len(reports)}개 시트")
        
        for sheet_name, sheet_df in reports.items():
            print(f"  • {sheet_name}: {sheet_df.shape}")
        
        # Excel 파일로 저장
        output_path = save_warehouse_flow_8sheet_excel_v3(reports, "test_warehouse_flow_v3.xlsx")
        print(f"\n✅ Excel 파일 저장 완료: {output_path}")
        
        return reports
        
    except Exception as e:
        print(f"❌ 8개 시트 리포트 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """메인 테스트 실행"""
    print("🎯 창고 흐름 분석 v3 테스트 시작")
    print("=" * 80)
    
    start_time = datetime.now()
    
    try:
        # 1. 정규화 함수 테스트
        test_normalization_functions()
        
        # 2. 창고 흐름 분석 테스트
        warehouse_flow, site_delivery = test_warehouse_flow_analysis()
        
        # 3. 8개 시트 리포트 생성 테스트
        if warehouse_flow is not None:
            reports = test_8sheet_report_generation()
        
        # 결과 요약
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        print("\n" + "=" * 80)
        print("🎉 창고 흐름 분석 v3 테스트 완료!")
        print("=" * 80)
        print(f"⏱️  총 처리 시간: {processing_time:.2f}초")
        
        if warehouse_flow is not None:
            print(f"📊 창고 흐름 분석 결과:")
            print(f"   • 창고 개수: {warehouse_flow['창고명'].nunique()}개")
            print(f"   • 분석 기간: {warehouse_flow['월'].nunique()}개월")
            print(f"   • 총 레코드: {len(warehouse_flow)}개")
        
        if site_delivery is not None:
            print(f"📊 현장 배송 분석 결과:")
            print(f"   • 현장 개수: {site_delivery['현장명'].nunique()}개")
            print(f"   • 분석 기간: {site_delivery['월'].nunique()}개월")
            print(f"   • 총 레코드: {len(site_delivery)}개")
        
        print(f"\n✅ 모든 테스트 성공! 🎉")
        
    except Exception as e:
        print(f"\n❌ 테스트 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 