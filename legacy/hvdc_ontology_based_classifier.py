#!/usr/bin/env python3
"""
HVDC 온톨로지 기준 완전 자동화 분류 시스템
==========================================

온톨로지에서 명시적으로 정의된 그룹 기준으로만 분류하여
패턴 매칭, 대소문자, 오타 등의 오류를 완전히 차단합니다.

사용법:
    from hvdc_ontology_based_classifier import get_location_group, create_ontology_warehouse_flow
    
    df['LocationGroup'] = df['hasLocation'].apply(get_location_group)
    warehouse_flow = create_ontology_warehouse_flow(df)
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import json

# ===============================================================================
# 1. 온톨로지 기준 완전 자동화 분류 딕셔너리
# ===============================================================================

# 온톨로지에서 명시적으로 정의된 그룹
INDOOR_WAREHOUSE = ["DSV Indoor", "DSV Al Markaz", "Hauler Indoor"]
OUTDOOR_WAREHOUSE = ["DSV Outdoor", "DSV MZP", "MOSB"]
SITE = ["AGI", "DAS", "MIR", "SHU"]
DANGEROUS_CARGO = ["AAA Storage", "Dangerous Storage"]

def get_location_group(name):
    """
    온톨로지 기준 위치 그룹 분류 (100% 명시적 매칭)
    
    Args:
        name: 위치명 (온톨로지 매핑 기준)
        
    Returns:
        str: 'IndoorWarehouse', 'OutdoorWarehouse', 'Site', 'DangerousCargoWarehouse', 'UNKNOWN'
    """
    if pd.isna(name):
        return "UNKNOWN"
    
    # 정확한 문자열 매칭만 수행 (패턴 매칭 금지)
    n = str(name).strip()
    
    if n in INDOOR_WAREHOUSE:
        return "IndoorWarehouse"
    elif n in OUTDOOR_WAREHOUSE:
        return "OutdoorWarehouse"
    elif n in SITE:
        return "Site"
    elif n in DANGEROUS_CARGO:
        return "DangerousCargoWarehouse"
    else:
        return "UNKNOWN"

def get_warehouse_locations():
    """모든 창고 위치 리스트 반환"""
    return INDOOR_WAREHOUSE + OUTDOOR_WAREHOUSE + DANGEROUS_CARGO

def get_site_locations():
    """모든 현장 위치 리스트 반환"""
    return SITE

def get_all_known_locations():
    """모든 알려진 위치 리스트 반환"""
    return INDOOR_WAREHOUSE + OUTDOOR_WAREHOUSE + SITE + DANGEROUS_CARGO

def validate_location_data(df, location_column='hasSite'):
    """
    위치 데이터 검증 및 분석
    
    Args:
        df: DataFrame
        location_column: 위치 컬럼명
        
    Returns:
        dict: 검증 결과
    """
    print("🔍 온톨로지 기준 위치 데이터 검증 중...")
    
    if location_column not in df.columns:
        return {"error": f"컬럼 '{location_column}'이 존재하지 않습니다."}
    
    # 위치 그룹 분류
    df_temp = df.copy()
    df_temp['LocationGroup'] = df_temp[location_column].apply(get_location_group)
    
    # 분석 결과
    location_counts = df_temp[location_column].value_counts()
    group_counts = df_temp['LocationGroup'].value_counts()
    
    # 알려지지 않은 위치들
    unknown_locations = df_temp[df_temp['LocationGroup'] == 'UNKNOWN'][location_column].value_counts()
    
    result = {
        "total_records": len(df_temp),
        "unique_locations": len(location_counts),
        "location_distribution": location_counts.to_dict(),
        "group_distribution": group_counts.to_dict(),
        "unknown_locations": unknown_locations.to_dict(),
        "validation_summary": {
            "indoor_warehouse": len(df_temp[df_temp['LocationGroup'] == 'IndoorWarehouse']),
            "outdoor_warehouse": len(df_temp[df_temp['LocationGroup'] == 'OutdoorWarehouse']),
            "site": len(df_temp[df_temp['LocationGroup'] == 'Site']),
            "dangerous_cargo": len(df_temp[df_temp['LocationGroup'] == 'DangerousCargoWarehouse']),
            "unknown": len(df_temp[df_temp['LocationGroup'] == 'UNKNOWN'])
        }
    }
    
    print("✅ 위치 데이터 검증 완료")
    print(f"📊 그룹별 분포: {result['group_distribution']}")
    
    if unknown_locations.any():
        print(f"⚠️ 알려지지 않은 위치 {len(unknown_locations)}개 발견:")
        print(unknown_locations.head())
    
    return result

# ===============================================================================
# 2. 온톨로지 기준 트랜잭션 타입 분류
# ===============================================================================

def classify_transaction_type_ontology(row):
    """
    온톨로지 기준 트랜잭션 타입 분류
    
    Args:
        row: DataFrame의 행 데이터
        
    Returns:
        str: 'IN', 'OUT', 'TRANSFER', 'UNKNOWN'
    """
    # hasTransactionType 컬럼이 있는 경우 우선 사용
    if 'hasTransactionType' in row and pd.notna(row['hasTransactionType']):
        tx_type = str(row['hasTransactionType']).upper().strip()
        if tx_type == 'IN' or 'INBOUND' in tx_type:
            return 'IN'
        elif tx_type == 'OUT' or 'OUTBOUND' in tx_type:
            return 'OUT'
        elif 'TRANSFER' in tx_type:
            return 'TRANSFER'
    
    # hasCurrentStatus 기반 분류
    if 'hasCurrentStatus' in row and pd.notna(row['hasCurrentStatus']):
        status = str(row['hasCurrentStatus']).upper().strip()
        if any(keyword in status for keyword in ['IN', 'RECEIVE', 'ARRIVAL', 'INBOUND']):
            return 'IN'
        elif any(keyword in status for keyword in ['OUT', 'SHIP', 'DELIVERY', 'OUTBOUND']):
            return 'OUT'
        elif 'TRANSFER' in status:
            return 'TRANSFER'
    
    # 수량 기반 추정 (양수=입고, 음수=출고)
    quantity_cols = ['hasQuantity', 'hasVolume_numeric', 'hasVolume']
    for col in quantity_cols:
        if col in row and pd.notna(row[col]):
            try:
                qty = float(row[col])
                if qty > 0:
                    return 'IN'
                elif qty < 0:
                    return 'OUT'
            except (ValueError, TypeError):
                continue
    
    # 기본값: 입고로 가정
    return 'IN'

# ===============================================================================
# 3. 온톨로지 기준 창고 흐름 분석 함수
# ===============================================================================

def create_ontology_warehouse_flow(df, location_column='hasSite'):
    """온톨로지 기준 창고별 월별 입고/출고/재고 흐름 분석"""
    print("🔄 온톨로지 기준 창고별 월별 입출고 흐름 분석 시작...")
    
    df_work = df.copy()
    
    # 1. 온톨로지 기준 위치 그룹 분류
    df_work['LocationGroup'] = df_work[location_column].apply(get_location_group)
    
    # 2. 창고만 필터링 (현장 제외)
    warehouse_groups = ['IndoorWarehouse', 'OutdoorWarehouse', 'DangerousCargoWarehouse']
    warehouse_df = df_work[df_work['LocationGroup'].isin(warehouse_groups)].copy()
    
    if warehouse_df.empty:
        print("⚠️ 창고 데이터가 없습니다.")
        return pd.DataFrame()
    
    print(f"📊 창고 데이터 필터링 결과: {len(warehouse_df):,}개 레코드")
    
    # 3. 월별 컬럼 생성
    warehouse_df['Month'] = pd.to_datetime(warehouse_df['hasDate']).dt.to_period("M")
    all_months = pd.period_range(warehouse_df['Month'].min(), warehouse_df['Month'].max(), freq='M')
    
    print(f"📅 분석 기간: {all_months[0]} ~ {all_months[-1]} ({len(all_months)}개월)")
    
    # 4. 입고/출고 수량 분리 (모든 데이터를 입고로 가정)
    quantity_col = 'hasVolume_numeric' if 'hasVolume_numeric' in warehouse_df.columns else 'hasVolume'
    if quantity_col not in warehouse_df.columns:
        warehouse_df[quantity_col] = 0
    
    warehouse_df['InQty'] = warehouse_df[quantity_col]
    warehouse_df['OutQty'] = 0  # 출고 데이터가 별도로 없으므로 0으로 설정
    warehouse_df['TransferQty'] = 0
    
    # 5. 월별 집계
    amount_col = 'hasAmount_numeric' if 'hasAmount_numeric' in warehouse_df.columns else 'hasAmount'
    if amount_col not in warehouse_df.columns:
        warehouse_df[amount_col] = 0
    
    monthly_flow = warehouse_df.groupby([location_column, 'LocationGroup', 'Month']).agg({
        'InQty': 'sum',
        'OutQty': 'sum', 
        'TransferQty': 'sum',
        amount_col: 'sum'
    }).round(2)
    
    # 6. 재고 계산 (누적 입고)
    monthly_flow['Net_Flow'] = monthly_flow['InQty'] - monthly_flow['OutQty'] + monthly_flow['TransferQty']
    monthly_flow['Cumulative_Stock'] = monthly_flow.groupby(level=[0, 1])['Net_Flow'].cumsum()
    
    # 7. 전체 월 범위로 reindex
    warehouse_list = monthly_flow.index.get_level_values(0).unique()
    group_list = monthly_flow.index.get_level_values(1).unique()
    
    # 위치별 그룹 매핑 생성
    location_group_map = warehouse_df.drop_duplicates([location_column, 'LocationGroup']).set_index(location_column)['LocationGroup'].to_dict()
    
    multi_index_data = []
    for location in warehouse_list:
        group = location_group_map[location]
        for month in all_months:
            multi_index_data.append((location, group, month))
    
    multi_index = pd.MultiIndex.from_tuples(
        multi_index_data, 
        names=[location_column, 'LocationGroup', 'Month']
    )
    
    monthly_flow = monthly_flow.reindex(multi_index, fill_value=0)
    
    # 8. 최종 포맷팅
    result = monthly_flow.reset_index()
    result.columns = ['위치명', '위치그룹', '월', '입고수량', '출고수량', '이동수량', '금액', '순증감', '누적재고']
    
    print(f"✅ 온톨로지 기준 창고별 흐름 분석 완료: {len(warehouse_list)}개 창고, {len(all_months)}개월")
    
    return result

def create_ontology_site_delivery(df, location_column='hasSite'):
    """온톨로지 기준 현장별 배송 현황 분석"""
    print("🔄 온톨로지 기준 현장별 배송 현황 분석 시작...")
    
    df_work = df.copy()
    
    # 1. 온톨로지 기준 위치 그룹 분류
    df_work['LocationGroup'] = df_work[location_column].apply(get_location_group)
    
    # 2. 현장만 필터링
    site_df = df_work[df_work['LocationGroup'] == 'Site'].copy()
    
    if site_df.empty:
        print("⚠️ 현장 데이터가 없습니다.")
        return pd.DataFrame()
    
    print(f"📊 현장 데이터 필터링 결과: {len(site_df):,}개 레코드")
    
    # 3. 월별 집계
    site_df['Month'] = pd.to_datetime(site_df['hasDate']).dt.to_period("M")
    all_months = pd.period_range(site_df['Month'].min(), site_df['Month'].max(), freq='M')
    
    quantity_col = 'hasVolume_numeric' if 'hasVolume_numeric' in site_df.columns else 'hasVolume'
    amount_col = 'hasAmount_numeric' if 'hasAmount_numeric' in site_df.columns else 'hasAmount'
    
    if quantity_col not in site_df.columns:
        site_df[quantity_col] = 0
    if amount_col not in site_df.columns:
        site_df[amount_col] = 0
    
    site_delivery = site_df.groupby([location_column, 'Month']).agg({
        quantity_col: ['sum', 'count'],
        amount_col: 'sum'
    }).round(2)
    
    # 컬럼명 정리
    site_delivery.columns = ['배송수량', '배송횟수', '배송금액']
    
    # 4. 전체 월 범위로 reindex
    site_list = site_delivery.index.get_level_values(0).unique()
    multi_index = pd.MultiIndex.from_product(
        [site_list, all_months], 
        names=[location_column, 'Month']
    )
    
    site_delivery = site_delivery.reindex(multi_index, fill_value=0)
    
    # 5. 최종 포맷팅
    result = site_delivery.reset_index()
    result.columns = ['현장명', '월', '배송수량', '배송횟수', '배송금액']
    
    print(f"✅ 온톨로지 기준 현장별 배송 분석 완료: {len(site_list)}개 현장, {len(all_months)}개월")
    
    return result

# ===============================================================================
# 4. 온톨로지 기준 통합 리포트 생성
# ===============================================================================

def create_ontology_based_reports(df, location_column='hasSite', date_column='hasDate'):
    """
    온톨로지 기준 통합 리포트 생성
    
    Args:
        df: 원본 DataFrame
        location_column: 위치 컬럼명
        date_column: 날짜 컬럼명
        
    Returns:
        Dict[str, pd.DataFrame]: 리포트별 DataFrame 딕셔너리
    """
    print("🚀 온톨로지 기준 통합 리포트 생성 시작")
    print("=" * 80)
    
    # 1. 위치 데이터 검증
    validation_result = validate_location_data(df, location_column)
    
    reports = {}
    
    # 2. 창고별 월별 입출고 흐름
    warehouse_flow = create_ontology_warehouse_flow(df, location_column)
    if not warehouse_flow.empty:
        reports['창고별_월별_입출고재고'] = warehouse_flow
    
    # 3. 현장별 배송 현황
    site_delivery = create_ontology_site_delivery(df, location_column)
    if not site_delivery.empty:
        reports['현장별_배송현황'] = site_delivery
    
    # 4. 위치 그룹별 요약 통계
    if not warehouse_flow.empty:
        warehouse_summary = warehouse_flow.groupby(['위치명', '위치그룹']).agg({
            '입고수량': 'sum',
            '출고수량': 'sum',
            '이동수량': 'sum',
            '금액': 'sum',
            '누적재고': 'last'
        }).round(2)
        warehouse_summary.columns = ['총입고', '총출고', '총이동', '총금액', '현재재고']
        reports['창고별_요약통계'] = warehouse_summary.reset_index()
    
    if not site_delivery.empty:
        site_summary = site_delivery.groupby('현장명').agg({
            '배송수량': 'sum',
            '배송횟수': 'sum',
            '배송금액': 'sum'
        }).round(2)
        site_summary.columns = ['총배송수량', '총배송횟수', '총배송금액']
        reports['현장별_요약통계'] = site_summary.reset_index()
    
    # 5. 온톨로지 분류 결과
    reports['온톨로지_분류결과'] = pd.DataFrame([
        {"분류": "Indoor Warehouse", "위치": ", ".join(INDOOR_WAREHOUSE)},
        {"분류": "Outdoor Warehouse", "위치": ", ".join(OUTDOOR_WAREHOUSE)},
        {"분류": "Site", "위치": ", ".join(SITE)},
        {"분류": "Dangerous Cargo", "위치": ", ".join(DANGEROUS_CARGO)}
    ])
    
    print("=" * 80)
    print("🎉 온톨로지 기준 통합 리포트 생성 완료!")
    print(f"📊 생성된 리포트: {len(reports)}개")
    for report_name, report_df in reports.items():
        print(f"   • {report_name}: {report_df.shape}")
    
    return reports

def save_ontology_reports_excel(reports, output_path=None):
    """
    온톨로지 기준 리포트를 Excel 파일로 저장
    
    Args:
        reports: 리포트 딕셔너리
        output_path: 출력 파일 경로
        
    Returns:
        str: 저장된 파일 경로
    """
    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        output_path = f"HVDC_온톨로지기준_창고흐름분석_{timestamp}.xlsx"
    
    print(f"💾 온톨로지 기준 Excel 리포트 저장 중: {output_path}")
    
    with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
        workbook = writer.book
        
        # 각 리포트를 시트로 저장
        for sheet_name, report_df in reports.items():
            # 시트명 길이 제한 (Excel 31자 제한)
            safe_sheet_name = sheet_name[:31] if len(sheet_name) > 31 else sheet_name
            
            report_df.to_excel(writer, sheet_name=safe_sheet_name, index=False)
            
            # 조건부 서식 적용
            worksheet = writer.sheets[safe_sheet_name]
            try:
                if len(report_df) > 0:
                    # 숫자 컬럼에만 조건부 서식 적용
                    numeric_cols = report_df.select_dtypes(include=[np.number]).columns
                    if len(numeric_cols) > 0:
                        worksheet.conditional_format(1, 1, len(report_df), len(report_df.columns)-1, {
                            "type": "3_color_scale",
                            "min_color": "#F8696B",
                            "mid_color": "#FFEB84", 
                            "max_color": "#63BE7B",
                        })
            except Exception as e:
                print(f"⚠️ 조건부 서식 적용 실패 ({safe_sheet_name}): {e}")
    
    print(f"✅ 온톨로지 기준 Excel 리포트 저장 완료: {output_path}")
    return output_path

# ===============================================================================
# 5. 메인 실행 함수
# ===============================================================================

def run_ontology_based_analysis(excel_path=None, mapping_rules_path=None, location_column='hasSite', date_column='hasDate'):
    """
    온톨로지 기준 창고 흐름 분석 메인 실행 함수
    
    Args:
        excel_path: Excel 파일 경로
        mapping_rules_path: 매핑 규칙 파일 경로
        location_column: 위치 컬럼명
        date_column: 날짜 컬럼명
        
    Returns:
        Dict[str, pd.DataFrame]: 분석 결과 리포트
    """
    print("🎯 온톨로지 기준 HVDC 창고 흐름 분석 시작")
    print("=" * 80)
    
    start_time = datetime.now()
    
    try:
        # 1. 데이터 로드
        if excel_path is None:
            excel_path = "data/HVDC WAREHOUSE_HITACHI(HE).xlsx"
        
        print(f"📂 데이터 로드 중: {excel_path}")
        
        if mapping_rules_path:
            # 매핑 규칙이 있는 경우
            with open(mapping_rules_path, encoding='utf-8') as f:
                mapping_rules = json.load(f)['field_map']
            
            df_raw = pd.read_excel(excel_path)
            col_map = {k: v for k, v in mapping_rules.items() if k in df_raw.columns}
            df = df_raw.rename(columns=col_map)
            
            # 필요 컬럼 추가
            for needed in mapping_rules.values():
                if needed not in df.columns:
                    df[needed] = 0
        else:
            # 매핑 규칙이 없는 경우 원본 그대로 사용
            df = pd.read_excel(excel_path)
        
        # 날짜 컬럼 처리
        if date_column not in df.columns:
            date_candidates = ['ETD/ATD', 'ETA/ATA', 'hasDate']
            for candidate in date_candidates:
                if candidate in df.columns:
                    df[date_column] = pd.to_datetime(df[candidate], errors='coerce')
                    break
            else:
                df[date_column] = pd.Timestamp.now()
        
        df[date_column] = df[date_column].fillna(pd.Timestamp.now())
        
        # 수치 컬럼 처리
        numeric_cols = ['hasAmount', 'hasVolume']
        for col in numeric_cols:
            if col in df.columns:
                df[f'{col}_numeric'] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        print(f"✅ 데이터 로드 완료: {df.shape[0]:,}개 레코드, {df.shape[1]}개 컬럼")
        
        # 2. 온톨로지 기준 분석 실행
        reports = create_ontology_based_reports(df, location_column, date_column)
        
        # 3. Excel 저장
        excel_output_path = save_ontology_reports_excel(reports)
        reports['_excel_path'] = excel_output_path
        
        # 4. 결과 요약
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        print("\n" + "=" * 80)
        print("🎉 온톨로지 기준 HVDC 창고 흐름 분석 완료!")
        print("=" * 80)
        
        print(f"📊 처리 결과:")
        print(f"   • 원본 데이터: {df.shape[0]:,}개 레코드")
        print(f"   • 처리 시간: {processing_time:.2f}초")
        print(f"   • Excel 파일: {excel_output_path}")
        
        if '창고별_요약통계' in reports:
            print(f"   • 창고 개수: {len(reports['창고별_요약통계'])}개")
        if '현장별_요약통계' in reports:
            print(f"   • 현장 개수: {len(reports['현장별_요약통계'])}개")
        
        return reports
        
    except Exception as e:
        print(f"❌ 온톨로지 기준 분석 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return {}

# ===============================================================================
# 6. 테스트 실행부
# ===============================================================================

if __name__ == "__main__":
    """직접 실행 시 테스트"""
    print("🧪 온톨로지 기준 분류 시스템 테스트")
    print("=" * 80)
    
    # 테스트 데이터 생성
    test_locations = [
        "DSV Indoor", "DSV Outdoor", "DSV Al Markaz", "MOSB",  # 창고
        "AGI", "DAS", "MIR", "SHU",  # 현장
        "AAA Storage", "Dangerous Storage",  # 위험물 창고
        "Unknown Location", "", None  # 알려지지 않은 위치
    ]
    
    print("📋 위치 분류 테스트:")
    for location in test_locations:
        group = get_location_group(location)
        print(f"  {str(location):20} → {group}")
    
    print(f"\n📊 온톨로지 정의:")
    print(f"  Indoor Warehouse: {INDOOR_WAREHOUSE}")
    print(f"  Outdoor Warehouse: {OUTDOOR_WAREHOUSE}")
    print(f"  Site: {SITE}")
    print(f"  Dangerous Cargo: {DANGEROUS_CARGO}")
    
    print(f"\n✅ 온톨로지 기준 분류 시스템 테스트 완료!") 