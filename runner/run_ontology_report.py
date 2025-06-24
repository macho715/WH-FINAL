#!/usr/bin/env python3
"""
HVDC 고급 v2 버전 실행 스크립트
python run_advanced_v2.py --mode=qty --version=v2
"""

import sys
import argparse
from hvdc_complete_8sheet_reporter import (
    load_ontology_mapping_data, 
    prepare_monthly_aggregation,
    save_8sheet_excel_report_v2,
    save_8sheet_excel_report_qty,
    save_8sheet_excel_report
)
import datetime

def main():
    """고급 v2 파이프라인 실행"""
    parser = argparse.ArgumentParser(description="HVDC 고급 v2 8시트 BI 리포트 실행기")
    parser.add_argument("--mode", choices=["amount", "qty"], default="qty", 
                       help="집계 기준 (amount: 금액 중심, qty: 수량 중심)")
    parser.add_argument("--output", default=None, help="출력 파일명 지정")
    parser.add_argument("--version", choices=["v1", "v2"], default="v2", 
                       help="함수 버전 (v1: 기본, v2: 개선)")
    
    args = parser.parse_args()
    
    print(f"🚀 HVDC 고급 v2 파이프라인 시작")
    print(f"🎯 모드: {args.mode.upper()}, 버전: {args.version}")
    print("=" * 80)
    
    start_time = datetime.datetime.now()
    
    try:
        # 온톨로지→매핑→DataFrame 준비
        print("🔄 1단계: 데이터 로딩 및 매핑...")
        df, mapping_rules = load_ontology_mapping_data()
        df, all_months = prepare_monthly_aggregation(df)
        
        # 파일명 결정
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M')
        output_name = args.output or f"HVDC_Advanced_8Sheet_{args.mode.upper()}_{args.version}_{timestamp}.xlsx"
        
        print(f"🔄 2단계: {args.version} 버전 {args.mode} 모드 리포트 생성...")
        
        # 버전별 저장 함수 호출
        if args.version == "v2":
            final_path = save_8sheet_excel_report_v2(df, all_months, output_name, mode=args.mode)
        else:
            # v1은 기존 함수 사용
            if args.mode == 'qty':
                final_path = save_8sheet_excel_report_qty(df, all_months, output_name)
            else:
                final_path = save_8sheet_excel_report(df, all_months, output_name)
        
        # 최종 결과
        end_time = datetime.datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        print("\n" + "=" * 80)
        print(f"🎉 HVDC 고급 {args.mode.upper()} BI 리포트 v{args.version} 완료!")
        print("=" * 80)
        
        print(f"📊 처리 결과:")
        print(f"   • 모드: {args.mode.upper()}")
        print(f"   • 버전: {args.version}")
        print(f"   • 데이터 건수: {len(df):,}건")
        print(f"   • 전체 월 범위: {len(all_months)}개월")
        print(f"   • 처리 시간: {processing_time:.2f}초")
        print(f"   • 출력 파일: {final_path}")
        
        print(f"\n🎯 고급 v2 파이프라인 실행 성공!")
        print(f"📁 결과 파일: {final_path}")
        
        return final_path, df, all_months
        
    except Exception as e:
        print(f"❌ 고급 파이프라인 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None

if __name__ == "__main__":
    main() 