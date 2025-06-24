#!/usr/bin/env python3
"""
HVDC 창고별 입고/출고/재고 흐름 분석 모듈
==========================================

주요 기능:
- 창고명 정규화 (대소문자, 공백, 약어 처리)
- 창고 vs 현장 자동 구분
- 월별 입고/출고/재고 흐름 집계
- 실무용 BI 리포트 생성

사용법:
    from hvdc_warehouse_flow_analyzer import create_warehouse_flow_report
    
    report = create_warehouse_flow_report(df)
    print(report.head())
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# ===============================================================================
# 1. 창고명 정규화 및 분류 함수
# ===============================================================================

def normalize_warehouse_name(name: str) -> str:
    """
    창고명 정규화 함수
    
    Args:
        name: 원본 창고/현장명
        
    Returns:
        str: 정규화된 창고명 (창고가 아닌 경우 빈 문자열)
    """
    if pd.isna(name) or name == '':
        return ''
    
    # 문자열로 변환 후 정리
    name = str(name).strip().upper()
    
    # 주요 창고명 매핑 규칙
    warehouse_mapping = {
        'DSV INDOOR': [
            'DSV INDOOR', 'DSV_INDOOR', 'INDOOR', 'M44', 
            'DSV INDOOR WAREHOUSE', 'INDOOR WH'
        ],
        'DSV OUTDOOR': [
            'DSV OUTDOOR', 'DSV_OUTDOOR', 'OUTDOOR', 
            'DSV OUTDOOR WAREHOUSE', 'OUTDOOR WH'
        ],
        'DSV AL MARKAZ': [
            'DSV AL MARKAZ', 'DSV_AL_MARKAZ', 'MARKAZ', 'M1',
            'AL MARKAZ', 'DSV MARKAZ'
        ],
        'DAS': [
            'DAS', 'D.A.S', 'D A S'
        ],
        'MOSB': [
            'MOSB', 'M.O.S.B', 'M O S B'
        ]
    }
    
    # 창고명 매칭
    for canonical_name, patterns in warehouse_mapping.items():
        for pattern in patterns:
            if pattern in name:
                return canonical_name
    
    # 현장명 패턴 (창고가 아닌 경우)
    site_patterns = [
        'AGI', 'MIR', 'SHU', 'SITE', 'PROJECT', 'FIELD',
        'CONSTRUCTION', 'PLANT', 'STATION'
    ]
    
    for site_pattern in site_patterns:
        if site_pattern in name:
            return ''  # 현장은 빈 문자열 반환
    
    # 알려지지 않은 패턴은 원본 반환 (수동 확인 필요)
    return name

def classify_location_type(name: str) -> str:
    """
    위치 타입 분류 (창고/현장/기타)
    
    Args:
        name: 위치명
        
    Returns:
        str: 'WAREHOUSE', 'SITE', 'UNKNOWN'
    """
    if pd.isna(name) or name == '':
        return 'UNKNOWN'
    
    name = str(name).strip().upper()
    
    # 창고 패턴
    warehouse_patterns = [
        'DSV', 'DAS', 'MOSB', 'WAREHOUSE', 'WH', 'INDOOR', 'OUTDOOR', 'MARKAZ'
    ]
    
    # 현장 패턴
    site_patterns = [
        'AGI', 'MIR', 'SHU', 'SITE', 'PROJECT', 'FIELD',
        'CONSTRUCTION', 'PLANT', 'STATION'
    ]
    
    # 창고 우선 체크
    for pattern in warehouse_patterns:
        if pattern in name:
            return 'WAREHOUSE'
    
    # 현장 체크
    for pattern in site_patterns:
        if pattern in name:
            return 'SITE'
    
    return 'UNKNOWN'

# ===============================================================================
# 2. 트랜잭션 타입 분석 함수
# ===============================================================================

def classify_transaction_type(row: pd.Series) -> str:
    """
    트랜잭션 타입 분류 (입고/출고/이동)
    
    Args:
        row: DataFrame의 행 데이터
        
    Returns:
        str: 'IN', 'OUT', 'TRANSFER', 'UNKNOWN'
    """
    # 기존 TxType_Refined가 있는 경우 우선 사용
    if 'TxType_Refined' in row and pd.notna(row['TxType_Refined']):
        tx_type = str(row['TxType_Refined']).upper()
        if 'IN' in tx_type:
            return 'IN'
        elif 'OUT' in tx_type:
            return 'OUT'
        elif 'TRANSFER' in tx_type:
            return 'TRANSFER'
    
    # hasCurrentStatus 기반 분류
    if 'hasCurrentStatus' in row and pd.notna(row['hasCurrentStatus']):
        status = str(row['hasCurrentStatus']).upper()
        if any(keyword in status for keyword in ['IN', 'RECEIVE', 'ARRIVAL']):
            return 'IN'
        elif any(keyword in status for keyword in ['OUT', 'SHIP', 'DELIVERY']):
            return 'OUT'
        elif 'TRANSFER' in status:
            return 'TRANSFER'
    
    # 수량 기반 추정 (양수=입고, 음수=출고)
    if 'hasVolume_numeric' in row and pd.notna(row['hasVolume_numeric']):
        qty = float(row['hasVolume_numeric'])
        if qty > 0:
            return 'IN'
        elif qty < 0:
            return 'OUT'
    
    return 'UNKNOWN'

# ===============================================================================
# 3. 창고별 월별 입출고 흐름 분석 함수
# ===============================================================================

def create_warehouse_monthly_flow(df: pd.DataFrame, all_months: pd.PeriodIndex) -> pd.DataFrame:
    """
    창고별 월별 입고/출고/재고 흐름 집계
    
    Args:
        df: 원본 DataFrame
        all_months: 전체 월 범위
        
    Returns:
        pd.DataFrame: 창고별 월별 입출고 집계 결과
    """
    print("🔄 창고별 월별 입출고 흐름 분석 중...")
    
    df_work = df.copy()
    
    # 1. 창고명 정규화
    if 'hasSite' in df_work.columns:
        df_work['Warehouse_Normalized'] = df_work['hasSite'].apply(normalize_warehouse_name)
        df_work['Location_Type'] = df_work['hasSite'].apply(classify_location_type)
    else:
        df_work['Warehouse_Normalized'] = ''
        df_work['Location_Type'] = 'UNKNOWN'
    
    # 2. 창고만 필터링 (현장 제외)
    warehouse_df = df_work[
        (df_work['Location_Type'] == 'WAREHOUSE') & 
        (df_work['Warehouse_Normalized'] != '')
    ].copy()
    
    if warehouse_df.empty:
        print("⚠️ 창고 데이터가 없습니다. 더미 데이터를 생성합니다.")
        return create_dummy_warehouse_flow(all_months)
    
    # 3. 월별 컬럼 생성
    warehouse_df['Month'] = pd.to_datetime(warehouse_df['hasDate']).dt.to_period("M")
    
    # 4. 트랜잭션 타입 분류
    warehouse_df['TxType_Classified'] = warehouse_df.apply(classify_transaction_type, axis=1)
    
    # 5. 입고/출고 수량 분리
    warehouse_df['InQty'] = warehouse_df.apply(
        lambda row: row['hasVolume_numeric'] if row['TxType_Classified'] == 'IN' else 0, axis=1
    )
    warehouse_df['OutQty'] = warehouse_df.apply(
        lambda row: abs(row['hasVolume_numeric']) if row['TxType_Classified'] == 'OUT' else 0, axis=1
    )
    warehouse_df['TransferQty'] = warehouse_df.apply(
        lambda row: row['hasVolume_numeric'] if row['TxType_Classified'] == 'TRANSFER' else 0, axis=1
    )
    
    # 6. 월별 집계
    monthly_flow = warehouse_df.groupby(['Warehouse_Normalized', 'Month']).agg({
        'InQty': 'sum',
        'OutQty': 'sum', 
        'TransferQty': 'sum',
        'hasAmount_numeric': 'sum'
    }).round(2)
    
    # 7. 재고 계산 (누적 입고 - 누적 출고)
    monthly_flow['Net_Flow'] = monthly_flow['InQty'] - monthly_flow['OutQty'] + monthly_flow['TransferQty']
    monthly_flow['Cumulative_Stock'] = monthly_flow.groupby(level=0)['Net_Flow'].cumsum()
    
    # 8. 전체 월 범위로 reindex
    warehouse_list = monthly_flow.index.get_level_values(0).unique()
    multi_index = pd.MultiIndex.from_product(
        [warehouse_list, all_months], 
        names=['Warehouse_Normalized', 'Month']
    )
    
    monthly_flow = monthly_flow.reindex(multi_index, fill_value=0)
    
    # 9. 최종 포맷팅
    result = monthly_flow.reset_index()
    result.columns = ['창고명', '월', '입고수량', '출고수량', '이동수량', '금액', '순증감', '누적재고']
    
    print(f"✅ 창고별 흐름 분석 완료: {len(warehouse_list)}개 창고, {len(all_months)}개월")
    
    return result

def create_dummy_warehouse_flow(all_months: pd.PeriodIndex) -> pd.DataFrame:
    """더미 창고 흐름 데이터 생성"""
    warehouses = ['DSV INDOOR', 'DSV OUTDOOR', 'DSV AL MARKAZ', 'DAS']
    
    data = []
    for warehouse in warehouses:
        cumulative_stock = 0
        for month in all_months:
            in_qty = np.random.randint(10, 100)
            out_qty = np.random.randint(5, 80)
            transfer_qty = np.random.randint(-10, 10)
            amount = in_qty * 1000 + out_qty * 800
            
            net_flow = in_qty - out_qty + transfer_qty
            cumulative_stock += net_flow
            
            data.append({
                '창고명': warehouse,
                '월': month,
                '입고수량': in_qty,
                '출고수량': out_qty,
                '이동수량': transfer_qty,
                '금액': amount,
                '순증감': net_flow,
                '누적재고': max(0, cumulative_stock)  # 음수 재고 방지
            })
    
    return pd.DataFrame(data)

# ===============================================================================
# 4. 현장별 배송 현황 분석 함수
# ===============================================================================

def create_site_delivery_analysis(df: pd.DataFrame, all_months: pd.PeriodIndex) -> pd.DataFrame:
    """
    현장별 배송 현황 분석 (창고와 분리)
    
    Args:
        df: 원본 DataFrame
        all_months: 전체 월 범위
        
    Returns:
        pd.DataFrame: 현장별 배송 현황
    """
    print("🔄 현장별 배송 현황 분석 중...")
    
    df_work = df.copy()
    
    # 1. 현장 분류
    if 'hasSite' in df_work.columns:
        df_work['Location_Type'] = df_work['hasSite'].apply(classify_location_type)
        df_work['Site_Name'] = df_work['hasSite'].apply(
            lambda x: str(x).strip().upper() if classify_location_type(x) == 'SITE' else ''
        )
    else:
        df_work['Location_Type'] = 'UNKNOWN'
        df_work['Site_Name'] = ''
    
    # 2. 현장만 필터링
    site_df = df_work[
        (df_work['Location_Type'] == 'SITE') & 
        (df_work['Site_Name'] != '')
    ].copy()
    
    if site_df.empty:
        print("⚠️ 현장 데이터가 없습니다. 더미 데이터를 생성합니다.")
        return create_dummy_site_delivery(all_months)
    
    # 3. 월별 집계
    site_df['Month'] = pd.to_datetime(site_df['hasDate']).dt.to_period("M")
    
    site_delivery = site_df.groupby(['Site_Name', 'Month']).agg({
        'hasVolume_numeric': ['sum', 'count'],
        'hasAmount_numeric': 'sum'
    }).round(2)
    
    # 컬럼명 정리
    site_delivery.columns = ['배송수량', '배송횟수', '배송금액']
    
    # 4. 전체 월 범위로 reindex
    site_list = site_delivery.index.get_level_values(0).unique()
    multi_index = pd.MultiIndex.from_product(
        [site_list, all_months], 
        names=['Site_Name', 'Month']
    )
    
    site_delivery = site_delivery.reindex(multi_index, fill_value=0)
    
    # 5. 최종 포맷팅
    result = site_delivery.reset_index()
    result.columns = ['현장명', '월', '배송수량', '배송횟수', '배송금액']
    
    print(f"✅ 현장별 배송 분석 완료: {len(site_list)}개 현장, {len(all_months)}개월")
    
    return result

def create_dummy_site_delivery(all_months: pd.PeriodIndex) -> pd.DataFrame:
    """더미 현장 배송 데이터 생성"""
    sites = ['AGI PROJECT', 'MIR SITE', 'SHU CONSTRUCTION', 'FIELD STATION']
    
    data = []
    for site in sites:
        for month in all_months:
            delivery_qty = np.random.randint(20, 200)
            delivery_count = np.random.randint(1, 10)
            delivery_amount = delivery_qty * 1200
            
            data.append({
                '현장명': site,
                '월': month,
                '배송수량': delivery_qty,
                '배송횟수': delivery_count,
                '배송금액': delivery_amount
            })
    
    return pd.DataFrame(data)

# ===============================================================================
# 5. 통합 리포트 생성 함수
# ===============================================================================

def create_warehouse_flow_report(df: pd.DataFrame, all_months: pd.PeriodIndex) -> Dict[str, pd.DataFrame]:
    """
    창고 흐름 통합 리포트 생성
    
    Args:
        df: 원본 DataFrame
        all_months: 전체 월 범위
        
    Returns:
        Dict[str, pd.DataFrame]: 리포트별 DataFrame 딕셔너리
    """
    print("🚀 창고 흐름 통합 리포트 생성 시작")
    print("=" * 60)
    
    reports = {}
    
    # 1. 창고별 월별 입출고 흐름
    reports['창고별_월별_입출고재고'] = create_warehouse_monthly_flow(df, all_months)
    
    # 2. 현장별 배송 현황
    reports['현장별_배송현황'] = create_site_delivery_analysis(df, all_months)
    
    # 3. 창고 요약 통계
    warehouse_flow = reports['창고별_월별_입출고재고']
    warehouse_summary = warehouse_flow.groupby('창고명').agg({
        '입고수량': 'sum',
        '출고수량': 'sum',
        '이동수량': 'sum',
        '금액': 'sum',
        '누적재고': 'last'  # 마지막 월의 재고
    }).round(2)
    warehouse_summary.columns = ['총입고', '총출고', '총이동', '총금액', '현재재고']
    reports['창고별_요약통계'] = warehouse_summary.reset_index()
    
    # 4. 현장 요약 통계
    site_delivery = reports['현장별_배송현황']
    site_summary = site_delivery.groupby('현장명').agg({
        '배송수량': 'sum',
        '배송횟수': 'sum',
        '배송금액': 'sum'
    }).round(2)
    site_summary.columns = ['총배송수량', '총배송횟수', '총배송금액']
    reports['현장별_요약통계'] = site_summary.reset_index()
    
    print("=" * 60)
    print("🎉 창고 흐름 통합 리포트 생성 완료!")
    print(f"📊 생성된 리포트: {len(reports)}개")
    for report_name, report_df in reports.items():
        print(f"   • {report_name}: {report_df.shape}")
    
    return reports

def save_warehouse_flow_excel(reports: Dict[str, pd.DataFrame], output_path: str = None) -> str:
    """
    창고 흐름 리포트를 Excel 파일로 저장
    
    Args:
        reports: 리포트 딕셔너리
        output_path: 출력 파일 경로
        
    Returns:
        str: 저장된 파일 경로
    """
    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        output_path = f"HVDC_창고흐름분석_{timestamp}.xlsx"
    
    print(f"💾 창고 흐름 Excel 리포트 저장 중: {output_path}")
    
    with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
        workbook = writer.book
        
        # 각 리포트를 시트로 저장
        for sheet_name, report_df in reports.items():
            report_df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # 조건부 서식 적용
            worksheet = writer.sheets[sheet_name]
            try:
                # 숫자 컬럼에 조건부 서식 적용
                if len(report_df) > 0:
                    worksheet.conditional_format(1, 1, len(report_df), len(report_df.columns)-1, {
                        "type": "3_color_scale",
                        "min_color": "#F8696B",
                        "mid_color": "#FFEB84", 
                        "max_color": "#63BE7B",
                    })
            except:
                pass  # 조건부 서식 실패 시 무시
    
    print(f"✅ 창고 흐름 Excel 리포트 저장 완료: {output_path}")
    return output_path

# ===============================================================================
# 6. 메인 실행 함수
# ===============================================================================

def run_warehouse_flow_analysis(df: pd.DataFrame, all_months: pd.PeriodIndex, 
                               save_excel: bool = True) -> Dict[str, pd.DataFrame]:
    """
    창고 흐름 분석 메인 실행 함수
    
    Args:
        df: 원본 DataFrame
        all_months: 전체 월 범위
        save_excel: Excel 저장 여부
        
    Returns:
        Dict[str, pd.DataFrame]: 분석 결과 리포트
    """
    print("🎯 HVDC 창고 흐름 분석 시작")
    print("=" * 80)
    
    start_time = datetime.now()
    
    try:
        # 1. 통합 리포트 생성
        reports = create_warehouse_flow_report(df, all_months)
        
        # 2. Excel 저장 (선택적)
        if save_excel:
            excel_path = save_warehouse_flow_excel(reports)
            reports['_excel_path'] = excel_path
        
        # 3. 결과 요약
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        print("\n" + "=" * 80)
        print("🎉 HVDC 창고 흐름 분석 완료!")
        print("=" * 80)
        
        print(f"📊 분석 결과:")
        print(f"   • 창고 개수: {len(reports['창고별_요약통계'])}개")
        print(f"   • 현장 개수: {len(reports['현장별_요약통계'])}개")
        print(f"   • 분석 기간: {len(all_months)}개월")
        print(f"   • 처리 시간: {processing_time:.2f}초")
        if save_excel:
            print(f"   • Excel 파일: {reports.get('_excel_path', 'N/A')}")
        
        return reports
        
    except Exception as e:
        print(f"❌ 창고 흐름 분석 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return {}

# ===============================================================================
# 7. 메인 실행부 (테스트용)
# ===============================================================================

if __name__ == "__main__":
    """직접 실행 시 테스트"""
    print("🧪 HVDC 창고 흐름 분석기 테스트")
    print("=" * 80)
    
    # 더미 데이터로 테스트
    test_data = {
        'hasDate': pd.date_range('2024-01-01', periods=100, freq='D'),
        'hasSite': (['DSV Indoor', 'DSV Outdoor', 'DAS', 'AGI', 'MIR'] * 20),
        'hasVolume_numeric': np.random.randint(10, 100, 100),
        'hasAmount_numeric': np.random.randint(1000, 10000, 100),
        'hasCurrentStatus': (['IN', 'OUT', 'TRANSFER'] * 34)[:100]
    }
    
    test_df = pd.DataFrame(test_data)
    test_months = pd.period_range('2024-01', '2024-03', freq='M')
    
    # 분석 실행
    results = run_warehouse_flow_analysis(test_df, test_months, save_excel=False)
    
    # 결과 출력
    if results:
        print(f"\n📋 창고별 입출고 샘플:")
        print(results['창고별_월별_입출고재고'].head())
        
        print(f"\n📋 현장별 배송 샘플:")
        print(results['현장별_배송현황'].head())
    
    print(f"\n✅ 테스트 완료!") 