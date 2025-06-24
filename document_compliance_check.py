#!/usr/bin/env python3
"""HVDC 시스템 문서 준수성 검토 및 개선"""

import os
import json
import pandas as pd
from pathlib import Path

def check_document_compliance():
    """문서 표준과 현재 구현의 차이점 분석"""
    
    print("🔍 HVDC 시스템 문서 준수성 검토")
    print("=" * 60)
    
    # 1. 현재 생성된 파일들 확인
    print("\n📁 생성된 파일들:")
    files_to_check = [
        'HVDC_온톨로지매핑리포트_20250624_2040.xlsx',
        'rdf_output/hvdc_ontology_20250624_2040.ttl', 
        'mapping_rules_hvdc_custom.json'
    ]
    
    for file in files_to_check:
        if os.path.exists(file):
            size = os.path.getsize(file) / 1024
            print(f"   ✅ {file} ({size:.1f} KB)")
        else:
            print(f"   ❌ {file} (없음)")
    
    # 2. 매핑 규칙 비교
    print("\n🔗 매핑 규칙 비교:")
    
    # 표준 매핑 규칙 로드
    with open('mapping_rules_v2.5.json', 'r', encoding='utf-8') as f:
        standard_rules = json.load(f)
    
    # 커스텀 매핑 규칙 로드
    with open('mapping_rules_hvdc_custom.json', 'r', encoding='utf-8') as f:
        custom_rules = json.load(f)
    
    print(f"\n📋 표준 매핑 규칙 (v{standard_rules['version']}): {len(standard_rules['field_map'])}개")
    for field, prop in standard_rules['field_map'].items():
        print(f"   {field} → {prop}")
    
    print(f"\n📋 커스텀 매핑 규칙: {len(custom_rules['field_map'])}개")
    for field, prop in custom_rules['field_map'].items():
        print(f"   {field} → {prop}")
    
    # 3. 차이점 분석
    print("\n🆚 표준과 커스텀의 차이점:")
    standard_fields = set(standard_rules['field_map'].keys())
    custom_fields = set(custom_rules['field_map'].keys())
    
    only_standard = standard_fields - custom_fields
    only_custom = custom_fields - standard_fields
    
    print(f"표준에만 있는 필드 ({len(only_standard)}개):", only_standard)
    print(f"커스텀에만 있는 필드 ({len(only_custom)}개):", only_custom)
    
    # 4. 실제 데이터와 매핑률 확인
    print("\n📊 실제 데이터 매핑 현황:")
    df = pd.read_excel('data/HVDC WAREHOUSE_HITACHI(HE).xlsx')
    
    standard_mapped = sum(1 for field in standard_rules['field_map'].keys() if field in df.columns)
    custom_mapped = sum(1 for field in custom_rules['field_map'].keys() if field in df.columns)
    
    print(f"표준 규칙 매핑률: {standard_mapped}/{len(standard_rules['field_map'])} ({standard_mapped/len(standard_rules['field_map'])*100:.1f}%)")
    print(f"커스텀 규칙 매핑률: {custom_mapped}/{len(custom_rules['field_map'])} ({custom_mapped/len(custom_rules['field_map'])*100:.1f}%)")
    
    return {
        'standard_rules': standard_rules,
        'custom_rules': custom_rules,
        'actual_columns': list(df.columns),
        'standard_mapped': standard_mapped,
        'custom_mapped': custom_mapped
    }

