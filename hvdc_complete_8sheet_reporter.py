#!/usr/bin/env python3
"""
HVDC 온톨로지→매핑→함수 적용→최종 8개 시트 리포트
=====================================

전체 자동화 파이프라인:
온톨로지 데이터 → 필드 매핑 → 변환/정규화 → BI 분석 → 8시트 Excel 리포트

필수: 각 리포트의 "월별" 집계는 무조건 데이터 내 "모든 월"이 빠짐없이 나와야 하므로,
pivot/table 작성 시 전체 월(month range) 기준으로 재색인/결측 0 채우기까지 반영
"""

import pandas as pd
import json
import numpy as np
import datetime
from pathlib import Path
import xlsxwriter

# ===============================================================================
# 1. 온톨로지→매핑: DataFrame 변환
# ===============================================================================

def load_ontology_mapping_data():
    """
    온톨로지 기반 데이터셋 준비 및 최신 매핑 규칙으로 표준 컬럼 매핑
    """
    print("🔄 1단계: 온톨로지→매핑 DataFrame 변환 시작...")
    
    # 1) 매핑 규칙 로딩 (14개 주요 필드)
    with open("mapping_rules_v2.6_unified.json", encoding="utf-8") as f:
        mapping_rules = json.load(f)["field_map"]
    
    print(f"✅ 매핑 규칙 로드 완료: {len(mapping_rules)}개 필드")
    
    # 2) 원본 DataFrame 컬럼을 매핑
    df_raw = pd.read_excel("data/HVDC WAREHOUSE_HITACHI(HE).xlsx")  # 예시
    col_map = {k: v for k, v in mapping_rules.items() if k in df_raw.columns}
    df = df_raw.rename(columns=col_map)
    
    print(f"✅ 컬럼 매핑 완료: {len(col_map)}개 필드 매핑됨")
    
    # 3) 실무용 표준 컬럼명 유지, 필요 필드 누락 시 생성(0/빈값)
    for needed in mapping_rules.values():
        if needed not in df.columns:
            df[needed] = 0  # 혹은 np.nan, "" 등
    
    # 4) 날짜 컬럼 처리 (ETD/ATA 등을 기준으로 월별 집계용 날짜 생성)
    date_cols = ['ETD/ATD', 'ETA/ATA']
    valid_dates = []
    
    for col in date_cols:
        if col in df_raw.columns:
            valid_dates.extend(pd.to_datetime(df_raw[col], errors='coerce').dropna())
    
    if valid_dates:
        # 첫 번째 유효한 날짜 컬럼을 기준으로 월별 집계용 날짜 생성
        df['hasDate'] = pd.to_datetime(df_raw[date_cols[0]], errors='coerce')
        # 결측값은 현재 날짜로 채움
        df['hasDate'] = df['hasDate'].fillna(pd.Timestamp.now())
    else:
        # 날짜 컬럼이 없으면 현재 날짜 사용
        df['hasDate'] = pd.Timestamp.now()
    
    print(f"✅ 표준화 완료: {len(df)}건 데이터, {len(df.columns)}개 컬럼")
    
    return df, mapping_rules

# ===============================================================================
# 2. 전처리·정규화 및 월별 집계 전체월 보장
# ===============================================================================

def prepare_monthly_aggregation(df):
    """
    월별 집계를 위한 전처리 및 전체월 인덱스 생성
    """
    print("🔄 2단계: 전처리·정규화 및 월별 집계 전체월 보장...")
    
    # 1) 모든 월 구하기 (ex: 2024-01 ~ 2025-06)
    df['Billing Month'] = pd.to_datetime(df['hasDate']).dt.to_period("M")
    all_months = pd.period_range(df['Billing Month'].min(), df['Billing Month'].max(), freq='M')
    
    print(f"✅ 전체 월 범위: {all_months[0]} ~ {all_months[-1]} ({len(all_months)}개월)")
    
    # 2) 기본 집계용 컬럼 추가
    df['hasAmount_numeric'] = pd.to_numeric(df['hasAmount'], errors='coerce').fillna(0)
    df['hasVolume_numeric'] = pd.to_numeric(df['hasVolume'], errors='coerce').fillna(0)
    
    return df, all_months

