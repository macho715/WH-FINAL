"""
HVDC 빠른 통합 - 고급 사용법
==========================

기존 시스템과의 고급 통합 예시
"""

import sys
from pathlib import Path
import pandas as pd
from datetime import datetime
import logging

# HVDC 통합 모듈 경로 추가
hvdc_integration_path = Path(__file__).parent / "quick_integration"
sys.path.insert(0, str(hvdc_integration_path))

import hvdc_quick

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WarehouseManager:
    """창고 관리 클래스 - HVDC 통합"""
    
    def __init__(self):
        self.hvdc_ready = hvdc_quick.get_status()["processor_ready"]
        self.last_update = None
        
        if self.hvdc_ready:
            logger.info("✅ HVDC 시스템 준비 완료")
        else:
            logger.error("❌ HVDC 시스템 초기화 실패")
    
    def process_daily_data(self, excel_file: str) -> dict:
        """일일 데이터 처리"""
        if not self.hvdc_ready:
            return {"success": False, "error": "HVDC 시스템 미준비"}
        
        try:
            # HVDC로 데이터 처리
            result = hvdc_quick.process_warehouse_data(excel_file)
            
            if result["success"]:
                # 추가 비즈니스 로직
                self._update_database(result["data"])
                self._send_notifications(result)
                
                self.last_update = datetime.now()
                logger.info(f"일일 데이터 처리 완료: {result['rows']} 행")
                
            return result
            
        except Exception as e:
            logger.error(f"일일 데이터 처리 실패: {e}")
            return {"success": False, "error": str(e)}
    
    def _update_database(self, df: pd.DataFrame):
        """데이터베이스 업데이트 (예시)"""
        # 기존 시스템 데이터베이스에 업데이트
        logger.info(f"데이터베이스 업데이트: {len(df)} 레코드")
        
        # 예시: 데이터베이스 연결 및 업데이트
        # db.update_inventory(df)
        pass
    
    def _send_notifications(self, result: dict):
        """알림 전송 (예시)"""
        if result["success"]:
            # 성공 알림
            logger.info("처리 완료 알림 전송")
            # send_email("success", result)
        else:
            # 실패 알림
            logger.error("처리 실패 알림 전송")
            # send_alert("failure", result)
    
    def generate_dashboard_data(self) -> dict:
        """대시보드용 데이터 생성"""
        if not self.hvdc_ready:
            return {"error": "HVDC 시스템 미준비"}
        
        try:
            status = hvdc_quick.get_status()
            
            dashboard_data = {
                "system_status": "online" if status["processor_ready"] else "offline",
                "last_update": self.last_update.isoformat() if self.last_update else None,
                "version": status["version"]
            }
            
            # 최근 처리 결과가 있으면 추가
            if status["last_processing"]["status"] == "success":
                last = status["last_processing"]
                dashboard_data.update({
                    "total_records": last["total_rows"],
                    "total_amount": last["total_amount"],
                    "categories": last["categories"],
                    "processing_time": last["processing_info"]["processing_time"]
                })
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"대시보드 데이터 생성 실패: {e}")
            return {"error": str(e)}
    
    def health_check(self) -> bool:
        """헬스체크"""
        try:
            test_result = hvdc_quick.quick_test()
            return test_result.get("processor_init", False)
        except:
            return False

# 배치 작업 예시
def nightly_batch_job():
    """야간 배치 작업"""
    manager = WarehouseManager()
    
    if not manager.health_check():
        logger.error("❌ 헬스체크 실패 - 배치 작업 중단")
        return False
    
    # 데이터 파일 검색
    data_dir = Path("data")
    excel_files = list(data_dir.glob("*.xlsx"))
    
    for excel_file in excel_files:
        logger.info(f"처리 중: {excel_file}")
        result = manager.process_daily_data(str(excel_file))
        
        if not result["success"]:
            logger.error(f"파일 처리 실패: {excel_file}")
            return False
    
    logger.info("✅ 야간 배치 작업 완료")
    return True

# 웹 API 통합 예시
from flask import Flask, jsonify, request

app = Flask(__name__)
warehouse_manager = WarehouseManager()

@app.route("/api/warehouse/status")
def get_status():
    """시스템 상태 API"""
    return jsonify(warehouse_manager.generate_dashboard_data())

@app.route("/api/warehouse/process", methods=["POST"])
def process_data():
    """데이터 처리 API"""
    file_path = request.json.get("file_path")
    
    if not file_path:
        return jsonify({"error": "file_path 필수"}), 400
    
    result = warehouse_manager.process_daily_data(file_path)
    return jsonify(result)

@app.route("/api/warehouse/health")
def health_check():
    """헬스체크 API"""
    is_healthy = warehouse_manager.health_check()
    return jsonify({"healthy": is_healthy}), 200 if is_healthy else 503

if __name__ == "__main__":
    # 배치 작업 실행
    if len(sys.argv) > 1 and sys.argv[1] == "batch":
        nightly_batch_job()
    else:
        # 웹 서버 실행
        app.run(host="0.0.0.0", port=5000)
