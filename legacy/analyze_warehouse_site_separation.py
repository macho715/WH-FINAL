#!/usr/bin/env python3
"""
창고/현장 구분 분석 스크립트
=========================

실제 데이터에서 창고와 현장을 구분하여 분석합니다.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import json

def test_warehouse_site_separation():
    """창고/현장 구분 테스트 함수"""
    print('🧪 창고/현장 구분 테스트')
    
    try:
        # 1. 매핑 규칙 로드
        with open('mapping_rules_v2.6_unified.json', encoding='utf-8') as f:
            mapping_rules = json.load(f)['field_map']
        
        # 2. 실제 데이터 로드
        df_raw = pd.read_excel('data/HVDC WAREHOUSE_HITACHI(HE).xlsx')
        print(f'원본 데이터: {df_raw.shape}')
        
        # 3. 매핑 적용
        col_map = {k: v for k, v in mapping_rules.items() if k in df_raw.columns}
        df = df_raw.rename(columns=col_map)
        
        # 4. 필요 컬럼 추가
        for needed in mapping_rules.values():
            if needed not in df.columns:
                df[needed] = 0
        
        # 5. hasSite 컬럼 분석
        if 'hasSite' in df.columns:
            unique_sites = df['hasSite'].value_counts()
            print(f'\n📊 hasSite 고유값 분석 (상위 10개):')
            print(unique_sites.head(10))
            
            # 창고/현장 구분 함수 적용
            def classify_location_type(name):
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
            
            df['Location_Type'] = df['hasSite'].apply(classify_location_type)
            type_counts = df['Location_Type'].value_counts()
            print(f'\n📊 위치 타입 분류 결과:')
            print(type_counts)
            
            # 창고별 분석
            warehouses = df[df['Location_Type'] == 'WAREHOUSE']['hasSite'].value_counts()
            print(f'\n🏢 창고 목록:')
            print(warehouses)
            
            # 현장별 분석
            sites = df[df['Location_Type'] == 'SITE']['hasSite'].value_counts()
            print(f'\n🏗️ 현장 목록:')
            print(sites)
            
            # 기타 분석
            unknowns = df[df['Location_Type'] == 'UNKNOWN']['hasSite'].value_counts()
            print(f'\n❓ 기타 위치 목록:')
            print(unknowns.head(10))
            
            print(f'\n✅ 창고/현장 구분 분석 완료!')
            print(f'   • 전체 레코드: {len(df):,}개')
            print(f'   • 창고 레코드: {len(df[df["Location_Type"] == "WAREHOUSE"]):,}개')
            print(f'   • 현장 레코드: {len(df[df["Location_Type"] == "SITE"]):,}개')
            print(f'   • 기타 레코드: {len(df[df["Location_Type"] == "UNKNOWN"]):,}개')
            
            # 월별 분석을 위한 날짜 컬럼 확인
            print(f'\n📅 날짜 컬럼 분석:')
            date_cols = ['ETD/ATD', 'ETA/ATA', 'hasDate']
            for col in date_cols:
                if col in df.columns:
                    non_null_count = df[col].notna().sum()
                    print(f'   • {col}: {non_null_count:,}개 유효값')
            
            # 수량/금액 컬럼 확인
            print(f'\n💰 수량/금액 컬럼 분석:')
            numeric_cols = ['hasVolume', 'hasAmount', 'hasVolume_numeric', 'hasAmount_numeric']
            for col in numeric_cols:
                if col in df.columns:
                    non_zero_count = (df[col] != 0).sum()
                    total_sum = df[col].sum() if pd.api.types.is_numeric_dtype(df[col]) else 'N/A'
                    print(f'   • {col}: {non_zero_count:,}개 비영값, 합계: {total_sum}')
        
        else:
            print('❌ hasSite 컬럼이 없습니다.')
            print('사용 가능한 컬럼:')
            print(df.columns.tolist())
    
    except Exception as e:
        print(f'❌ 분석 중 오류 발생: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_warehouse_site_separation() 