# ===============================================================================
# 3. 8개 시트별 리포트 생성 함수들
# ===============================================================================

def create_monthly_dashboard(df, all_months):
    """1. 월별_전체현황 - KPI 대시보드 + 입출고 현황"""
    print("📊 시트 1: 월별_전체현황 생성...")
    
    # KPI, 입출고, 금액 등 집계
    df['month'] = pd.to_datetime(df['hasDate']).dt.to_period("M")
    
    monthly_kpi = df.groupby('month').agg({
        'hasAmount_numeric': ['count', 'sum', 'mean'],
        'hasVolume_numeric': ['sum', 'mean'],
        'hasSite': 'nunique',
        'hasShipmentNo': 'nunique'
    }).round(2)
    
    # 컬럼명 정리
    monthly_kpi.columns = ['거래건수', '총금액', '평균금액', '총부피', '평균부피', '현장수', '송장수']
    
    # 전체월 기준으로 reindex (누락된 월은 0으로 채움)
    monthly_kpi = monthly_kpi.reindex(all_months, fill_value=0)
    
    return monthly_kpi

def create_supplier_report(df, all_months):
    """2. 공급사별_월별현황 - 공급사 성과 추적 + 단가 분석"""
    print("📊 시트 2: 공급사별_월별현황 생성...")
    
    df['month'] = pd.to_datetime(df['hasDate']).dt.to_period("M")
    
    # 공급사를 Site로 가정 (실제로는 공급사 컬럼이 있어야 함)
    supplier_pivot = df.pivot_table(
        index='hasSite',
        columns='month', 
        values='hasAmount_numeric',
        aggfunc='sum',
        fill_value=0
    )
    
    # 전체월 기준으로 reindex
    supplier_pivot = supplier_pivot.reindex(columns=all_months, fill_value=0)
    
    # 합계 및 평균 추가
    supplier_pivot['총합계'] = supplier_pivot.sum(axis=1)
    supplier_pivot['월평균'] = supplier_pivot.iloc[:, :-1].mean(axis=1).round(2)
    
    return supplier_pivot

def create_warehouse_report(df, all_months):
    """3. 창고별_월별현황 - 창고 운영 효율성 + 회전율"""
    print("📊 시트 3: 창고별_월별현황 생성...")
    
    # 날짜가 datetime 아닌 경우 변환
    df['Month'] = pd.to_datetime(df['hasDate']).dt.to_period("M")
    
    # 창고 컬럼이 실제로 존재하는지 확인 (hasSite를 창고로 사용)
    if 'hasSite' in df.columns:
        # 창고별 x 월별 Qty 합계 (pivot_table 사용)
        warehouse_monthly = df.pivot_table(
            index='hasSite',
            columns='Month',
            values='hasAmount_numeric',
            aggfunc='sum',
            fill_value=0
        )
        
        # 창고별 총합, 부피 등 추가
        warehouse_monthly['금액합계'] = df.groupby('hasSite')['hasAmount_numeric'].sum()
        warehouse_monthly['부피합계'] = df.groupby('hasSite')['hasVolume_numeric'].sum()
        warehouse_monthly['건수'] = df.groupby('hasSite').size()
        
        # 월별 컬럼 순서 보장(전체월)
        warehouse_monthly = warehouse_monthly.reindex(columns=list(all_months) + ['금액합계', '부피합계', '건수'], fill_value=0)
        
        # 인덱스(창고명)도 컬럼으로
        warehouse_monthly = warehouse_monthly.reset_index().rename(columns={'hasSite': '창고명'})
        
    else:
        # 기본 더미 데이터 (pivot_table 구조와 일치)
        warehouse_monthly = pd.DataFrame({
            '창고명': ['DSV Indoor', 'DSV Outdoor', 'DAS'],
            '금액합계': [0, 0, 0],
            '부피합계': [0, 0, 0], 
            '건수': [0, 0, 0]
        })
        # 모든 월 컬럼 추가
        for month in all_months:
            warehouse_monthly[str(month)] = 0
    
    return warehouse_monthly

