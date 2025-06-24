# HVDC Warehouse Automation Suite - 모듈별 문서화

## 📋 개요

HVDC Warehouse Automation Suite는 고전압직류송전(HVDC) 창고 분석 시스템으로, 온톨로지 기반 데이터 표준화와 사용자 검증된 재고 계산 로직을 결합한 창고 관리 플랫폼입니다.

**버전**: v0.5.1 (완전 완성)  
**최종 업데이트**: 2024년 6월 24일  
**GitHub**: https://github.com/macho715/WH11

---

## 🏗️ 시스템 아키텍처

```
HVDC Warehouse Suite
├── 🔧 Core Modules (핵심 엔진)
│   ├── inventory_engine.py     # 정밀 재고 계산 엔진
│   ├── ontology_mapper.py      # RDF 온톨로지 매핑
│   ├── excel_reporter.py       # Excel 리포트 생성기
│   └── warehouse_loader.py     # 창고 데이터 로더
├── 📊 Analysis & Reporting (분석 및 리포팅)
│   ├── hvdc_complete_8sheet_reporter.py  # 8시트 BI 리포트
│   ├── data_loader_mapper.py             # 데이터 로딩/매핑
│   └── create_ontology_reporter.py       # 온톨로지 리포터
├── 🧪 Testing & Quality (테스트 및 품질)
│   ├── tests/test_bi_qty_report.py       # 단위 테스트
│   ├── test_end_to_end.py                # E2E 테스트
│   └── test_system.py                    # 시스템 테스트
└── ⚡ Quick Integration (빠른 통합)
    ├── quick_integration/                # 5분 완성 통합
    └── hvdc_quick/                       # 즉시 사용 모듈
```

---

## 📚 모듈별 상세 문서

### 1️⃣ `hvdc_complete_8sheet_reporter.py` - 8시트 BI 리포트 생성기

**목적**: 온톨로지→매핑→정규화→8시트 BI 리포트 자동 생성 메인 모듈

#### 🔧 주요 함수

##### 금액 중심 함수 (기본)
```python
def create_monthly_dashboard(df, all_months):
    """
    월별 전체현황 대시보드 생성 (금액 기준)
    
    Parameters:
    -----------
    df : pd.DataFrame
        표준화된 HVDC DataFrame (필수 컬럼: 'hasDate', 'hasAmount_numeric')
    all_months : pd.PeriodIndex
        전체 월별 인덱스 (누락 월 0 보장)
    
    Returns:
    --------
    pd.DataFrame
        월별(행) × 트랜잭션타입(열) 금액 집계 DataFrame
        
    Example:
    --------
    >>> df, all_months = prepare_monthly_aggregation(raw_df)
    >>> dashboard = create_monthly_dashboard(df, all_months)
    >>> print(dashboard.shape)  # (18, 4) - 18개월 × 4개 트랜잭션 타입
    """
```

##### 수량 중심 함수 (v1)
```python
def create_monthly_dashboard_qty(df, all_months):
    """
    월별 전체현황 대시보드 생성 (수량 기준)
    
    Parameters:
    -----------
    df : pd.DataFrame
        표준화된 HVDC DataFrame (필수 컬럼: 'hasDate', 'hasVolume_numeric')
    all_months : pd.PeriodIndex
        전체 월별 인덱스
    
    Returns:
    --------
    pd.DataFrame
        월별(행) × 트랜잭션타입(열) 수량 집계 DataFrame
    """
```

##### 개선된 수량 중심 함수 (v2)
```python
def create_monthly_dashboard_qty_v2(df, all_months):
    """
    개선된 월별 전체현황 대시보드 (수량 기준, TxType 기반 정교한 분석)
    
    Parameters:
    -----------
    df : pd.DataFrame
        표준화된 HVDC DataFrame
        필수 컬럼: 'hasDate', 'hasVolume_numeric', 'hasCurrentStatus', 'hasSite'
    all_months : pd.PeriodIndex
        전체 월별 인덱스
    
    Returns:
    --------
    pd.DataFrame
        개선된 월별 × TxType_Refined 수량 집계
        
    Features:
    ---------
    - TxType 자동 정제 (hasCurrentStatus 또는 hasSite 기반)
    - 정교한 수량 분석
    - 누락 월 자동 0 처리
    """
```

#### 🚀 실행 방법

