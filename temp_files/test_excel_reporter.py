#!/usr/bin/env python3
"""
HVDC Excel Reporter 테스트 스크립트
"""

import pandas as pd
from datetime import datetime
import sys
import os

# 핵심 모듈 임포트
from config import load_expected_stock
from core.inventory_engine import validate_transfer_pairs, validate_date_sequence
from core.deduplication import drop_duplicate_transfers, reconcile_orphan_transfers
from core.loader import DataLoader
from excel_reporter import generate_excel_comprehensive_report

def main():
    """Excel Reporter 테스트 메인 함수"""
    print("🚀 HVDC Excel Reporter 테스트 시작")
    print("=" * 70)
    
    try:
        # 1. 데이터 로딩
        print("📄 데이터 로딩 중...")
        loader = DataLoader()
        excel_files = loader.load_excel_files("data")
        
        if not excel_files:
            print("❌ Excel 파일이 없습니다!")
            return False
            
        raw_transactions = loader.extract_transactions(excel_files)
        print(f"📊 총 {len(raw_transactions):,}건의 원시 트랜잭션 수집")

        # 2. 트랜잭션 DataFrame 변환
        print("🔄 트랜잭션 변환 중...")
        transaction_df = transactions_to_dataframe(raw_transactions)
        print(f"✅ {len(transaction_df)}건 트랜잭션 생성")

        # 3. 전처리
        print("🛠️ 데이터 전처리 중...")
        transaction_df = reconcile_orphan_transfers(transaction_df)
        transaction_df = drop_duplicate_transfers(transaction_df)
        
        # 4. 검증
        validate_transfer_pairs(transaction_df)
        validate_date_sequence(transaction_df)
        print("✅ 데이터 검증 완료")
        
        # 5. 일별 재고 계산
        print("📊 일별 재고 계산 중...")
        daily_stock = calculate_daily_inventory(transaction_df)
        print(f"✅ {len(daily_stock)}개 일별 재고 스냅샷 생성")
        
        # 6. Excel 리포트 생성
        print("\n📊 Excel 종합 리포트 생성 시작...")
        output_file = f"HVDC_테스트리포트_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        
        success = generate_excel_comprehensive_report(
            transaction_df=transaction_df,
            daily_stock=daily_stock,
            output_file=output_file,
            debug=True
        )
        
        if success:
            print(f"\n🎉 Excel 리포트 생성 성공!")
            print(f"📋 파일: {output_file}")
            return True
        else:
            print("❌ Excel 리포트 생성 실패!")
            return False
            
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def transactions_to_dataframe(transactions):
    """트랜잭션 리스트를 DataFrame으로 변환"""
    data = []
    
    for tx in transactions:
        tx_data = tx.get('data', {})
        
        # 기본 정보 추출
        case_id = extract_case_id(tx_data)
        warehouse = extract_warehouse(tx_data)
        date_val = extract_datetime(tx_data)
        
        # 수량 처리
        incoming = tx_data.get('incoming', 0) or 0
        outgoing = tx_data.get('outgoing', 0) or 0
        
        # 기본 레코드 템플릿
        base_record = {
            'Case_No': case_id,
            'Date': date_val,
            'Location': warehouse,
            'Source_File': tx.get('source_file', ''),
            'Loc_From': 'SOURCE',
            'Target_Warehouse': warehouse
        }
        
        # IN 트랜잭션 생성
        if incoming > 0:
            record = base_record.copy()
            record.update({
                'TxType_Refined': 'IN',
                'Qty': int(incoming)
            })
            data.append(record)
            
        # OUT 트랜잭션 생성
        if outgoing > 0:
            record = base_record.copy()
            
            # 사이트 구분하여 FINAL_OUT vs TRANSFER_OUT 결정
            site = extract_site(warehouse)
            tx_type = 'FINAL_OUT' if site in ['AGI', 'DAS', 'MIR', 'SHU'] else 'TRANSFER_OUT'
                
            record.update({
                'TxType_Refined': tx_type,
                'Qty': int(outgoing),
                'Loc_From': warehouse,  # 출고는 해당 창고에서
                'Target_Warehouse': 'DESTINATION'
            })
            data.append(record)
    
    return pd.DataFrame(data)

