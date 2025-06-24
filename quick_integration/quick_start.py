#!/usr/bin/env python3
"""
HVDC 빠른 시작 스크립트
===================

기존 시스템에서 바로 사용할 수 있는 원라이너
"""

import sys
from pathlib import Path

# HVDC 통합 경로 자동 추가
integration_path = Path(__file__).parent
if str(integration_path) not in sys.path:
    sys.path.insert(0, str(integration_path))

# HVDC 모듈 임포트
import hvdc_quick

def demo():
    """데모 실행"""
    print("🚀 HVDC 빠른 통합 데모")
    print("=" * 40)
    
    # 시스템 상태 확인
    status = hvdc_quick.get_status()
    print(f"시스템 준비: {'✅' if status['processor_ready'] else '❌'}")
    print(f"버전: {status['version']}")
    
    # 샘플 테스트
    test_result = hvdc_quick.quick_test()
    print(f"테스트 결과: {'✅' if test_result.get('sample_data_test') else '❌'}")
    
    print("\n📋 사용법:")
    print("1. import hvdc_quick")
    print("2. data = hvdc_quick.load_data('file.xlsx')")
    print("3. report = hvdc_quick.generate_report(data, 'report.xlsx')")
    
    return status['processor_ready']

if __name__ == "__main__":
    demo()