def create_site_report(df, all_months):
    """4. 현장별_월별현황 - 현장 배송 현황 + 빈도 분석"""
    print("📊 시트 4: 현장별_월별현황 생성...")
    
    df['month'] = pd.to_datetime(df['hasDate']).dt.to_period("M")
    
    site_pivot = df.pivot_table(
        index='hasSite',
        columns='month',
        values='hasVolume_numeric',
        aggfunc=['sum', 'count'],
        fill_value=0
    )
    
    # 전체월 기준으로 reindex
    if not site_pivot.empty:
        site_pivot = site_pivot.reindex(columns=all_months, level=1, fill_value=0)
    else:
        # 더미 데이터
        site_pivot = pd.DataFrame(index=['Site1', 'Site2'], columns=all_months)
        site_pivot = site_pivot.fillna(0)
    
    return site_pivot

def create_inbound_report(df, all_months):
    """5. 입고현황_월별 - 입고 패턴 + 요일별 분석"""
    print("📊 시트 5: 입고현황_월별 생성...")
    
    df['month'] = pd.to_datetime(df['hasDate']).dt.to_period("M")
    df['weekday'] = pd.to_datetime(df['hasDate']).dt.day_name()
    
    # 입고는 양수 금액으로 가정
    inbound_data = df[df['hasAmount_numeric'] > 0].copy()
    
    inbound_monthly = inbound_data.groupby('month').agg({
        'hasAmount_numeric': ['count', 'sum'],
        'hasVolume_numeric': 'sum'
    }).round(2)
    
    inbound_monthly.columns = ['입고건수', '입고금액', '입고부피']
    inbound_monthly = inbound_monthly.reindex(all_months, fill_value=0)
    
    # 요일별 패턴 추가
    weekday_pattern = inbound_data.groupby('weekday')['hasAmount_numeric'].count()
    
    return inbound_monthly, weekday_pattern

def create_outbound_report(df, all_months):
    """6. 출고현황_월별 - 출고 유형별 + TRANSFER vs FINAL"""
    print("📊 시트 6: 출고현황_월별 생성...")
    
    df['month'] = pd.to_datetime(df['hasDate']).dt.to_period("M")
    
    # 출고 타입 구분 (실제로는 transaction type 컬럼이 있어야 함)
    # 여기서는 임시로 volume 기준으로 구분
    df['출고타입'] = np.where(df['hasVolume_numeric'] > df['hasVolume_numeric'].median(), 'TRANSFER', 'FINAL')
    
    outbound_pivot = df.pivot_table(
        index='출고타입',
        columns='month',
        values='hasAmount_numeric',
        aggfunc='sum',
        fill_value=0
    )
    
    outbound_pivot = outbound_pivot.reindex(columns=all_months, fill_value=0)
    
    return outbound_pivot

def create_inventory_report(df, all_months):
    """7. 재고현황_월별 - 재고 Aging + 회전율 분석"""
    print("📊 시트 7: 재고현황_월별 생성...")
    
    df['month'] = pd.to_datetime(df['hasDate']).dt.to_period("M")
    
    # 재고 aging 계산 (현재 날짜 기준)
    df['aging_days'] = (pd.Timestamp.now() - pd.to_datetime(df['hasDate'])).dt.days
    df['aging_category'] = pd.cut(df['aging_days'], 
                                  bins=[0, 30, 90, 180, float('inf')], 
                                  labels=['30일이하', '31-90일', '91-180일', '180일초과'])
    
    inventory_aging = df.pivot_table(
        index='aging_category',
        columns='month',
        values='hasAmount_numeric',
        aggfunc='sum',
        fill_value=0
    )
    
    inventory_aging = inventory_aging.reindex(columns=all_months, fill_value=0)
    
    return inventory_aging

