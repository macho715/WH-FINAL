import pandas as pd
import os
from datetime import datetime

def analyze_hvdc_data():
    """HVDC WAREHOUSE_HITACHI(HE) 파일 데이터 분석"""
    
    file_path = "data/HVDC WAREHOUSE_HITACHI(HE).xlsx"
    
    if not os.path.exists(file_path):
        print(f"❌ 파일이 존재하지 않습니다: {file_path}")
        return
    
    try:
        # 다양한 엔진으로 시도
        engines = ['openpyxl', 'xlrd', None]
        df = None
        
        for engine in engines:
            try:
                if engine:
                    df = pd.read_excel(file_path, engine=engine)
                else:
                    df = pd.read_excel(file_path)
                print(f"✅ Excel 파일 로드 성공 (engine: {engine or 'auto'})")
                break
            except Exception as e:
                print(f"🔄 {engine or 'auto'} 엔진 실패: {e}")
                continue
        
        if df is None:
            print("❌ 모든 엔진으로 파일 로드 실패")
            return
        
        print("\n🔍 HVDC WAREHOUSE_HITACHI(HE) 데이터 분석")
        print("=" * 60)
        print(f"📊 총 행 수: {len(df):,}")
        print(f"📋 총 컬럼 수: {len(df.columns)}")
        print()
        
        # 컬럼 정보
        print("📋 주요 컬럼:")
        for i, col in enumerate(df.columns[:15]):  # 처음 15개 컬럼만 표시
            non_null_count = df[col].count()
            print(f"  {i+1:2d}. {col}: {non_null_count:,}개 (비어있음: {len(df) - non_null_count:,}개)")
        
        if len(df.columns) > 15:
            print(f"  ... 및 {len(df.columns) - 15}개 추가 컬럼")
        print()
        
        # 날짜 관련 컬럼 분석
        date_columns = []
        for col in df.columns:
            col_lower = str(col).lower()
            if any(keyword in col_lower for keyword in ['date', 'eta', 'etd', 'markaz', 'indoor', 'outdoor']):
                date_columns.append(col)
        
        print(f"📅 날짜/위치 관련 컬럼 ({len(date_columns)}개):")
        for col in date_columns[:10]:  # 처음 10개만 표시
            non_null_count = df[col].count()
            print(f"   - {col}: {non_null_count:,}개")
        print()
        
        # 핵심 컬럼 분석
        key_columns = ['Shipment No', 'Category', 'CNTR Unstuffing Q\'TY', 'CNTR Stuffing Q\'TY']
        print("🔑 핵심 컬럼 분석:")
        for col in key_columns:
            if col in df.columns:
                non_null_count = df[col].count()
                unique_count = df[col].nunique()
                print(f"   - {col}: {non_null_count:,}개 (고유값: {unique_count:,}개)")
        print()
        
        # **3691번 행 이후 데이터 확인 (메모리 이슈 해결 확인)**
        print("🔍 3691번 행 이후 데이터 상태 (누락 데이터 문제 확인):")
        if len(df) > 3691:
            after_3691 = df.iloc[3691:]
            print(f"   ✅ 3691번 이후 행 수: {len(after_3691):,}")
            
            # 날짜 컬럼별 데이터 수 확인
            date_data_count = 0
            for col in date_columns[:5]:  # 처음 5개 날짜 컬럼만 확인
                after_3691_count = after_3691[col].count()
                date_data_count += after_3691_count
                print(f"   - {col}: {after_3691_count:,}개")
            
            print(f"   📊 3691번 이후 총 날짜 데이터: {date_data_count:,}개")
            
            # 메모리에서 언급된 377개 누락 데이터 문제 확인
            if date_data_count > 0:
                print("   ✅ 데이터 누락 문제 해결됨: 3691번 이후에도 날짜 데이터 존재")
            else:
                print("   ❌ 데이터 누락 지속: 3691번 이후 날짜 데이터 없음")
        else:
            print(f"   ⚠️  총 행수({len(df)})가 3691보다 작음")
        print()
        
        # 마지막 데이터 확인
        print("📋 마지막 10행 샘플:")
        last_rows = df.tail(10)
        for idx, row in last_rows.iterrows():
            shipment = row.get('Shipment No', 'N/A')
            category = row.get('Category', 'N/A')
            print(f"   행 {idx+1}: Shipment={shipment}, Category={category}")
        
        # **결론**
        print("\n🎯 결론:")
        if len(df) >= 3691:
            after_3691_count = len(df) - 3691
            print(f"   - 총 데이터 행: {len(df):,}개")
            print(f"   - 3691번 이후: {after_3691_count:,}개")
            if after_3691_count >= 300:  # 약 377개 근처
                print("   ✅ 메모리의 377개 누락 데이터 문제가 해결된 것으로 보임")
            else:
                print("   ⚠️  일부 데이터는 여전히 처리되지 않을 수 있음")
        
    except Exception as e:
        print(f"❌ 데이터 분석 중 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_hvdc_data() 