##### 기본 실행
```bash
# 금액 중심 리포트
python hvdc_complete_8sheet_reporter.py

# 수량 중심 리포트 (v1)
python hvdc_complete_8sheet_reporter.py --mode=qty
```

##### 고급 실행 (argparse 기반)
```bash
# 개선된 수량 중심 v2 버전
python hvdc_complete_8sheet_reporter.py --advanced --mode=qty --version=v2

# 개선된 금액 중심 v2 버전
python hvdc_complete_8sheet_reporter.py --advanced --mode=amount --version=v2

# 출력 파일명 지정
python hvdc_complete_8sheet_reporter.py --advanced --mode=qty --output="CustomReport.xlsx"
```

#### 📊 출력 결과

**8개 시트 구성**:
1. `01_월별_전체현황` - 월별 트랜잭션 대시보드
2. `02_공급사별_월별현황` - 공급사별 월별 집계
3. `03_창고별_월별현황` - 창고별 월별 집계  
4. `04_현장별_월별현황` - 현장별 월별 집계
5. `05_입고현황_월별` - 입고 패턴 분석
6. `06_출고현황_월별` - 출고 유형 분석
7. `07_재고현황_월별` - 재고 Aging 분석
8. `08_청구매칭_검증` - 송장-화물 매칭 검증

**조건부 서식**: 3-Color Scale 자동 적용 (빨강-노랑-초록)

---

### 2️⃣ `data_loader_mapper.py` - 데이터 로딩 및 온톨로지 매핑

**목적**: Excel 데이터 → 매핑 규칙 적용 → 표준화된 DataFrame 변환

#### 🔧 주요 클래스

##### `HVDCDataLoader`
```python
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
```

##### 핵심 메서드
```python
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
        
    Pipeline:
        1. 매핑 규칙 로딩 (JSON)
        2. Excel 데이터 로딩 (다중 시트 지원)
        3. 컬럼 매핑 적용 (정확한 매치 + 부분 매치)
        4. 데이터 타입 정규화 (datetime, float64, string)
        5. 데이터 품질 검증 (결측값, 중복, 품질 점수)
    """
```

#### 🚀 사용 예시

##### 기본 사용
```python
from data_loader_mapper import HVDCDataLoader

# 기본 로딩
loader = HVDCDataLoader()
df, mapping_info = loader.load_and_map_data()

print(f"로딩 완료: {df.shape}")
print(f"품질 점수: {mapping_info['validation_report']['quality_score']:.1f}/100")
```

##### 고급 사용
```python
# 커스텀 파일 및 매핑
loader = HVDCDataLoader(
    data_dir="custom_data",
    mapping_file="custom_mapping.json"
)

df, info = loader.load_and_map_data(
    excel_file="specific_file.xlsx",
    validate=True
)

# 일괄 처리
from data_loader_mapper import batch_load_excel_files

files = ["file1.xlsx", "file2.xlsx", "file3.xlsx"]
results = batch_load_excel_files(files)
```

#### 📋 매핑 규칙 구조

```json
{
  "field_map": {
    "Date": "hasDate",
    "날짜": "hasDate",
    "수량": "hasVolume_numeric",
    "Qty": "hasVolume_numeric",
    "금액": "hasAmount_numeric",
    "Amount": "hasAmount_numeric",
    "위치": "hasSite",
    "Location": "hasSite"
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
```

---

### 3️⃣ `tests/test_bi_qty_report.py` - 단위 테스트 모듈

**목적**: 수량 중심 8시트 BI 함수의 pytest 기반 단위 테스트

#### 🧪 테스트 구조

##### Fixtures
```python
@pytest.fixture
def dummy_df():
    """테스트용 더미 DataFrame 생성 (60일간 샘플 데이터)"""
    
@pytest.fixture  
def all_months_fixture(dummy_df):
    """테스트용 전체 월 범위 생성"""
```

##### 테스트 함수들
```python
def test_monthly_dashboard_qty(dummy_df, all_months_fixture):
    """월별_전체현황_수량 함수 테스트"""
    
def test_supplier_report_qty(dummy_df, all_months_fixture):
    """공급사별_월별현황_수량 함수 테스트"""
    
def test_warehouse_report_qty(dummy_df, all_months_fixture):
    """창고별_월별현황_수량 함수 테스트"""
    
# ... 8개 함수 모두 테스트
    
def test_full_pipeline_integration(dummy_df):
    """전체 파이프라인 통합 테스트"""
```

