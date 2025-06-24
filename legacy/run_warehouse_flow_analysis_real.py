#!/usr/bin/env python3
"""
실제 데이터로 창고 흐름 분석 실행
===============================

사용자가 요청한 창고와 현장 구분, 입고/출고/재고 흐름 분석을 실제 데이터로 실행합니다.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import json

def load_real_data():
    """실제 데이터 로드 및 전처리"""
    print("🔄 실제 데이터 로드 중...")
    
    # 1. 매핑 규칙 로드
    with open('mapping_rules_v2.6_unified.json', encoding='utf-8') as f:
        mapping_rules = json.load(f)['field_map']
    
    # 2. 실제 데이터 로드
    df_raw = pd.read_excel('data/HVDC WAREHOUSE_HITACHI(HE).xlsx')
    
    # 3. 매핑 적용
    col_map = {k: v for k, v in mapping_rules.items() if k in df_raw.columns}
    df = df_raw.rename(columns=col_map)
    
    # 4. 필요 컬럼 추가
    for needed in mapping_rules.values():
        if needed not in df.columns:
            df[needed] = 0
    
    # 5. 날짜 처리
    if 'ETD/ATD' in df_raw.columns:
        df['hasDate'] = pd.to_datetime(df_raw['ETD/ATD'], errors='coerce')
    elif 'ETA/ATA' in df_raw.columns:
        df['hasDate'] = pd.to_datetime(df_raw['ETA/ATA'], errors='coerce')
    else:
        df['hasDate'] = pd.Timestamp.now()
    
    # 결측값 처리
    df['hasDate'] = df['hasDate'].fillna(pd.Timestamp.now())
    
    # 6. 수치 컬럼 처리
    df['hasAmount_numeric'] = pd.to_numeric(df['hasAmount'], errors='coerce').fillna(0)
    df['hasVolume_numeric'] = pd.to_numeric(df['hasVolume'], errors='coerce').fillna(0)
    
    print(f"✅ 데이터 로드 완료: {df.shape[0]:,}개 레코드, {df.shape[1]}개 컬럼")
    
    return df

def normalize_warehouse_name(name):
    """창고명 정규화 (DAS, Das 통합)"""
    if pd.isna(name) or name == '':
        return ''
    
    name = str(name).strip().upper()
    
    # DAS 정규화 (대소문자 통합)
    if name in ['DAS', 'D.A.S', 'D A S']:
        return 'DAS'
    
    # 기타 창고명 정규화
    warehouse_mapping = {
        'DSV INDOOR': ['DSV INDOOR', 'DSV_INDOOR', 'INDOOR', 'M44'],
        'DSV OUTDOOR': ['DSV OUTDOOR', 'DSV_OUTDOOR', 'OUTDOOR'],
        'DSV AL MARKAZ': ['DSV AL MARKAZ', 'DSV_AL_MARKAZ', 'MARKAZ', 'M1'],
        'MOSB': ['MOSB', 'M.O.S.B', 'M O S B']
    }
    
    for canonical_name, patterns in warehouse_mapping.items():
        for pattern in patterns:
            if pattern in name:
                return canonical_name
    
    # 현장명 패턴 (창고가 아닌 경우)
    site_patterns = ['AGI', 'MIR', 'SHU', 'SITE', 'PROJECT', 'FIELD']
    
    for site_pattern in site_patterns:
        if site_pattern in name:
            return ''  # 현장은 빈 문자열 반환
    
    return name

def classify_location_type(name):
    """위치 타입 분류"""
    if pd.isna(name) or name == '':
        return 'UNKNOWN'
    
    name = str(name).strip().upper()
    
    # 창고 패턴
    if name in ['DAS', 'DSV INDOOR', 'DSV OUTDOOR', 'DSV AL MARKAZ', 'MOSB']:
        return 'WAREHOUSE'
    
    # 현장 패턴
    if name in ['AGI', 'MIR', 'SHU']:
        return 'SITE'
    
    return 'UNKNOWN'

def classify_transaction_type(row):
    """트랜잭션 타입 분류 (입고/출고/이동)"""
    # 수량 기반 추정 (양수=입고, 음수=출고)
    if 'hasVolume_numeric' in row and pd.notna(row['hasVolume_numeric']):
        qty = float(row['hasVolume_numeric'])
        if qty > 0:
            return 'IN'
        elif qty < 0:
            return 'OUT'
    
    # 기본적으로 입고로 가정
    return 'IN'

def create_warehouse_flow_analysis_real(df):
    """실제 데이터로 창고 흐름 분석"""
    print("🔄 창고별 월별 입출고 흐름 분석 시작...")
    
    df_work = df.copy()
    
    # 1. 창고명 정규화 및 분류
    df_work['Warehouse_Normalized'] = df_work['hasSite'].apply(normalize_warehouse_name)
    df_work['Location_Type'] = df_work['hasSite'].apply(classify_location_type)
    
    # 2. 창고만 필터링
    warehouse_df = df_work[
        (df_work['Location_Type'] == 'WAREHOUSE') & 
        (df_work['Warehouse_Normalized'] != '')
    ].copy()
    
    print(f"📊 창고 데이터 필터링 결과: {len(warehouse_df):,}개 레코드")
    
    # 3. 월별 컬럼 생성
    warehouse_df['Month'] = pd.to_datetime(warehouse_df['hasDate']).dt.to_period("M")
    all_months = pd.period_range(warehouse_df['Month'].min(), warehouse_df['Month'].max(), freq='M')
    
    print(f"📅 분석 기간: {all_months[0]} ~ {all_months[-1]} ({len(all_months)}개월)")
    
    # 4. 트랜잭션 타입 분류
    warehouse_df['TxType_Classified'] = warehouse_df.apply(classify_transaction_type, axis=1)
    
    # 5. 입고/출고 수량 분리 (모든 데이터를 입고로 가정)
    warehouse_df['InQty'] = warehouse_df['hasVolume_numeric']
    warehouse_df['OutQty'] = 0  # 출고 데이터가 별도로 없으므로 0으로 설정
    warehouse_df['TransferQty'] = 0
    
    # 6. 월별 집계
    monthly_flow = warehouse_df.groupby(['Warehouse_Normalized', 'Month']).agg({
        'InQty': 'sum',
        'OutQty': 'sum', 
        'TransferQty': 'sum',
        'hasAmount_numeric': 'sum'
    }).round(2)
    
    # 7. 재고 계산 (누적 입고)
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

def create_site_delivery_analysis_real(df):
    """실제 데이터로 현장 배송 분석"""
    print("🔄 현장별 배송 현황 분석 시작...")
    
    df_work = df.copy()
    
    # 1. 현장 분류
    df_work['Location_Type'] = df_work['hasSite'].apply(classify_location_type)
    df_work['Site_Name'] = df_work['hasSite'].apply(
        lambda x: str(x).strip().upper() if classify_location_type(x) == 'SITE' else ''
    )
    
    # 2. 현장만 필터링
    site_df = df_work[
        (df_work['Location_Type'] == 'SITE') & 
        (df_work['Site_Name'] != '')
    ].copy()
    
    print(f"📊 현장 데이터 필터링 결과: {len(site_df):,}개 레코드")
    
    # 3. 월별 집계
    site_df['Month'] = pd.to_datetime(site_df['hasDate']).dt.to_period("M")
    all_months = pd.period_range(site_df['Month'].min(), site_df['Month'].max(), freq='M')
    
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

def save_results_to_excel(warehouse_flow, site_delivery):
    """결과를 Excel 파일로 저장"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    output_path = f"HVDC_실제데이터_창고흐름분석_{timestamp}.xlsx"
    
    print(f"💾 Excel 파일 저장 중: {output_path}")
    
    with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
        # 창고별 흐름 분석
        warehouse_flow.to_excel(writer, sheet_name="창고별_월별_입출고재고", index=False)
        
        # 현장별 배송 분석
        site_delivery.to_excel(writer, sheet_name="현장별_배송현황", index=False)
        
        # 창고 요약 통계
        warehouse_summary = warehouse_flow.groupby('창고명').agg({
            '입고수량': 'sum',
            '출고수량': 'sum',
            '이동수량': 'sum',
            '금액': 'sum',
            '누적재고': 'last'
        }).round(2)
        warehouse_summary.columns = ['총입고', '총출고', '총이동', '총금액', '현재재고']
        warehouse_summary.reset_index().to_excel(writer, sheet_name="창고별_요약통계", index=False)
        
        # 현장 요약 통계
        site_summary = site_delivery.groupby('현장명').agg({
            '배송수량': 'sum',
            '배송횟수': 'sum',
            '배송금액': 'sum'
        }).round(2)
        site_summary.columns = ['총배송수량', '총배송횟수', '총배송금액']
        site_summary.reset_index().to_excel(writer, sheet_name="현장별_요약통계", index=False)
    
    print(f"✅ Excel 파일 저장 완료: {output_path}")
    return output_path