def extract_case_id(data):
    """케이스 ID 추출"""
    case_fields = ['case', 'Case', 'case_id', 'CaseID', 'ID', 'carton', 'box', 'mr#']
    
    for field in case_fields:
        if field in data and data[field]:
            case_value = str(data[field]).strip()
            if case_value and case_value.lower() not in ['nan', 'none', '']:
                return case_value
    
    return f"CASE_{abs(hash(str(data))) % 100000}"

def extract_warehouse(data):
    """창고명 추출 및 정규화"""
    warehouse_fields = ['warehouse', 'Warehouse', 'site', 'Site', 'location', 'Location']
    
    for field in warehouse_fields:
        if field in data and data[field]:
            raw_warehouse = str(data[field]).strip()
            if raw_warehouse and raw_warehouse.lower() not in ['nan', 'none', '']:
                return normalize_warehouse_name(raw_warehouse)
    
    return 'UNKNOWN'

def extract_datetime(data):
    """날짜/시간 추출"""
    date_fields = ['date', 'Date', 'timestamp', 'Timestamp', 'datetime']
    
    for field in date_fields:
        if field in data and data[field]:
            try:
                date_value = data[field]
                if isinstance(date_value, str) and date_value.lower() in ['nan', 'none', '']:
                    continue
                return pd.to_datetime(date_value)
            except:
                continue
    
    return pd.Timestamp.now()

def normalize_warehouse_name(raw_name):
    """창고명 정규화"""
    if pd.isna(raw_name) or not raw_name:
        return 'UNKNOWN'
    
    name_lower = str(raw_name).lower().strip()
    
    warehouse_rules = {
        'DSV Al Markaz': ['markaz', 'm1', 'al markaz', 'almarkaz'],
        'DSV Indoor': ['indoor', 'm44', 'hauler indoor'],
        'DSV Outdoor': ['outdoor', 'out'],
        'MOSB': ['mosb'],
        'DSV MZP': ['mzp'],
        'DHL WH': ['dhl'],
        'AAA Storage': ['aaa']
    }
    
    for canonical, patterns in warehouse_rules.items():
        if any(pattern in name_lower for pattern in patterns):
            return canonical
    
    return str(raw_name).strip()

def extract_site(warehouse_name):
    """사이트명 추출"""
    if pd.isna(warehouse_name):
        return 'UNK'
    
    name_upper = str(warehouse_name).upper()
    
    site_patterns = {
        'AGI': ['AGI'],
        'DAS': ['DAS'],
        'MIR': ['MIR'],
        'SHU': ['SHU']
    }
    
    for site, patterns in site_patterns.items():
        if any(pattern in name_upper for pattern in patterns):
            return site
    
    return 'UNK'

def calculate_daily_inventory(transaction_df):
    """일별 재고 계산"""
    if transaction_df.empty:
        return pd.DataFrame()
    
    # 날짜별로 정렬
    transaction_df = transaction_df.sort_values(['Location', 'Date'])
    
    # 창고별로 그룹화하여 일별 재고 계산
    daily_stock_data = []
    
    for location in transaction_df['Location'].unique():
        location_df = transaction_df[transaction_df['Location'] == location].copy()
        
        # 초기 재고 (첫 번째 트랜잭션 이전)
        current_stock = 0
        
        for _, row in location_df.iterrows():
            date = row['Date']
            tx_type = row['TxType_Refined']
            qty = row['Qty']
            
            # 기초 재고
            opening_stock = current_stock
            
            # 트랜잭션 처리
            if tx_type == 'IN':
                inbound = qty
                transfer_out = 0
                final_out = 0
                current_stock += qty
            elif tx_type == 'TRANSFER_OUT':
                inbound = 0
                transfer_out = qty
                final_out = 0
                current_stock -= qty
            elif tx_type == 'FINAL_OUT':
                inbound = 0
                transfer_out = 0
                final_out = qty
                current_stock -= qty
            else:
                inbound = 0
                transfer_out = 0
                final_out = 0
            
            total_outbound = transfer_out + final_out
            closing_stock = current_stock
            
            daily_stock_data.append({
                'Location': location,
                'Date': date,
                'Opening_Stock': opening_stock,
                'Inbound': inbound,
                'Transfer_Out': transfer_out,
                'Final_Out': final_out,
                'Total_Outbound': total_outbound,
                'Closing_Stock': closing_stock
            })
    
    return pd.DataFrame(daily_stock_data)

if __name__ == "__main__":
    success = main()
    if not success:
        exit(1) 