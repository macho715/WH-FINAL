#!/usr/bin/env python3
"""HVDC 온톨로지 매핑 리포터 v1.0
ontology_mapper와 excel_reporter를 조합하여 완전한 HVDC 보고서 생성
"""

import pandas as pd
from ontology_mapper import dataframe_to_rdf
import datetime
import json
from pathlib import Path
import os

def create_custom_mapping_rules():
    """실제 HVDC 데이터에 맞는 매핑 규칙 생성"""
    
    # 실제 데이터 컬럼에 맞는 매핑 규칙
    custom_rules = {
        "namespaces": {
            "ex": "http://example.org/hvdc#",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "xsd": "http://www.w3.org/2001/XMLSchema#"
        },
        "field_map": {
            "Shipment Invoice No.": "hasShipmentNo",
            "SCT Ref.No": "hasSCTRef",
            "Site": "hasSite", 
            "EQ No": "hasEquipmentNo",
            "Case No.": "hasCaseNo",
            "Description": "hasDescription",
            "Price": "hasAmount",
            "CBM": "hasVolume",
            "N.W(kgs)": "hasNetWeight",
            "G.W(kgs)": "hasGrossWeight",
            "Currency": "hasCurrency",
            "Vessel": "hasVessel",
            "POL": "hasPortOfLoading",
            "POD": "hasPortOfDischarge",
            "ETD/ATD": "hasETD",
            "ETA/ATA": "hasETA",
            "DSV Indoor": "hasDSVIndoor",
            "DSV Al Markaz": "hasDSVAlMarkaz", 
            "DSV Outdoor": "hasDSVOutdoor",
            "DAS": "hasDAS",
            "Status_Current": "hasCurrentStatus",
            "Status_Location ": "hasLocation",
            "Storage": "hasStorageType"
        }
    }
    
    # 커스텀 매핑 규칙 저장
    with open("mapping_rules_hvdc_custom.json", "w", encoding="utf-8") as f:
        json.dump(custom_rules, f, indent=2, ensure_ascii=False)
    
    return custom_rules

def create_simplified_excel_reporter(df, output_path):
    """실제 데이터 구조에 맞는 간단한 Excel 리포터"""
    
    try:
        import xlsxwriter
        
        with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
            workbook = writer.book
            
            # 1. 원본 데이터 시트
            df.to_excel(writer, sheet_name='Raw_Data', index=False)
            
            # 2. 사이트별 집계
            if 'Site' in df.columns:
                site_summary = df.groupby('Site').agg({
                    'Price': ['count', 'sum', 'mean'],
                    'CBM': 'sum',
                    'G.W(kgs)': 'sum'
                }).round(2)
                site_summary.to_excel(writer, sheet_name='Site_Summary')
            
            # 3. 창고별 현황
            warehouse_cols = ['DSV Indoor', 'DSV Al Markaz', 'DSV Outdoor', 'DAS', 'MOSB', 'MIR', 'SHU', 'AGI']
            available_warehouse_cols = [col for col in warehouse_cols if col in df.columns]
            
            if available_warehouse_cols:
                warehouse_data = []
                for col in available_warehouse_cols:
                    count = df[col].notna().sum()
                    if count > 0:
                        warehouse_data.append({
                            'Warehouse': col,
                            'Count': count,
                            'Percentage': f"{(count/len(df)*100):.1f}%"
                        })
                
                if warehouse_data:
                    warehouse_df = pd.DataFrame(warehouse_data)
                    warehouse_df.to_excel(writer, sheet_name='Warehouse_Summary', index=False)
            
            # 4. 통계 요약
            summary_stats = {
                'Total_Records': len(df),
                'Total_Sites': df['Site'].nunique() if 'Site' in df.columns else 0,
                'Total_Value_SEK': df['Price'].sum() if 'Price' in df.columns else 0,
                'Total_CBM': df['CBM'].sum() if 'CBM' in df.columns else 0,
                'Total_Weight_KG': df['G.W(kgs)'].sum() if 'G.W(kgs)' in df.columns else 0,
                'Report_Generated': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            summary_df = pd.DataFrame(list(summary_stats.items()), columns=['Metric', 'Value'])
            summary_df.to_excel(writer, sheet_name='Summary_Stats', index=False)
            
            print(f"✅ Excel 리포트 생성 성공: {output_path}")
            return True
            
    except Exception as e:
        print(f"❌ Excel 리포트 생성 실패: {e}")
        return False

def main():
    """메인 온톨로지 매핑 리포터 실행"""
    
    print("🔄 HVDC 온톨로지 매핑 리포터 v1.0")
    print("=" * 60)
    
    # 1. 데이터 로드
    print("📁 데이터 로딩...")
    df = pd.read_excel('data/HVDC WAREHOUSE_HITACHI(HE).xlsx')
    print(f"✅ 데이터 로드 완료: {len(df)}건, {len(df.columns)}개 컬럼")
    
    # 2. 커스텀 매핑 규칙 생성
    print("\n🗂️ 커스텀 매핑 규칙 생성...")
    custom_rules = create_custom_mapping_rules() 
    print("✅ 매핑 규칙 생성 완료: mapping_rules_hvdc_custom.json")
    
    # 3. RDF 온톨로지 매핑 (기존 함수 사용)
    print("\n🔗 RDF 온톨로지 매핑...")
    try:
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M')
        rdf_path = dataframe_to_rdf(df, f'rdf_output/hvdc_ontology_{timestamp}.ttl')
        file_size = os.path.getsize(rdf_path) / 1024
        print(f"✅ RDF 매핑 완료: {rdf_path} ({file_size:.1f} KB)")
    except Exception as e:
        print(f"❌ RDF 매핑 실패: {e}")
        return False
    
    # 4. Excel 리포트 생성 (간소화된 버전)
    print("\n📊 Excel 리포트 생성...")
    excel_path = f'HVDC_온톨로지매핑리포트_{timestamp}.xlsx'
    success = create_simplified_excel_reporter(df, excel_path)
    
    if success and os.path.exists(excel_path):
        file_size = os.path.getsize(excel_path) / 1024
        print(f"   파일 크기: {file_size:.1f} KB")
    
    # 5. 매핑 결과 요약
    print(f"\n🎉 온톨로지 매핑 리포터 완료!")
    print("📋 생성된 파일들:")
    print(f"   - RDF 온톨로지: {rdf_path}")
    print(f"   - Excel 리포트: {excel_path}")
    print(f"   - 매핑 규칙: mapping_rules_hvdc_custom.json")
    
    # 6. 매핑된 필드 요약
    print(f"\n🔗 매핑된 필드 ({len(custom_rules['field_map'])}개):")
    for original, mapped in custom_rules['field_map'].items():
        if original in df.columns:
            print(f"   ✅ {original} → {mapped}")
        else:
            print(f"   ❌ {original} → {mapped} (컬럼 없음)")
    
    return True

if __name__ == "__main__":
    main() 