def main():
    """메인 실행 함수"""
    print("🎯 실제 데이터로 창고 흐름 분석 시작")
    print("=" * 80)
    
    start_time = datetime.now()
    
    try:
        # 1. 실제 데이터 로드
        df = load_real_data()
        
        # 2. 창고 흐름 분석
        warehouse_flow = create_warehouse_flow_analysis_real(df)
        
        # 3. 현장 배송 분석
        site_delivery = create_site_delivery_analysis_real(df)
        
        # 4. 결과 저장
        excel_path = save_results_to_excel(warehouse_flow, site_delivery)
        
        # 5. 결과 요약
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        print("\n" + "=" * 80)
        print("🎉 실제 데이터 창고 흐름 분석 완료!")
        print("=" * 80)
        
        print(f"📊 분석 결과:")
        print(f"   • 원본 데이터: {df.shape[0]:,}개 레코드")
        print(f"   • 창고 개수: {warehouse_flow['창고명'].nunique()}개")
        print(f"   • 현장 개수: {site_delivery['현장명'].nunique()}개")
        print(f"   • 분석 기간: {warehouse_flow['월'].nunique()}개월")
        print(f"   • 처리 시간: {processing_time:.2f}초")
        print(f"   • Excel 파일: {excel_path}")
        
        print(f"\n📋 창고별 입출고 현황 (상위 10개):")
        print(warehouse_flow.head(10))
        
        print(f"\n📋 현장별 배송 현황 (상위 10개):")
        print(site_delivery.head(10))
        
        print(f"\n✅ 모든 분석 완료! 🎉")
        
    except Exception as e:
        print(f"\n❌ 분석 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 