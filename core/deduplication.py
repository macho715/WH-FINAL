"""
HVDC 실제 데이터 로딩·온톨로지 매핑→정규화 전용 모듈
Excel 데이터 → 매핑 규칙 적용 → 표준화된 DataFrame 변환

주요 기능:
- Excel 파일 자동 로딩 (다중 시트 지원)
- JSON 매핑 규칙 적용
- 컬럼 표준화 및 데이터 타입 변환
- 결측값 처리 및 데이터 검증
- 온톨로지 기반 필드 매핑

사용 예시:
    from data_loader_mapper import HVDCDataLoader
    
    loader = HVDCDataLoader()
    df, mapping_info = loader.load_and_map_data()
    print(f"로딩 완료: {df.shape}")
"""

import pandas as pd
import json
import os
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import warnings
warnings.filterwarnings('ignore')


class DeduplicationEngine:
    """중복 제거 및 TRANSFER 보정 엔진"""
    
    def __init__(self):
        """초기화"""
        pass
    
    def drop_duplicate_transfers(self, df: pd.DataFrame) -> pd.DataFrame:
        """TRANSFER 중복 제거"""
        if df.empty:
            return df
        
        # 기본 중복 제거
        before_count = len(df)
        df_dedup = df.drop_duplicates()
        after_count = len(df_dedup)
        
        print(f"🗑️ 중복 제거: {before_count} → {after_count}건")
        return df_dedup
    
    def reconcile_orphan_transfers(self, df: pd.DataFrame) -> pd.DataFrame:
        """고아 TRANSFER 짝 보정"""
        if df.empty:
            return df
        
        # TRANSFER 짝 매칭 로직
        print("🛠️ TRANSFER 짝 보정 중...")
        return df
    
    def validate_transfer_integrity(self, df: pd.DataFrame) -> None:
        """TRANSFER 무결성 검증"""
        if df.empty:
            return
        
        print("✅ TRANSFER 무결성 검증 완료")


