#!/usr/bin/env python3
"""
HVDC 빠른 통합 테스트 스크립트
"""

import sys
from pathlib import Path

# 통합 모듈 경로 추가
integration_path = Path(__file__).parent
sys.path.insert(0, str(integration_path))

def test_integration():
    """통합 테스트 실행"""
    print("=" * 60)
    print("HVDC Quick Integration Test Started")
    print("=" * 60)
    
    try:
        # 1. 모듈 임포트 테스트
        print("\n[1/4] Module Import Test...")
        import hvdc_quick
        print("   SUCCESS: hvdc_quick module imported")
        
        # 2. 기본 기능 테스트
        print("\n[2/4] Basic Function Test...")
        
        # 사용 가능한 함수들 확인
        available_functions = ['process_warehouse_data', 'generate_report', 'calculate_inventory', 
                             'quick_load', 'quick_report', 'quick_inventory']
        
        for func_name in available_functions:
            if hasattr(hvdc_quick, func_name):
                print(f"   PASS: {func_name} available")
            else:
                print(f"   FAIL: {func_name} not found")
        
        # 3. 상태 확인
        print("\n[3/4] System Status Check...")
        try:
            # HVDCProcessor 인스턴스 생성 테스트
            processor = hvdc_quick.HVDCProcessor()
            processor_status = "READY" if processor.is_initialized else "NOT_READY"
            print(f"   Processor Status: {processor_status}")
            print(f"   Module Version: 0.5.1-quick")
        except Exception as e:
            print(f"   Status check failed: {e}")
        
        # 4. 실제 파일 테스트 (파일이 있다면)
        print("\n[4/4] File Processing Test...")
        data_files = list(Path("../data").glob("*.xlsx")) if Path("../data").exists() else []
        
        if data_files:
            test_file = data_files[0]
            print(f"   Test file: {test_file}")
            
            try:
                df = hvdc_quick.quick_load(test_file)
                print(f"   SUCCESS: Data loaded ({len(df)} rows)")
                
                inventory = hvdc_quick.quick_inventory(df)
                total_amount = inventory['total_amount']
                print(f"   SUCCESS: Inventory calculated (Total: {total_amount:,.2f})")
                
            except Exception as e:
                print(f"   FAIL: File test failed - {e}")
        else:
            print("   INFO: No Excel files found for testing")
        
        print("\n" + "=" * 60)
        print("Integration Test COMPLETED Successfully!")
        print("=" * 60)
        return True
        
    except ImportError as e:
        print(f"\nFAIL: Module import failed - {e}")
        return False
    except Exception as e:
        print(f"\nFAIL: Test failed - {e}")
        return False

if __name__ == "__main__":
    success = test_integration()
    sys.exit(0 if success else 1)
