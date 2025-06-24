#!/usr/bin/env python3
"""
HVDC 데이터 변환/정규화 엔진
==========================

데이터 타입 변환, 결측치 처리, 이상치 보정, 값 정규화를 담당
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class DataTransformer:
    """데이터 정규화/타입변환/결측치/이상치 처리 클래스"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Args:
            config: 변환 설정 딕셔너리
        """
        self.config = config or {}
        
    def normalize_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """데이터 타입 정규화"""
        logger.info("🔄 데이터 타입 정규화 시작...")
        
        df_result = df.copy()
        
        # 날짜 컬럼 정규화
        date_columns = ['hasDate', 'ETD/ATD', 'ETA/ATA']
        for col in date_columns:
            if col in df_result.columns:
                df_result[col] = pd.to_datetime(df_result[col], errors='coerce')
                logger.info(f"   • {col}: datetime 변환 완료")
        
        # 수치 컬럼 정규화
        numeric_columns = ['hasVolume', 'hasAmount', 'hasQuantity']
        for col in numeric_columns:
            if col in df_result.columns:
                df_result[f'{col}_numeric'] = pd.to_numeric(df_result[col], errors='coerce')
                logger.info(f"   • {col}: numeric 변환 완료")
        
        # 문자열 컬럼 정규화
        string_columns = ['hasSite', 'hasCurrentStatus', 'hasCaseNumber']
        for col in string_columns:
            if col in df_result.columns:
                df_result[col] = df_result[col].astype(str).str.strip()
                logger.info(f"   • {col}: string 정규화 완료")
        
        logger.info(f"✅ 데이터 타입 정규화 완료: {df_result.shape}")
        return df_result
    
    def handle_missing(self, df: pd.DataFrame) -> pd.DataFrame:
        """결측치 처리"""
        logger.info("🔄 결측치 처리 시작...")
        
        df_result = df.copy()
        
        # 날짜 결측치 → 현재 시간
        date_columns = ['hasDate']
        for col in date_columns:
            if col in df_result.columns:
                missing_count = df_result[col].isna().sum()
                if missing_count > 0:
                    df_result[col] = df_result[col].fillna(pd.Timestamp.now())
                    logger.info(f"   • {col}: {missing_count}개 결측치 → 현재시간")
        
        # 수치 결측치 → 0
        numeric_columns = [col for col in df_result.columns if col.endswith('_numeric')]
        for col in numeric_columns:
            missing_count = df_result[col].isna().sum()
            if missing_count > 0:
                df_result[col] = df_result[col].fillna(0)
                logger.info(f"   • {col}: {missing_count}개 결측치 → 0")
        
        # 문자열 결측치 → 'UNKNOWN'
        string_columns = ['hasSite', 'hasCurrentStatus', 'hasCaseNumber']
        for col in string_columns:
            if col in df_result.columns:
                missing_count = df_result[col].isna().sum()
                if missing_count > 0:
                    df_result[col] = df_result[col].fillna('UNKNOWN')
                    logger.info(f"   • {col}: {missing_count}개 결측치 → UNKNOWN")
        
        logger.info(f"✅ 결측치 처리 완료: {df_result.shape}")
        return df_result
    
    def fix_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """이상치 보정"""
        logger.info("🔄 이상치 보정 시작...")
        
        df_result = df.copy()
        
        # 수량/금액 음수값 보정
        numeric_columns = [col for col in df_result.columns if col.endswith('_numeric')]
        for col in numeric_columns:
            if col in df_result.columns:
                negative_count = (df_result[col] < 0).sum()
                if negative_count > 0:
                    df_result[col] = df_result[col].abs()
                    logger.info(f"   • {col}: {negative_count}개 음수값 → 절댓값")
        
        # 극단적 이상치 제거 (IQR 방법)
        for col in numeric_columns:
            if col in df_result.columns and df_result[col].std() > 0:
                Q1 = df_result[col].quantile(0.25)
                Q3 = df_result[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                outlier_count = ((df_result[col] < lower_bound) | (df_result[col] > upper_bound)).sum()
                if outlier_count > 0:
                    df_result[col] = df_result[col].clip(lower=lower_bound, upper=upper_bound)
                    logger.info(f"   • {col}: {outlier_count}개 이상치 보정")
        
        logger.info(f"✅ 이상치 보정 완료: {df_result.shape}")
        return df_result
    
    def normalize_locations(self, df: pd.DataFrame) -> pd.DataFrame:
        """위치명 정규화 (대소문자, 공백 등)"""
        logger.info("🔄 위치명 정규화 시작...")
        
        df_result = df.copy()
        
        if 'hasSite' in df_result.columns:
            # 대소문자 통일 및 공백 제거
            df_result['hasSite_normalized'] = (
                df_result['hasSite']
                .str.strip()
                .str.upper()
                .replace('', 'UNKNOWN')
            )
            
            # 일반적인 변형 통일
            location_mapping = {
                'DAS': 'DAS',
                'Das': 'DAS',
                'das': 'DAS',
                'D.A.S': 'DAS',
                'D A S': 'DAS'
            }
            
            df_result['hasSite_normalized'] = df_result['hasSite_normalized'].replace(location_mapping)
            
            unique_locations = df_result['hasSite_normalized'].value_counts()
            logger.info(f"   • 정규화된 위치: {len(unique_locations)}개")
            for loc, count in unique_locations.head(10).items():
                logger.info(f"     - {loc}: {count}건")
        
        logger.info(f"✅ 위치명 정규화 완료: {df_result.shape}")
        return df_result
    
    def run_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """모든 변환 작업을 순차적으로 실행"""
        logger.info("🚀 전체 데이터 변환 파이프라인 시작")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        
        # 1. 타입 정규화
        df_result = self.normalize_types(df)
        
        # 2. 결측치 처리
        df_result = self.handle_missing(df_result)
        
        # 3. 이상치 보정
        df_result = self.fix_outliers(df_result)
        
        # 4. 위치명 정규화
        df_result = self.normalize_locations(df_result)
        
        # 5. 최종 검증
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        logger.info("=" * 60)
        logger.info("🎉 전체 데이터 변환 파이프라인 완료!")
        logger.info(f"📊 처리 결과:")
        logger.info(f"   • 원본: {df.shape} → 결과: {df_result.shape}")
        logger.info(f"   • 처리 시간: {processing_time:.2f}초")
        logger.info(f"   • 컬럼 수: {len(df.columns)} → {len(df_result.columns)}")
        
        return df_result
    
    def validate_transformation(self, df_original: pd.DataFrame, df_transformed: pd.DataFrame) -> Dict[str, Any]:
        """변환 결과 검증"""
        validation_result = {
            "original_shape": df_original.shape,
            "transformed_shape": df_transformed.shape,
            "data_loss": len(df_original) - len(df_transformed),
            "new_columns": list(set(df_transformed.columns) - set(df_original.columns)),
            "missing_data": {},
            "data_types": {}
        }
        
        # 결측치 검사
        for col in df_transformed.columns:
            missing_count = df_transformed[col].isna().sum()
            if missing_count > 0:
                validation_result["missing_data"][col] = missing_count
        
        # 데이터 타입 검사
        for col in df_transformed.columns:
            validation_result["data_types"][col] = str(df_transformed[col].dtype)
        
        logger.info(f"📋 변환 검증 결과: {validation_result}")
        
        return validation_result

# 편의 함수들
def quick_transform(df: pd.DataFrame) -> pd.DataFrame:
    """빠른 변환 (기본 설정)"""
    transformer = DataTransformer()
    return transformer.run_all(df)

def validate_data_quality(df: pd.DataFrame) -> Dict[str, Any]:
    """데이터 품질 검증"""
    quality_report = {
        "total_records": len(df),
        "total_columns": len(df.columns),
        "missing_data_summary": {},
        "data_type_summary": {},
        "duplicates": df.duplicated().sum(),
        "memory_usage": df.memory_usage(deep=True).sum() / 1024 / 1024  # MB
    }
    
    # 결측치 요약
    for col in df.columns:
        missing_count = df[col].isna().sum()
        missing_pct = (missing_count / len(df)) * 100
        if missing_count > 0:
            quality_report["missing_data_summary"][col] = {
                "count": missing_count,
                "percentage": round(missing_pct, 2)
            }
    
    # 데이터 타입 요약
    type_counts = df.dtypes.value_counts()
    quality_report["data_type_summary"] = type_counts.to_dict()
    
    return quality_report

if __name__ == "__main__":
    # 테스트 실행
    print("🧪 DataTransformer 테스트")
    
    # 샘플 데이터 생성
    sample_data = {
        'hasSite': ['DAS', 'AGI', 'MIR', 'Das', None],
        'hasVolume': ['100.5', '200', '-50', 'invalid', '300'],
        'hasAmount': [1000, 2000, -500, None, 3000],
        'hasDate': ['2024-01-01', '2024-01-02', None, '2024-01-04', '2024-01-05']
    }
    
    df_test = pd.DataFrame(sample_data)
    print(f"원본 데이터:\n{df_test}")
    
    # 변환 실행
    transformer = DataTransformer()
    df_transformed = transformer.run_all(df_test)
    print(f"\n변환된 데이터:\n{df_transformed}")
    
    # 품질 검증
    quality_report = validate_data_quality(df_transformed)
    print(f"\n데이터 품질 리포트:\n{quality_report}") 