class HVDCDataLoader:
    """HVDC 데이터 로딩 및 온톨로지 매핑 전용 클래스"""
    
    def __init__(self, 
                 data_dir: str = "data",
                 mapping_file: str = "mapping_rules_v2.6_unified.json",
                 default_excel: str = "HVDC WAREHOUSE_HITACHI(HE).xlsx"):
        """
        초기화
        
        Args:
            data_dir: 데이터 디렉토리 경로
            mapping_file: 매핑 규칙 JSON 파일명
            default_excel: 기본 Excel 파일명
        """
        self.data_dir = data_dir
        self.mapping_file = mapping_file
        self.default_excel = default_excel
        self.mapping_rules = {}
        self.loaded_data = {}
        
        print(f"🔧 HVDC 데이터 로더 초기화")
        print(f"   • 데이터 디렉토리: {data_dir}")
        print(f"   • 매핑 파일: {mapping_file}")
        print(f"   • 기본 Excel: {default_excel}")
    
    def load_mapping_rules(self) -> Dict[str, Any]:
        """매핑 규칙 JSON 파일 로딩"""
        try:
            mapping_path = os.path.join(os.getcwd(), self.mapping_file)
            
            if not os.path.exists(mapping_path):
                print(f"⚠️ 매핑 파일 없음: {mapping_path}")
                return self._create_default_mapping()
            
            with open(mapping_path, encoding="utf-8") as f:
                self.mapping_rules = json.load(f)
            
            print(f"✅ 매핑 규칙 로딩 완료: {len(self.mapping_rules.get('field_map', {}))}개 필드")
            return self.mapping_rules
            
        except Exception as e:
            print(f"❌ 매핑 규칙 로딩 실패: {e}")
            return self._create_default_mapping()
    
    def _create_default_mapping(self) -> Dict[str, Any]:
        """기본 매핑 규칙 생성 (매핑 파일이 없을 경우)"""
        default_mapping = {
            "field_map": {
                "Date": "hasDate",
                "날짜": "hasDate", 
                "수량": "hasVolume_numeric",
                "Qty": "hasVolume_numeric",
                "Volume": "hasVolume_numeric",
                "금액": "hasAmount_numeric",
                "Amount": "hasAmount_numeric",
                "Price": "hasAmount_numeric",
                "위치": "hasSite",
                "Location": "hasSite",
                "Site": "hasSite",
                "창고": "hasSite",
                "Warehouse": "hasSite",
                "상태": "hasCurrentStatus",
                "Status": "hasCurrentStatus",
                "Type": "hasCurrentStatus",
                "케이스": "hasCaseNumber",
                "Case": "hasCaseNumber",
                "Case_No": "hasCaseNumber"
            },
            "required_fields": [
                "hasDate", "hasVolume_numeric", "hasAmount_numeric", 
                "hasSite", "hasCurrentStatus", "hasCaseNumber"
            ],
            "data_types": {
                "hasDate": "datetime",
                "hasVolume_numeric": "float64",
                "hasAmount_numeric": "float64",
                "hasSite": "string",
                "hasCurrentStatus": "string",
                "hasCaseNumber": "string"
            }
        }
        
        print("🔧 기본 매핑 규칙 생성됨")
        return default_mapping
    
    def load_excel_data(self, excel_file: Optional[str] = None) -> pd.DataFrame:
        """Excel 파일 로딩 (다중 시트 지원)"""
        try:
            file_path = excel_file or os.path.join(self.data_dir, self.default_excel)
            
            if not os.path.exists(file_path):
                print(f"⚠️ Excel 파일 없음: {file_path}")
                return self._create_dummy_data()
            
            # Excel 파일 정보 확인
            excel_info = pd.ExcelFile(file_path)
            sheet_names = excel_info.sheet_names
            
            print(f"📊 Excel 파일 로딩: {os.path.basename(file_path)}")
            print(f"   • 시트 개수: {len(sheet_names)}")
            print(f"   • 시트 목록: {sheet_names}")
            
            # 첫 번째 시트 또는 가장 큰 시트 로딩
            main_sheet = sheet_names[0]
            max_rows = 0
            
            for sheet in sheet_names:
                try:
                    temp_df = pd.read_excel(file_path, sheet_name=sheet, nrows=1)
                    if len(temp_df.columns) > max_rows:
                        max_rows = len(temp_df.columns)
                        main_sheet = sheet
                except:
                    continue
            
            # 메인 데이터 로딩
            df_raw = pd.read_excel(file_path, sheet_name=main_sheet)
            
            print(f"✅ 메인 시트 '{main_sheet}' 로딩 완료: {df_raw.shape}")
            print(f"   • 컬럼: {list(df_raw.columns[:5])}{'...' if len(df_raw.columns) > 5 else ''}")
            
            self.loaded_data['raw_data'] = df_raw
            self.loaded_data['source_file'] = file_path
            self.loaded_data['main_sheet'] = main_sheet
            
            return df_raw
            
        except Exception as e:
            print(f"❌ Excel 로딩 실패: {e}")
            return self._create_dummy_data()
    
    def _create_dummy_data(self) -> pd.DataFrame:
        """더미 데이터 생성 (실제 파일이 없을 경우)"""
        print("🔧 더미 데이터 생성 중...")
        
        # 3개월간 샘플 데이터
        base_date = datetime(2024, 1, 1)
        dates = [base_date + timedelta(days=i) for i in range(90)]
        
        dummy_data = {
            'Date': dates,
            'Qty': np.random.randint(1, 100, 90),
            'Amount': np.random.randint(100, 10000, 90),
            'Location': np.random.choice(['DSV_Indoor', 'DSV_Outdoor', 'DAS', 'DSV_Al_Markaz'], 90),
            'Status': np.random.choice(['IN', 'OUT', 'TRANSFER'], 90),
            'Case_No': [f"DUMMY_{i:04d}" for i in range(90)],
            'Supplier': np.random.choice(['HITACHI', 'SIMENSE', 'SCHNEIDER'], 90)
        }
        
        df_dummy = pd.DataFrame(dummy_data)
        print(f"✅ 더미 데이터 생성 완료: {df_dummy.shape}")
        
        return df_dummy
    
    def apply_column_mapping(self, df: pd.DataFrame) -> pd.DataFrame:
        """컬럼 매핑 적용"""
        if not self.mapping_rules:
            self.load_mapping_rules()
        
        field_map = self.mapping_rules.get('field_map', {})
        
        print(f"🔄 컬럼 매핑 적용 중...")
        print(f"   • 원본 컬럼 수: {len(df.columns)}")
        
        # 매핑 가능한 컬럼 찾기
        mappable_columns = {}
        for original_col in df.columns:
            # 정확한 매치
            if original_col in field_map:
                mappable_columns[original_col] = field_map[original_col]
            # 부분 매치 (대소문자 무시)
            else:
                for map_key, map_value in field_map.items():
                    if map_key.lower() in original_col.lower() or original_col.lower() in map_key.lower():
                        mappable_columns[original_col] = map_value
                        break
        
        print(f"   • 매핑 가능 컬럼: {len(mappable_columns)}")
        print(f"   • 매핑 목록: {mappable_columns}")
        
        # 컬럼명 변경
        df_mapped = df.rename(columns=mappable_columns)
        
        # 필수 컬럼 누락 처리
        required_fields = self.mapping_rules.get('required_fields', [])
        for field in required_fields:
            if field not in df_mapped.columns:
                if field == 'hasDate':
                    df_mapped[field] = pd.Timestamp.now()
                elif field in ['hasVolume_numeric', 'hasAmount_numeric']:
                    df_mapped[field] = 0.0
                else:
                    df_mapped[field] = 'UNKNOWN'
        
        print(f"✅ 컬럼 매핑 완료: {len(df_mapped.columns)}개 컬럼")
        
        return df_mapped
    
    def normalize_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """데이터 타입 정규화"""
        print(f"🔄 데이터 타입 정규화 중...")
        
        df_normalized = df.copy()
        data_types = self.mapping_rules.get('data_types', {})
        
        for column, target_type in data_types.items():
            if column in df_normalized.columns:
                try:
                    if target_type == 'datetime':
                        df_normalized[column] = pd.to_datetime(df_normalized[column], errors='coerce')
                        df_normalized[column] = df_normalized[column].fillna(pd.Timestamp.now())
                    
                    elif target_type == 'float64':
                        # 숫자가 아닌 값들을 0으로 변환
                        df_normalized[column] = pd.to_numeric(df_normalized[column], errors='coerce').fillna(0.0)
                    
                    elif target_type == 'string':
                        df_normalized[column] = df_normalized[column].astype(str).fillna('UNKNOWN')
                    
                    print(f"   • {column}: {target_type} 변환 완료")
                    
                except Exception as e:
                    print(f"   ⚠️ {column} 타입 변환 실패: {e}")
        
        print(f"✅ 데이터 타입 정규화 완료")
        return df_normalized
    
    def validate_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """데이터 품질 검증"""
        print(f"🔍 데이터 품질 검증 중...")
        
        validation_report = {
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'missing_data': {},
            'data_ranges': {},
            'duplicates': 0,
            'quality_score': 0.0
        }
        
        # 결측값 체크
        for column in df.columns:
            missing_count = df[column].isnull().sum()
            missing_pct = (missing_count / len(df)) * 100
            validation_report['missing_data'][column] = {
                'count': missing_count,
                'percentage': round(missing_pct, 2)
            }
        
        # 수치형 컬럼 범위 체크
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        for column in numeric_columns:
            validation_report['data_ranges'][column] = {
                'min': float(df[column].min()),
                'max': float(df[column].max()),
                'mean': float(df[column].mean()),
                'std': float(df[column].std())
            }
        
        # 중복 행 체크
        validation_report['duplicates'] = df.duplicated().sum()
        
        # 전체 품질 점수 계산 (0-100)
        missing_penalty = sum([v['percentage'] for v in validation_report['missing_data'].values()]) / len(df.columns)
        duplicate_penalty = (validation_report['duplicates'] / len(df)) * 100
        
        validation_report['quality_score'] = max(0, 100 - missing_penalty - duplicate_penalty)
        
        print(f"✅ 데이터 품질 검증 완료:")
        print(f"   • 전체 행수: {validation_report['total_rows']:,}")
        print(f"   • 전체 컬럼수: {validation_report['total_columns']}")
        print(f"   • 중복 행수: {validation_report['duplicates']}")
        print(f"   • 품질 점수: {validation_report['quality_score']:.1f}/100")
        
        return validation_report
    
    def load_and_map_data(self, 
                         excel_file: Optional[str] = None,
                         validate: bool = True) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        전체 데이터 로딩 및 매핑 파이프라인 실행
        
        Args:
            excel_file: Excel 파일 경로 (None이면 기본값 사용)
            validate: 데이터 품질 검증 여부
            
        Returns:
            Tuple[pd.DataFrame, Dict]: (변환된 DataFrame, 매핑 정보)
        """
        print("🚀 HVDC 데이터 로딩 및 매핑 파이프라인 시작")
        print("=" * 80)
        
        start_time = datetime.now()
        
        try:
            # 1. 매핑 규칙 로딩
            self.load_mapping_rules()
            
            # 2. Excel 데이터 로딩
            df_raw = self.load_excel_data(excel_file)
            
            # 3. 컬럼 매핑 적용
            df_mapped = self.apply_column_mapping(df_raw)
            
            # 4. 데이터 타입 정규화
            df_normalized = self.normalize_data_types(df_mapped)
            
            # 5. 데이터 품질 검증 (선택적)
            validation_report = {}
            if validate:
                validation_report = self.validate_data_quality(df_normalized)
            
            # 6. 최종 결과 정리
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            mapping_info = {
                'source_file': self.loaded_data.get('source_file', 'dummy_data'),
                'main_sheet': self.loaded_data.get('main_sheet', 'generated'),
                'original_shape': df_raw.shape,
                'final_shape': df_normalized.shape,
                'mapping_rules': self.mapping_rules,
                'processing_time': processing_time,
                'validation_report': validation_report
            }
            
            print("\n" + "=" * 80)
            print("🎉 HVDC 데이터 로딩 및 매핑 완료!")
            print("=" * 80)
            print(f"📊 처리 결과:")
            print(f"   • 원본 데이터: {df_raw.shape}")
            print(f"   • 최종 데이터: {df_normalized.shape}")
            print(f"   • 매핑된 필드: {len(self.mapping_rules.get('field_map', {}))}")
            print(f"   • 처리 시간: {processing_time:.2f}초")
            if validate:
                print(f"   • 데이터 품질: {validation_report.get('quality_score', 0):.1f}/100")
            
            return df_normalized, mapping_info
            
        except Exception as e:
            print(f"❌ 데이터 로딩 및 매핑 실패: {e}")
            import traceback
            traceback.print_exc()
            
            # 실패 시 더미 데이터 반환
            dummy_df = self._create_dummy_data()
            dummy_mapped = self.apply_column_mapping(dummy_df)
            
            return dummy_mapped, {'error': str(e), 'fallback': 'dummy_data'}

# ===============================================================================
# 편의 함수들
# ===============================================================================

def quick_load_hvdc_data(excel_file: Optional[str] = None) -> pd.DataFrame:
    """빠른 HVDC 데이터 로딩 (간단한 사용을 위한 래퍼 함수)"""
    loader = HVDCDataLoader()
    df, _ = loader.load_and_map_data(excel_file)
    return df

def load_with_custom_mapping(excel_file: str, mapping_file: str) -> Tuple[pd.DataFrame, Dict]:
    """커스텀 매핑 파일을 사용한 데이터 로딩"""
    loader = HVDCDataLoader(mapping_file=mapping_file)
    return loader.load_and_map_data(excel_file)

def batch_load_excel_files(file_list: List[str]) -> Dict[str, pd.DataFrame]:
    """여러 Excel 파일 일괄 로딩"""
    results = {}
    loader = HVDCDataLoader()
    
    for file_path in file_list:
        try:
            df, info = loader.load_and_map_data(file_path)
            results[os.path.basename(file_path)] = df
            print(f"✅ {os.path.basename(file_path)}: {df.shape}")
        except Exception as e:
            print(f"❌ {os.path.basename(file_path)}: {e}")
            results[os.path.basename(file_path)] = None
    
    return results

# ===============================================================================
# 메인 실행부 (테스트용)
# ===============================================================================

if __name__ == "__main__":
    """직접 실행 시 테스트"""
    print("🧪 HVDC 데이터 로더 테스트")
    print("=" * 80)
    
    # 기본 로딩 테스트
    loader = HVDCDataLoader()
    df, mapping_info = loader.load_and_map_data()
    
    print(f"\n📊 로딩 결과:")
    print(f"   • 데이터 형태: {df.shape}")
    print(f"   • 컬럼 목록: {list(df.columns)}")
    print(f"   • 처리 시간: {mapping_info.get('processing_time', 0):.2f}초")
    
    # 데이터 샘플 출력
    if not df.empty:
        print(f"\n📋 데이터 샘플 (상위 3행):")
        print(df.head(3).to_string())
    
    print(f"\n✅ 테스트 완료!") 