"""
HVDC Warehouse Inventory Engine
==============================
runner/run_quantity_report.py의 calculate_daily_inventory 함수를 기반으로 추출
"""
from __future__ import annotations

import pandas as pd
from typing import Dict, Any, Optional
from datetime import datetime


class InventoryEngine:
    """수량 중심 재고·입출고·월간 KPI 계산 엔진"""
    
    def __init__(self, df: pd.DataFrame):
        """
        초기화
        
        Args:
            df: 표준화된 재고 데이터프레임
        """
        self.df = df.copy()
        self._prepare_data()
    
    def _prepare_data(self) -> None:
        """데이터 전처리"""
        # 기본 컬럼 확인 및 생성
        required_cols = ['Incoming', 'Outgoing', 'Inventory', 'Amount', 'Billing month']
        for col in required_cols:
            if col not in self.df.columns:
                if col == 'Incoming':
                    self.df[col] = self.df.get('cntr_q_in', 0)
                elif col == 'Outgoing':
                    self.df[col] = self.df.get('cntr_q_out', 0)
                elif col == 'Inventory':
                    self.df[col] = self.df.get('Incoming', 0) - self.df.get('Outgoing', 0)
                elif col == 'Amount':
                    self.df[col] = self.df.get('amount', 0)
                elif col == 'Billing month':
                    self.df[col] = self.df.get('billing_month', pd.Timestamp.now())
                else:
                    self.df[col] = 0
        
        # 날짜 정규화
        self.df['Billing month'] = pd.to_datetime(self.df['Billing month'])
        
        # 숫자 컬럼 정규화
        numeric_cols = ['Incoming', 'Outgoing', 'Inventory', 'Amount']
        for col in numeric_cols:
            self.df[col] = pd.to_numeric(self.df[col], errors='coerce').fillna(0)
    
    def calculate_monthly_summary(self) -> pd.DataFrame:
        """월별 재고 요약 계산 - test_inventory_amount.py 기반"""
        # 월별 그룹화
        monthly = self.df.groupby(pd.Grouper(key='Billing month', freq='M')).agg({
            'Incoming': 'sum',
            'Outgoing': 'sum', 
            'Inventory': 'last',  # 기말재고
            'Amount': 'sum'
        }).reset_index()
        
        # 컬럼명 정리
        monthly.columns = ['Billing Month', 'Incoming', 'Outgoing', 'End_Inventory', 'Total_Amount']
        
        # 추가 KPI 계산
        monthly['Net_Change'] = monthly['Incoming'] - monthly['Outgoing']
        monthly['Turnover_Rate'] = monthly['Outgoing'] / monthly['End_Inventory'].replace(0, 1)
        
        return monthly
    
    def calculate_daily_inventory(self) -> pd.DataFrame:
        """일별 재고 계산 - runner/run_quantity_report.py의 함수 기반"""
        transaction_df = self.df.copy()
        
        if transaction_df.empty:
            print("❌ 계산할 트랜잭션이 없습니다")
            return pd.DataFrame()
        
        # 날짜별, 위치별 집계
        transaction_df['Date'] = pd.to_datetime(transaction_df.get('Date', transaction_df.get('Billing month'))).dt.date
        
        daily_summary = transaction_df.groupby(['Location', 'Date', 'TxType_Refined']).agg({
            'Qty': 'sum'
        }).reset_index() if 'Location' in transaction_df.columns else pd.DataFrame()
        
        if daily_summary.empty:
            return pd.DataFrame()
        
        # 피벗으로 입고/출고 분리
        daily_pivot = daily_summary.pivot_table(
            index=['Location', 'Date'],
            columns='TxType_Refined', 
            values='Qty',
            fill_value=0
        ).reset_index()
        
        # 컬럼명 정리
        daily_pivot.columns.name = None
        expected_cols = ['IN', 'TRANSFER_OUT', 'FINAL_OUT']
        for col in expected_cols:
            if col not in daily_pivot.columns:
                daily_pivot[col] = 0
        
        # 재고 계산 (위치별 누적)
        stock_records = []
        
        for location in daily_pivot['Location'].unique():
            if location in ['UNKNOWN', 'UNK', '']:
                continue
                
            loc_data = daily_pivot[daily_pivot['Location'] == location].copy()
            loc_data = loc_data.sort_values('Date')
            
            opening_stock = 0
            
            for _, row in loc_data.iterrows():
                inbound = row.get('IN', 0)
                transfer_out = row.get('TRANSFER_OUT', 0) 
                final_out = row.get('FINAL_OUT', 0)
                total_outbound = transfer_out + final_out
                
                closing_stock = opening_stock + inbound - total_outbound
                
                stock_records.append({
                    'Location': location,
                    'Date': row['Date'],
                    'Opening_Stock': opening_stock,
                    'Inbound': inbound,
                    'Transfer_Out': transfer_out,
                    'Final_Out': final_out,
                    'Total_Outbound': total_outbound,
                    'Closing_Stock': closing_stock
                })
                
                opening_stock = closing_stock
        
        daily_stock_df = pd.DataFrame(stock_records)
        
        return daily_stock_df
    
    def validate_inventory_results(self, expected: Dict[str, int]) -> Dict[str, Any]:
        """재고 결과 검증"""
        daily_stock = self.calculate_daily_inventory()
        
        if daily_stock.empty:
            return {'error': '재고 데이터가 없습니다'}
        
        latest_stock = daily_stock.groupby('Location')['Closing_Stock'].last()
        
        validation_results = {
            'total_matches': 0,
            'total_expected': len(expected),
            'mismatches': [],
            'summary': {}
        }
        
        for location, expected_qty in expected.items():
            actual_qty = latest_stock.get(location, 0)
            is_match = abs(actual_qty - expected_qty) <= 2  # 허용 오차 2
            
            validation_results['summary'][location] = {
                'expected': expected_qty,
                'actual': actual_qty,
                'match': is_match,
                'difference': actual_qty - expected_qty
            }
            
            if is_match:
                validation_results['total_matches'] += 1
            else:
                validation_results['mismatches'].append({
                    'location': location,
                    'expected': expected_qty,
                    'actual': actual_qty,
                    'difference': actual_qty - expected_qty
                })
        
        validation_results['pass_rate'] = (validation_results['total_matches'] / validation_results['total_expected']) * 100
        
        return validation_results 