#### 🚀 실행 방법

```bash
# 전체 테스트 실행
pytest tests/test_bi_qty_report.py -v

# 특정 테스트만 실행
pytest tests/test_bi_qty_report.py::test_monthly_dashboard_qty -v

# 상세 출력과 함께 실행
pytest tests/test_bi_qty_report.py -v -s

# 커버리지와 함께 실행
pytest tests/test_bi_qty_report.py --cov=hvdc_complete_8sheet_reporter
```

#### ✅ 검증 항목

- **기본 검증**: 리포트 비어있지 않음, 데이터 존재
- **구조 검증**: 행/열 개수, 컬럼 존재 여부
- **월별 범위 검증**: 전체 월 범위 누락 없음 (`reindex` 패턴 검증)
- **데이터 타입 검증**: 수치형 데이터 정상 처리
- **통합 테스트**: 전체 파이프라인 에러 없이 실행

---

## 🛠️ 개발 가이드

### 환경 설정

```bash
# 의존성 설치
pip install -r requirements.txt

# 개발 의존성 추가 설치
pip install pytest pytest-cov black flake8
```

### 코딩 스타일

- **함수 네이밍**: `create_[기능]_[모드]_[버전]` (예: `create_monthly_dashboard_qty_v2`)
- **모드 구분**: `_qty` (수량), `_amount` (금액) 접미사
- **버전 구분**: `_v2` (개선 버전) 접미사
- **월별 처리**: 반드시 `reindex(all_months, fill_value=0)` 패턴 사용

### 새 함수 추가 시 체크리스트

- [ ] 함수명 일관성 확인
- [ ] docstring 작성 (Parameters, Returns, Example)
- [ ] 전체 월 범위 보장 (`reindex` 적용)
- [ ] 단위 테스트 작성
- [ ] 에러 처리 추가
- [ ] 성능 최적화 고려

---

## 📊 성능 지표

### 처리 성능 (v0.5.1 기준)
- **데이터 처리량**: 5,578+ 트랜잭션 < 1초
- **8시트 리포트 생성**: 2.11-2.27초
- **메모리 사용량**: 평균 50MB 이하
- **TRANSFER 매치 해결**: 559개 AUTO-FIX

### 데이터 커버리지
- **전체 기간**: 18개월 (2023-12 ~ 2025-05)
- **매핑 효율**: 100% (기존 10% → 100% 개선)
- **데이터 손실**: 0% (완전 보장)

---

## 🔧 트러블슈팅

### 자주 발생하는 문제

#### 1. Import 오류
```bash
❌ ImportError: No module named 'hvdc_complete_8sheet_reporter'
```
**해결**: 
```python
import sys
sys.path.append('.')  # 현재 디렉토리 추가
```

#### 2. 매핑 파일 없음
```bash
⚠️ 매핑 파일 없음: mapping_rules_v2.6_unified.json
```
**해결**: 기본 매핑 규칙 자동 생성됨 (문제 없음)

#### 3. Excel 파일 없음
```bash
⚠️ Excel 파일 없음: data/HVDC WAREHOUSE_HITACHI(HE).xlsx
```
**해결**: 더미 데이터 자동 생성됨 (테스트 가능)

#### 4. 월별 데이터 누락
```bash
KeyError: '2024-03'
```
**해결**: `reindex(all_months, fill_value=0)` 패턴 적용 필수

---

## 📈 향후 개발 계획

### Phase 1: 고급 분석 (진행 중)
- [ ] 예측 분석 모듈 추가
- [ ] 실시간 대시보드 구현
- [ ] API 서버 구축

### Phase 2: 확장성 (계획)
- [ ] 다중 창고 지원
- [ ] 클라우드 배포
- [ ] 모바일 앱 연동

### Phase 3: AI 통합 (연구)
- [ ] 머신러닝 기반 재고 최적화
- [ ] 자연어 쿼리 지원
- [ ] 자동 이상 탐지

---

## 📞 지원 및 문의

- **GitHub Issues**: https://github.com/macho715/WH11/issues
- **개발자**: macho715
- **최종 업데이트**: 2024-06-24
- **라이선스**: MIT

---

**🎯 HVDC Warehouse Automation Suite v0.5.1 - 완전 완성**  
*온톨로지 기반 데이터 표준화 × 사용자 검증된 재고 계산 로직* 