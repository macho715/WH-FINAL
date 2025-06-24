"""
HVDC 빠른 통합 - 기본 사용법
==========================

기존 시스템에 이 코드를 추가하면 즉시 HVDC 기능 사용 가능
"""

import sys
from pathlib import Path

# HVDC 통합 모듈 경로 추가 (한 번만 설정)
hvdc_integration_path = Path(__file__).parent / "quick_integration"
sys.path.insert(0, str(hvdc_integration_path))

import hvdc_quick

def main():
    """기본 사용 예시"""
    
    # 1. 단순 파일 처리
    print("🔄 창고 데이터 처리 중...")
    result = hvdc_quick.process_warehouse_data("data/warehouse.xlsx")
    
    if result["success"]:
        print(f"✅ 처리 완료: {result['rows']} 행")
        print(f"⏱️ 처리 시간: {result['processing_time']:.2f} 초")
        
        # 2. 재고 계산
        inventory = hvdc_quick.calculate_inventory(result["data"])
        print(f"💰 총 금액: {inventory['total_amount']:,.2f}")
        
        # 3. 보고서 생성
        report_path = hvdc_quick.generate_report(result["data"], "monthly_report.xlsx")
        print(f"📊 보고서 생성: {report_path}")
        
    else:
        print(f"❌ 처리 실패: {result['error']}")

def quick_pipeline():
    """전체 파이프라인 실행"""
    
    # 원스톱 처리 (파일 → 보고서)
    result = hvdc_quick.process_file("data/warehouse.xlsx", generate_report=True)
    
    if result["success"]:
        print("✅ 파이프라인 완료")
        if "report_generated" in result:
            print(f"📊 보고서: {result['report_generated']}")
    else:
        print(f"❌ 파이프라인 실패: {result['error']}")

def monitor_system():
    """시스템 모니터링"""
    
    status = hvdc_quick.get_status()
    
    print("🔍 HVDC 시스템 상태:")
    print(f"   준비 상태: {'✅' if status['processor_ready'] else '❌'}")
    print(f"   버전: {status['version']}")
    
    if status['last_processing']['status'] == 'success':
        last = status['last_processing']
        print(f"   마지막 처리: {last['total_rows']} 행")
        print(f"   처리 시간: {last['processing_info']['processing_time']:.2f}초")

if __name__ == "__main__":
    # 사용 예시 실행
    main()
    quick_pipeline()
    monitor_system()