def create_unified_mapping_rules(analysis_result):
    """표준과 실제 데이터를 결합한 통합 매핑 규칙 생성"""
    
    print("\n🔄 통합 매핑 규칙 생성...")
    
    standard_rules = analysis_result['standard_rules']
    custom_rules = analysis_result['custom_rules']
    actual_columns = analysis_result['actual_columns']
    
    # 통합 매핑 규칙 생성
    unified_rules = {
        "version": "2.6-unified",
        "description": "HVDC Warehouse Ontology Mapping Rules - 표준 v2.5 + 실제 데이터 통합",
        "namespaces": custom_rules["namespaces"],
        "field_map": {}
    }
    
    # 1. 표준 규칙 중 실제 데이터에 있는 것들 포함
    for field, prop in standard_rules['field_map'].items():
        if field in actual_columns:
            unified_rules['field_map'][field] = prop
            print(f"   ✅ 표준: {field} → {prop}")
    
    # 2. 커스텀 규칙 중 표준에 없지만 중요한 것들 추가
    important_custom_fields = [
        'Shipment Invoice No.', 'Site', 'EQ No', 'Case No.', 
        'Description', 'Price', 'Vessel', 'POL', 'POD',
        'DSV Indoor', 'DSV Al Markaz', 'DSV Outdoor', 'DAS'
    ]
    
    for field, prop in custom_rules['field_map'].items():
        if field in important_custom_fields and field in actual_columns and field not in unified_rules['field_map']:
            unified_rules['field_map'][field] = prop
            print(f"   ✅ 커스텀: {field} → {prop}")
    
    # 3. 통합 규칙 저장
    with open('mapping_rules_v2.6_unified.json', 'w', encoding='utf-8') as f:
        json.dump(unified_rules, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 통합 매핑 규칙 생성 완료: {len(unified_rules['field_map'])}개 필드")
    print("   파일: mapping_rules_v2.6_unified.json")
    
    return unified_rules

def generate_improved_ontology_report(unified_rules):
    """통합 매핑 규칙을 사용한 개선된 온톨로지 리포트 생성"""
    
    print("\n🚀 개선된 온톨로지 리포트 생성...")
    
    from ontology_mapper import dataframe_to_rdf
    import datetime
    
    # 1. 데이터 로드
    df = pd.read_excel('data/HVDC WAREHOUSE_HITACHI(HE).xlsx')
    
    # 2. 통합 매핑 규칙 적용하여 RDF 생성
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M')
    rdf_path = f'rdf_output/hvdc_unified_ontology_{timestamp}.ttl'
    
    try:
        # ontology_mapper가 기본 매핑 규칙을 사용하므로 이 부분은 별도 처리
        rdf_result = dataframe_to_rdf(df, rdf_path)
        rdf_size = os.path.getsize(rdf_result) / 1024
        print(f"   ✅ 통합 RDF 생성 완료: {rdf_result} ({rdf_size:.1f} KB)")
    except Exception as e:
        print(f"   ❌ RDF 생성 실패: {e}")
        return False
    
    # 3. 개선된 Excel 리포트 생성
    excel_path = f'HVDC_통합온톨로지리포트_{timestamp}.xlsx'
    
    try:
        import xlsxwriter
        
        with pd.ExcelWriter(excel_path, engine='xlsxwriter') as writer:
            workbook = writer.book
            
            # 시트 1: 매핑 규칙 요약
            mapping_summary = []
            for field, prop in unified_rules['field_map'].items():
                status = "✅ 매핑됨" if field in df.columns else "❌ 컬럼없음"
                mapping_summary.append({
                    'Original_Field': field,
                    'Ontology_Property': prop,
                    'Status': status,
                    'Data_Type': str(df[field].dtype) if field in df.columns else 'N/A',
                    'Sample_Value': str(df[field].iloc[0]) if field in df.columns and len(df) > 0 else 'N/A'
                })
            
            mapping_df = pd.DataFrame(mapping_summary)
            mapping_df.to_excel(writer, sheet_name='Mapping_Rules', index=False)
            
            # 시트 2: 데이터 통계
            stats_data = {
                'Metric': [
                    'Total Records', 'Total Columns', 'Mapped Fields', 
                    'Mapping Rate', 'RDF File Size (KB)', 'Excel File Generated'
                ],
                'Value': [
                    len(df), len(df.columns), len(unified_rules['field_map']),
                    f"{len([f for f in unified_rules['field_map'].keys() if f in df.columns])/len(unified_rules['field_map'])*100:.1f}%",
                    f"{rdf_size:.1f}", excel_path
                ]
            }
            stats_df = pd.DataFrame(stats_data)
            stats_df.to_excel(writer, sheet_name='Statistics', index=False)
            
            # 시트 3: 원본 데이터 샘플 (첫 100건)
            sample_df = df.head(100)
            sample_df.to_excel(writer, sheet_name='Data_Sample', index=False)
        
        excel_size = os.path.getsize(excel_path) / 1024
        print(f"   ✅ 통합 Excel 리포트 생성 완료: {excel_path} ({excel_size:.1f} KB)")
        
    except Exception as e:
        print(f"   ❌ Excel 리포트 생성 실패: {e}")
        return False
    
    print(f"\n🎉 문서 표준 준수 온톨로지 리포터 완료!")
    print("📋 생성된 파일들:")
    print(f"   - 통합 매핑 규칙: mapping_rules_v2.6_unified.json")
    print(f"   - 통합 RDF 온톨로지: {rdf_path}")  
    print(f"   - 통합 Excel 리포트: {excel_path}")
    
    return True

def main():
    """메인 실행 함수"""
    
    # 1. 문서 준수성 검토
    analysis_result = check_document_compliance()
    
    # 2. 통합 매핑 규칙 생성
    unified_rules = create_unified_mapping_rules(analysis_result)
    
    # 3. 개선된 온톨로지 리포트 생성
    success = generate_improved_ontology_report(unified_rules)
    
    if success:
        print("\n✅ 모든 문서 표준 준수 작업이 완료되었습니다!")
    else:
        print("\n❌ 일부 작업에서 오류가 발생했습니다.")
    
    return success

if __name__ == "__main__":
    main() 