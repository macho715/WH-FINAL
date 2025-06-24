import pandas as pd
from excel_reporter import generate_full_dashboard
import datetime

print('=== HVDC 데이터 컬럼 분석 ===')

# 데이터 로드
df = pd.read_excel('data/HVDC WAREHOUSE_HITACHI(HE).xlsx')
print(f'총 {len(df)}건, {len(df.columns)}개 컬럼')

print('\n=== 전체 컬럼 목록 ===')
for i, col in enumerate(df.columns):
    print(f'{i+1:2d}. "{col}"')

print('\n=== 샘플 데이터 (첫 3행) ===')
print(df.head(3).to_string())

# Amount 관련 컬럼 찾기
print('\n=== Amount/수량 관련 컬럼 검색 ===')
amount_keywords = ['amount', 'amt', 'qty', 'quantity', 'price', '금액', '수량', '가격', 'value']
amount_cols = []
for col in df.columns:
    for keyword in amount_keywords:
        if keyword.lower() in col.lower():
            amount_cols.append(col)
            break

print('발견된 Amount 관련 컬럼:', amount_cols)

# 컬럼 이름 표준화 시도
print('\n=== 컬럼 표준화 시도 ===')
df_clean = df.copy()

# 기본적인 표준화
column_mapping = {}
for col in df.columns:
    clean_col = col.strip().lower()
    if 'amount' in clean_col or 'amt' in clean_col:
        column_mapping[col] = 'Amount'
        break

if column_mapping:
    print('적용할 컬럼 매핑:', column_mapping)
    df_clean = df_clean.rename(columns=column_mapping)
else:
    # Amount 컬럼이 없으면 첫 번째 숫자 컬럼을 Amount로 사용
    numeric_cols = df_clean.select_dtypes(include=['number']).columns
    if len(numeric_cols) > 0:
        column_mapping[numeric_cols[0]] = 'Amount'
        df_clean = df_clean.rename(columns={numeric_cols[0]: 'Amount'})
        print(f'첫 번째 숫자 컬럼을 Amount로 사용: {numeric_cols[0]} -> Amount')

# Excel 리포트 재시도
print('\n=== Excel 리포트 생성 재시도 ===')
timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M')
report_name = f'HVDC_온톨로지매핑리포트_{timestamp}.xlsx'

try:
    generate_full_dashboard(df_clean, report_name)
    print(f'✅ Excel 리포트 생성 성공: {report_name}')
    
    import os
    if os.path.exists(report_name):
        size = os.path.getsize(report_name) / 1024
        print(f'   파일 크기: {size:.1f} KB')
except Exception as e:
    print(f'❌ Excel 리포트 생성 실패: {e}')
    
    # 디버깅용 정보
    print('\n=== 디버깅 정보 ===')
    print('Excel 리포터가 요구하는 컬럼들:')
    print('- Amount (필수)')
    print('현재 데이터프레임 컬럼:', list(df_clean.columns)) 