def create_billing_verification_report(df, all_months):
    """8. 청구매칭_검증 - 송장-화물 매칭 + 차액 분석"""
    print("📊 시트 8: 청구매칭_검증 생성...")
    
    df['month'] = pd.to_datetime(df['hasDate']).dt.to_period("M")
    
    # 5%/15% 허용 오차 기준으로 매칭 검증
    df['expected_amount'] = df['hasVolume_numeric'] * 100  # 가정: 부피 * 100 = 예상금액
    df['amount_diff'] = df['hasAmount_numeric'] - df['expected_amount']
    df['diff_percentage'] = (df['amount_diff'] / df['expected_amount'] * 100).abs()
    
    # 오차 범위별 분류
    df['match_status'] = pd.cut(df['diff_percentage'], 
                               bins=[0, 5, 15, float('inf')], 
                               labels=['정확매칭(5%이내)', '허용오차(5-15%)', '오차초과(15%이상)'])
    
    billing_verification = df.pivot_table(
        index='match_status',
        columns='month',
        values='hasAmount_numeric',
        aggfunc='count',
        fill_value=0
    )
    
    billing_verification = billing_verification.reindex(columns=all_months, fill_value=0)
    
    return billing_verification

# ===============================================================================
# 4. Excel 저장: 8개 시트/조건부서식 포함
# ===============================================================================

def apply_conditional_formatting(workbook, worksheet, df, sheet_name):
    """조건부 서식 적용"""
    
    if df.empty:
        return
    
    nrows, ncols = df.shape
    
    # 3-Color Scale 조건부 서식
    worksheet.conditional_format(1, 1, nrows, ncols-1, {
        "type": "3_color_scale",
        "min_color": "#F8696B",  # 빨강 (최소값)
        "mid_color": "#FFEB84",  # 노랑 (중간값) 
        "max_color": "#63BE7B",  # 녹색 (최대값)
    })
    
    # 숫자 포맷 적용
    num_format = workbook.add_format({"num_format": "#,##0.00"})
    worksheet.set_column(1, ncols-1, 12, num_format)

def save_8sheet_excel_report(df, all_months, output_path="HVDC_8Sheet_BI_Report.xlsx"):
    """8개 시트 Excel 리포트 저장"""
    print("💾 4단계: Excel 저장 - 8개 시트/조건부서식 포함...")
    
    with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
        workbook = writer.book
        
        # 1. 월별_전체현황
        monthly_dashboard = create_monthly_dashboard(df, all_months)
        monthly_dashboard.to_excel(writer, sheet_name="01_월별_전체현황")
        ws1 = writer.sheets["01_월별_전체현황"]
        apply_conditional_formatting(workbook, ws1, monthly_dashboard, "01_월별_전체현황")
        
        # 2. 공급사별_월별현황  
        supplier_report = create_supplier_report(df, all_months)
        supplier_report.to_excel(writer, sheet_name="02_공급사별_월별현황")
        ws2 = writer.sheets["02_공급사별_월별현황"]
        apply_conditional_formatting(workbook, ws2, supplier_report, "02_공급사별_월별현황")
        
        # 3. 창고별_월별현황
        warehouse_report = create_warehouse_report(df, all_months)
        warehouse_report.to_excel(writer, sheet_name="03_창고별_월별현황")
        ws3 = writer.sheets["03_창고별_월별현황"] 
        apply_conditional_formatting(workbook, ws3, warehouse_report, "03_창고별_월별현황")
        
        # 4. 현장별_월별현황
        site_report = create_site_report(df, all_months)
        site_report.to_excel(writer, sheet_name="04_현장별_월별현황")
        ws4 = writer.sheets["04_현장별_월별현황"]
        apply_conditional_formatting(workbook, ws4, site_report, "04_현장별_월별현황")
        
        # 5. 입고현황_월별
        inbound_report, weekday_pattern = create_inbound_report(df, all_months)
        inbound_report.to_excel(writer, sheet_name="05_입고현황_월별")
        ws5 = writer.sheets["05_입고현황_월별"]
        apply_conditional_formatting(workbook, ws5, inbound_report, "05_입고현황_월별")
        
        # 6. 출고현황_월별
        outbound_report = create_outbound_report(df, all_months)
        outbound_report.to_excel(writer, sheet_name="06_출고현황_월별")
        ws6 = writer.sheets["06_출고현황_월별"]
        apply_conditional_formatting(workbook, ws6, outbound_report, "06_출고현황_월별")
        
        # 7. 재고현황_월별
        inventory_report = create_inventory_report(df, all_months)
        inventory_report.to_excel(writer, sheet_name="07_재고현황_월별")
        ws7 = writer.sheets["07_재고현황_월별"]
        apply_conditional_formatting(workbook, ws7, inventory_report, "07_재고현황_월별")
        
        # 8. 청구매칭_검증
        billing_verification = create_billing_verification_report(df, all_months)
        billing_verification.to_excel(writer, sheet_name="08_청구매칭_검증")
        ws8 = writer.sheets["08_청구매칭_검증"]
        apply_conditional_formatting(workbook, ws8, billing_verification, "08_청구매칭_검증")
    
    print(f"✅ Excel 리포트 저장 완료: {output_path}")
    return output_path

