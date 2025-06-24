"""
HVDC 핵심 처리 모듈
"""

import pandas as pd
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Union

# HVDC 시스템 경로 추가
HVDC_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(HVDC_ROOT))

class HVDCProcessor:
    """HVDC 핵심 처리기"""
    
    def __init__(self):
        self.last_result = None
        self.is_initialized = False
        self._initialize()
    
    def _initialize(self):
        """초기화"""
        try:
            # 핵심 모듈 임포트
            global warehouse_loader, excel_reporter, main_process
            
            from warehouse_loader import load_hvdc_warehouse_file
            from excel_reporter import generate_full_dashboard
            from main import main as main_process
            
            self.warehouse_loader = load_hvdc_warehouse_file
            self.excel_reporter = generate_full_dashboard
            self.main_process = main_process
            
            self.is_initialized = True
            print("✅ HVDC 모듈 초기화 완료")
            
        except ImportError as e:
            print(f"❌ HVDC 모듈 초기화 실패: {e}")
            self.is_initialized = False
    
    def process(self, excel_file: Union[str, Path], 
                output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        창고 데이터 처리
        
        Args:
            excel_file: Excel 파일 경로
            output_file: 출력 파일명 (옵션)
        
        Returns:
            처리 결과 딕셔너리
        """
        if not self.is_initialized:
            return {"success": False, "error": "모듈 초기화 실패"}
        
        try:
            start_time = datetime.now()
            
            # 1. 데이터 로드
            print(f"📄 데이터 로딩: {excel_file}")
            df = self.warehouse_loader(excel_file)
            
            # 2. 기본 검증
            if df.empty:
                return {"success": False, "error": "빈 데이터셋"}
            
            # 3. 보고서 생성 (옵션)
            report_path = None
            if output_file:
                print(f"📊 보고서 생성: {output_file}")
                report_path = self.excel_reporter(df, output_file)
            
            # 4. 결과 준비
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            result = {
                "success": True,
                "data": df,
                "rows": len(df),
                "columns": list(df.columns),
                "processing_time": processing_time,
                "report_path": str(report_path) if report_path else None,
                "timestamp": end_time.isoformat()
            }
            
            self.last_result = result
            print(f"✅ 처리 완료 ({processing_time:.2f}초, {len(df)}행)")
            
            return result
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            print(f"❌ 처리 실패: {e}")
            return error_result
    
    def get_summary(self) -> Dict[str, Any]:
        """처리 결과 요약"""
        if not self.last_result:
            return {"status": "no_data"}
        
        if not self.last_result["success"]:
            return {"status": "error", "error": self.last_result["error"]}
        
        df = self.last_result["data"]
        
        summary = {
            "status": "success",
            "total_rows": len(df),
            "total_amount": df.get("Amount", pd.Series()).sum(),
            "categories": df.get("Category", pd.Series()).nunique(),
            "date_range": {
                "start": df.get("Billing month", pd.Series()).min(),
                "end": df.get("Billing month", pd.Series()).max()
            },
            "processing_info": {
                "timestamp": self.last_result["timestamp"],
                "processing_time": self.last_result["processing_time"]
            }
        }
        
        return summary
    
    def run_full_pipeline(self, data_dir: str = "data") -> Dict[str, Any]:
        """전체 파이프라인 실행"""
        if not self.is_initialized:
            return {"success": False, "error": "모듈 초기화 실패"}
        
        try:
            print("🚀 HVDC 전체 파이프라인 실행")
            
            # 환경 변수 설정
            original_cwd = os.getcwd()
            os.chdir(HVDC_ROOT)
            
            # 전체 시스템 실행
            success = self.main_process()
            
            # 원래 디렉토리로 복원
            os.chdir(original_cwd)
            
            return {
                "success": success,
                "timestamp": datetime.now().isoformat(),
                "data_dir": data_dir
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
