"""
HVDC 데이터 로딩 및 전처리 모듈 - 수정된 버전
실제 Excel 파일 구조에 맞춘 데이터 추출
"""

import pandas as pd
import os
import glob
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataLoader:
    """HVDC 데이터 로딩 및 전처리 클래스 - 개선된 버전"""
    
    def __init__(self):
        self.warehouse_mapping = {
            'DSV Al Markaz': ['markaz', 'm1', 'al markaz', 'almarkaz', 'al_markaz'],
            'DSV Indoor': ['indoor', 'm44', 'hauler indoor', 'hauler_indoor'],
            'DSV Outdoor': ['outdoor', 'out'],
            'MOSB': ['mosb'],
            'DSV MZP': ['mzp'],
            'DHL WH': ['dhl'],
            'AAA Storage': ['aaa']
        }
        
    def load_excel_files(self, data_dir: str = "data") -> Dict[str, pd.DataFrame]:
        """Excel 파일들을 로드 (개선된 버전)"""
        excel_files = {}
        
        if not os.path.exists(data_dir):
            logger.error(f"데이터 디렉토리 없음: {data_dir}")
            return excel_files
        
        # HVDC 창고 파일 패턴
        file_patterns = [
            "HVDC WAREHOUSE_HITACHI*.xlsx",
            "HVDC WAREHOUSE_SIMENSE*.xlsx"
        ]
        
        for pattern in file_patterns:
            for filepath in glob.glob(os.path.join(data_dir, pattern)):
                filename = os.path.basename(filepath)
                
                # 인보이스 파일 스킵
                if 'invoice' in filename.lower():
                    continue
                    
                try:
                    print(f"📄 파일 처리 중: {filename}")
                    
                    # Excel 파일 로드
                    xl_file = pd.ExcelFile(filepath)
                    
                    # Case List 시트 우선 선택
                    sheet_name = xl_file.sheet_names[0]
                    for sheet in xl_file.sheet_names:
                        if 'case' in sheet.lower() and 'list' in sheet.lower():
                            sheet_name = sheet
                            break
                    
                    df = pd.read_excel(filepath, sheet_name=sheet_name)
                    
                    if not df.empty:
                        excel_files[filename] = df
                        
                        # 간단한 통계 출력
                        date_cols = self._find_date_columns(df)
                        print(f"   📅 날짜 컬럼 {len(date_cols)}개 발견")
                        
                        case_col = self._find_case_column(df)
                        if case_col:
                            case_count = df[case_col].nunique()
                            print(f"   📦 고유 케이스 {case_count}개")
                    
                except Exception as e:
                    logger.error(f"Excel 파일 로드 실패 {filename}: {e}")
                    
        return excel_files
    
    def extract_transactions(self, excel_files: Dict[str, pd.DataFrame]) -> List[Dict]:
        """Excel 파일들에서 트랜잭션 데이터 추출 (개선된 로직)"""
        all_transactions = []
        
        for filename, df in excel_files.items():
            try:
                transactions = self._extract_file_transactions(df, filename)
                all_transactions.extend(transactions)
                print(f"   ✅ {len(transactions)}건 이벤트 추출")
                
            except Exception as e:
                logger.error(f"트랜잭션 추출 실패 {filename}: {e}")
                
        return all_transactions
    
    def _extract_file_transactions(self, df: pd.DataFrame, filename: str) -> List[Dict]:
        """단일 파일에서 트랜잭션 추출 - Status 컬럼 지원"""
        transactions = []
        
        if df.empty:
            return transactions
        
        # 핵심 컬럼 찾기
        case_col = self._find_case_column(df)
        qty_col = self._find_quantity_column(df)
        date_cols = self._find_date_columns(df)
        
        # 새로운 Status 컬럼들 찾기
        status_cols = self._find_status_columns(df)
        
        if not case_col:
            logger.warning(f"케이스 컬럼을 찾을 수 없음: {filename}")
            return transactions
        
        if not date_cols:
            logger.warning(f"날짜 컬럼을 찾을 수 없음: {filename}")
            return transactions
        
        # Qty 전처리
        if qty_col:
            df[qty_col] = self._normalize_quantities(df, case_col, qty_col)
        else:
            df['default_qty'] = 1
            qty_col = 'default_qty'
        
        # 각 행에 대해 트랜잭션 생성
        for idx, row in df.iterrows():
            case_id = str(row[case_col]) if pd.notna(row[case_col]) else f"CASE_{idx}"
            quantity = int(row[qty_col]) if pd.notna(row[qty_col]) else 1
            
            # Status 정보 추출
            status_info = self._extract_status_info(row, status_cols)
            
            # 각 날짜 컬럼에서 이벤트 추출
            case_events = []
            
            for date_col in date_cols:
                if pd.notna(row[date_col]):
                    try:
                        event_date = pd.to_datetime(row[date_col])
                        warehouse = self._extract_warehouse_from_column(date_col)
                        
                        # Status 정보가 있으면 우선 사용
                        if status_info.get('current_location'):
                            warehouse = status_info['current_location']
                        
                        if warehouse != 'UNKNOWN':
                            event_data = {
                                'case_id': case_id,
                                'date': event_date,
                                'warehouse': warehouse,
                                'quantity': quantity,
                                'source_column': date_col,
                                'status_info': status_info  # Status 정보 추가
                            }
                            case_events.append(event_data)
                    except Exception as e:
                        logger.debug(f"날짜 파싱 실패 {date_col}: {e}")
                        continue
            
            # 시간순 정렬
            case_events.sort(key=lambda x: x['date'])
            
            # 이벤트를 트랜잭션으로 변환
            for i, event in enumerate(case_events):
                # 입고 이벤트 (모든 위치 도착)
                incoming_tx = {
                    'source_file': filename,
                    'timestamp': datetime.now(),
                    'data': {
                        'case': event['case_id'],
                        'date': event['date'],
                        'warehouse': event['warehouse'],
                        'incoming': event['quantity'],
                        'outgoing': 0,
                        'inventory': event['quantity'],
                        'status_warehouse': event['status_info'].get('warehouse', ''),
                        'status_site': event['status_info'].get('site', ''),
                        'status_current': event['status_info'].get('current', ''),
                        'status_location': event['status_info'].get('location', ''),
                        'status_storage': event['status_info'].get('storage', '')
                    }
                }
                transactions.append(incoming_tx)
                
                # 출고 이벤트 (이전 위치에서)
                if i > 0:
                    prev_warehouse = case_events[i-1]['warehouse']
                    outgoing_tx = {
                        'source_file': filename,
                        'timestamp': datetime.now(),
                        'data': {
                            'case': event['case_id'],
                            'date': event['date'],
                            'warehouse': prev_warehouse,
                            'incoming': 0,
                            'outgoing': event['quantity'],
                            'inventory': 0,
                            'status_warehouse': event['status_info'].get('warehouse', ''),
                            'status_site': event['status_info'].get('site', ''),
                            'status_current': event['status_info'].get('current', ''),
                            'status_location': event['status_info'].get('location', ''),
                            'status_storage': event['status_info'].get('storage', '')
                        }
                    }
                    transactions.append(outgoing_tx)
        
        return transactions
    
    def _find_status_columns(self, df: pd.DataFrame) -> Dict[str, str]:
        """Status 관련 컬럼들 찾기"""
        status_mapping = {}
        
        status_patterns = {
            'warehouse': ['status_warehouse', 'status warehouse'],
            'site': ['status_site', 'status site'],
            'current': ['status_current', 'status current'],
            'location': ['status_location', 'status location'],
            'storage': ['status_storage', 'status storage']
        }
        
        for col in df.columns:
            col_lower = str(col).lower().strip()
            for status_type, patterns in status_patterns.items():
                if any(pattern in col_lower for pattern in patterns):
                    status_mapping[status_type] = col
                    break
        
        return status_mapping
    
    def _extract_status_info(self, row: pd.Series, status_cols: Dict[str, str]) -> Dict[str, str]:
        """행에서 Status 정보 추출"""
        status_info = {}
        
        for status_type, col_name in status_cols.items():
            if col_name in row.index and pd.notna(row[col_name]):
                status_info[status_type] = str(row[col_name]).strip()
        
        # 현재 위치 결정 우선순위
        # 1. Status_Location이 있으면 사용
        # 2. Status_Current가 있으면 사용  
        # 3. Status_Warehouse 사용
        if status_info.get('location'):
            status_info['current_location'] = self._normalize_warehouse_name(status_info['location'])
        elif status_info.get('current'):
            status_info['current_location'] = self._normalize_warehouse_name(status_info['current'])
        elif status_info.get('warehouse'):
            status_info['current_location'] = self._normalize_warehouse_name(status_info['warehouse'])
        
        return status_info
    
    def _normalize_warehouse_name(self, raw_name: str) -> str:
        """창고명 정규화 - Status 컬럼용"""
        if pd.isna(raw_name) or not raw_name:
            return 'UNKNOWN'
            
        name_lower = str(raw_name).lower().strip()
        
        # 기존 매핑 + Status 특화 매핑
        warehouse_rules = {
            'DSV Al Markaz': ['markaz', 'm1', 'al markaz', 'almarkaz', 'al_markaz', 'dsv al markaz'],
            'DSV Indoor': ['indoor', 'm44', 'hauler indoor', 'hauler_indoor', 'dsv indoor'],
            'DSV Outdoor': ['outdoor', 'out', 'dsv outdoor'],
            'MOSB': ['mosb'],
            'DSV MZP': ['mzp', 'dsv mzp'],
            'DHL WH': ['dhl', 'dhl wh'],
            'AAA Storage': ['aaa', 'aaa storage'],
            'Storage': ['storage', '창고'],  # Status 컬럼 특화
            'Site': ['site', '사이트'],        # Status 컬럼 특화
        }
        
        for canonical, patterns in warehouse_rules.items():
            if any(pattern in name_lower for pattern in patterns):
                return canonical
        
        return str(raw_name).strip()
    
    def _find_case_column(self, df: pd.DataFrame) -> Optional[str]:
        """케이스 컬럼 찾기"""
        case_patterns = ['case', 'carton', 'box', 'mr#', 'mr #', 'sct ship no', 'case no']
        
        for col in df.columns:
            col_lower = str(col).lower().strip()
            if any(pattern in col_lower for pattern in case_patterns):
                return col
        return None
    
    def _normalize_text_for_matching(self, text: str) -> str:
        """텍스트 정규화 - 대소문자, 복수형, 소유격 통일"""
        if pd.isna(text) or not text:
            return ""
        
        normalized = str(text).strip()
        
        # 1. 대소문자 통일 (소문자로)
        normalized = normalized.lower()
        
        # 2. 특수문자 제거 및 공백 정리
        import re
        normalized = re.sub(r'[\'\"’]', '', normalized)  # 따옴표 제거
        normalized = re.sub(r'[^\w\s]', ' ', normalized)   # 특수문자를 공백으로
        normalized = re.sub(r'\s+', ' ', normalized)       # 연속 공백 제거
        normalized = normalized.strip()
        
        # 3. 복수형 정규화 (s 제거)
        if normalized.endswith('s') and len(normalized) > 2:
            # 일반적인 복수형 처리
            if normalized.endswith('ies'):
                normalized = normalized[:-3] + 'y'  # companies -> company
            elif normalized.endswith('es') and len(normalized) > 3:
                if normalized[-3] in 'sxz' or normalized.endswith('ches') or normalized.endswith('shes'):
                    normalized = normalized[:-2]     # boxes -> box, dishes -> dish
                else:
                    normalized = normalized[:-1]     # cases -> case
            elif not normalized.endswith('ss'):     # glass는 그대로
                normalized = normalized[:-1]         # pkgs -> pkg
        
        # 4. 약어 표준화
        abbreviation_map = {
            'pkg': 'package',
            'qty': 'quantity', 
            'q ty': 'quantity',
            'pcs': 'pieces',
            'pc': 'piece',
            'ea': 'each',
            'no': 'number',
            'wh': 'warehouse',
            'mr': 'material request'
        }
        
        for abbr, full in abbreviation_map.items():
            if normalized == abbr or normalized.startswith(abbr + ' '):
                normalized = normalized.replace(abbr, full, 1)
        
        return normalized.strip()
    
    def _find_quantity_column(self, df: pd.DataFrame) -> Optional[str]:
        """수량 컬럼 찾기 - 정규화된 패턴 매칭"""
        quantity_patterns = [
            # 기본 수량 패턴 (정규화 전)
            'q\'ty', 'qty', 'quantity', 'received', 'pieces', 'piece',
            # PKG 관련 모든 변형
            'pkg', 'pkgs', 'pkg\'s', 'package', 'packages', 'package\'s',
            'PKG', 'PKGS', 'PKG\'S', 'PACKAGE', 'PACKAGES', 'PACKAGE\'S',
            'Pkg', 'Pkgs', 'Pkg\'s', 'Package', 'Packages', 'Package\'s',
            # 기타 수량 관련
            'pcs', 'pc', 'pieces', 'piece', 'ea', 'each', 'count', 'cnt', 'p\'kg'
        ]
        
        # 정규화된 패턴으로 변환
        normalized_patterns = [self._normalize_text_for_matching(p) for p in quantity_patterns]
        
        for col in df.columns:
            col_normalized = self._normalize_text_for_matching(str(col))
            
            # 정확한 매칭
            if col_normalized in normalized_patterns:
                logger.debug(f"수량 컬럼 발견 (정확 매칭): {col} → {col_normalized}")
                return col
            
            # 부분 매칭 (컬럼명에 패턴이 포함된 경우)
            for pattern in normalized_patterns:
                if pattern and (pattern in col_normalized or col_normalized in pattern):
                    logger.debug(f"수량 컬럼 발견 (부분 매칭): {col} → {col_normalized} (패턴: {pattern})")
                    return col
        
        return None
    
    def _find_date_columns(self, df: pd.DataFrame) -> List[str]:
        """날짜 컬럼 찾기 (개선된 로직)"""
        date_columns = []
        
        for col in df.columns:
            # 1. 컬럼명에 창고명이 포함된 경우
            warehouse = self._extract_warehouse_from_column(col)
            if warehouse != 'UNKNOWN':
                # 실제 날짜 데이터가 있는지 확인
                sample_values = df[col].dropna().head(5)
                if len(sample_values) > 0:
                    date_count = 0
                    for val in sample_values:
                        if self._is_date_like(str(val)):
                            date_count += 1
                    
                    # 50% 이상이 날짜 형식이면 날짜 컬럼으로 인정
                    if date_count >= len(sample_values) * 0.5:
                        date_columns.append(col)
        
        return date_columns
    
    def _extract_warehouse_from_column(self, col_name: str) -> str:
        """컬럼명에서 창고명 추출"""
        col_lower = str(col_name).lower().strip()
        
        # 날짜 관련 키워드 제거
        date_keywords = ['eta', 'etd', 'ata', 'atd', 'date', 'time', 'arrival', 'departure']
        for keyword in date_keywords:
            col_lower = col_lower.replace(keyword, '').strip()
        
        # 창고 매핑 확인
        for warehouse, patterns in self.warehouse_mapping.items():
            for pattern in patterns:
                if pattern in col_lower:
                    return warehouse
        
        return 'UNKNOWN'
    
    def _is_date_like(self, value: str) -> bool:
        """문자열이 날짜 형식인지 확인"""
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # 2024-01-01
            r'\d{2}/\d{2}/\d{4}',  # 01/01/2024
            r'\d{1,2}/\d{1,2}/\d{4}',  # 1/1/2024
            r'\d{4}/\d{2}/\d{2}',  # 2024/01/01
        ]
        
        for pattern in date_patterns:
            if re.search(pattern, str(value)):
                return True
                
        # pandas로 날짜 파싱 시도
        try:
            pd.to_datetime(value)
            return True
        except:
            return False
    
    def _normalize_quantities(self, df: pd.DataFrame, case_col: str, qty_col: str) -> pd.Series:
        """수량 정규화 (케이스별 전파) - 인덱스 안전 처리"""
        qty_series = pd.to_numeric(df[qty_col], errors='coerce')
        
        # 0을 NaN으로 변환
        qty_series = qty_series.replace(0, pd.NA)
        
        try:
            # 케이스별 전파 (pandas 2.0+ 호환, 인덱스 안전)
            df_temp = df[[case_col]].copy()
            df_temp['qty'] = qty_series
            
            # 케이스별 그룹핑하여 forward/backward fill
            filled_values = df_temp.groupby(case_col)['qty'].transform(
                lambda x: x.ffill().bfill()
            )
            
            # 원본 인덱스 유지하면서 결과 반환
            result = filled_values.fillna(1).astype(int)
            
        except Exception as e:
            logger.warning(f"수량 정규화 실패: {e}, 기본값 사용")
            result = pd.Series([1] * len(df), index=df.index)
        
        return result
    
    def get_summary_statistics(self, transactions: List[Dict]) -> Dict[str, Any]:
        """추출된 트랜잭션 요약 통계"""
        if not transactions:
            return {}
        
        # 창고별 집계
        warehouse_counts = {}
        total_incoming = 0
        total_outgoing = 0
        
        for tx in transactions:
            data = tx.get('data', {})
            warehouse = data.get('warehouse', 'UNKNOWN')
            
            if warehouse not in warehouse_counts:
                warehouse_counts[warehouse] = 0
            warehouse_counts[warehouse] += 1
            
            total_incoming += data.get('incoming', 0)
            total_outgoing += data.get('outgoing', 0)
        
        # 날짜 범위
        dates = []
        for tx in transactions:
            date = tx.get('data', {}).get('date')
            if date:
                dates.append(date)
        
        return {
            'total_transactions': len(transactions),
            'total_incoming': total_incoming,
            'total_outgoing': total_outgoing,
            'warehouse_distribution': warehouse_counts,
            'date_range': {
                'start': min(dates) if dates else None,
                'end': max(dates) if dates else None
            },
            'unique_cases': len(set(tx['data'].get('case', '') for tx in transactions if 'case' in tx.get('data', {})))
        } 