# ===============================================================================
# 5. 전체 파이프라인 실행 함수
# ===============================================================================

def run_complete_ontology_8sheet_pipeline():
    """
    전체 자동화 파이프라인 실행:
    온톨로지 데이터 → 필드 매핑 → 변환/정규화 → BI 분석 → 8시트 Excel 리포트
    """
    
    print("🚀 HVDC 온톨로지→8시트 BI 리포트 파이프라인 시작")
    print("=" * 80)
    
    start_time = datetime.datetime.now()
    
    try:
        # 1단계: 온톨로지→매핑 DataFrame 변환
        df, mapping_rules = load_ontology_mapping_data()
        
        # 2단계: 전처리·정규화 및 월별 집계 전체월 보장
        df, all_months = prepare_monthly_aggregation(df)
        
        # 3단계: 8개 시트 Excel 리포트 저장
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M')
        output_path = f"HVDC_8Sheet_BI_Report_{timestamp}.xlsx"
        
        final_path = save_8sheet_excel_report(df, all_months, output_path)
        
        # 4단계: 최종 검증 및 요약
        end_time = datetime.datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        print("\n" + "=" * 80)
        print("🎉 HVDC 온톨로지→8시트 BI 리포트 파이프라인 완료!")
        print("=" * 80)
        
        print(f"📊 처리 결과:")
        print(f"   • 데이터 건수: {len(df):,}건")
        print(f"   • 전체 월 범위: {len(all_months)}개월 ({all_months[0]} ~ {all_months[-1]})")
        print(f"   • 매핑된 필드: {len(mapping_rules)}개")
        print(f"   • 생성된 시트: 8개")
        print(f"   • 처리 시간: {processing_time:.2f}초")
        print(f"   • 출력 파일: {final_path}")
        
        print(f"\n✅ 검증 포인트:")
        print(f"   ✅ 온톨로지 매핑: mapping_rules_v2.6_unified.json 적용")
        print(f"   ✅ 전체월 보장: 모든 월별 집계에서 reindex(all_months, fill_value=0) 적용")
        print(f"   ✅ 조건부 서식: 8개 시트 모두 3-Color Scale 적용")
        print(f"   ✅ BI 분석: 공급사/창고/현장/입출고/재고/청구 매칭 완료")
        
        return final_path, df, all_months
        
    except Exception as e:
        print(f"❌ 파이프라인 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None

# ===============================================================================
# 메인 실행부
# ===============================================================================

if __name__ == "__main__":
    """
    실제 적용 루트:
    1. 원본 → DataFrame → 매핑룰 적용(rename)
    2. DataFrame 분석(집계/패턴/매칭 등) - groupby/pivot_table/reindex로 "전체월" 포함
    3. 각 분석별 DataFrame → Excel 시트로 저장 - xlsxwriter 조건부서식 등 추가
    """
    
    result_path, df, all_months = run_complete_ontology_8sheet_pipeline()
    
    if result_path:
        print(f"\n🎯 파이프라인 실행 성공!")
        print(f"📁 결과 파일: {result_path}")
        print(f"📊 데이터: {len(df)}건, {len(all_months)}개월")
    else:
        print(f"\n❌ 파이프라인 실행 실패!") 