# 🚨 HVDC 온톨로지 기준 분류 시스템 - 중대한 문제점 발견

## 📋 문제 요약
**온톨로지 정의와 실제 데이터 간의 완전한 불일치**로 인해 창고/현장 분류가 실패하고 있습니다.

## 🔍 상세 문제 분석

### 1. 온톨로지 정의 오류
```python
# 현재 온톨로지 정의 (잘못됨)
INDOOR_WAREHOUSE = ["DSV Indoor", "DSV Al Markaz", "Hauler Indoor"]    # ❌ 실제 데이터에 없음
OUTDOOR_WAREHOUSE = ["DSV Outdoor", "DSV MZP", "MOSB"]                # ❌ 실제 데이터에 없음
SITE = ["AGI", "DAS", "MIR", "SHU"]                                   # ❌ DAS는 창고임
DANGEROUS_CARGO = ["AAA Storage", "Dangerous Storage"]                # ❌ 실제 데이터에 없음
```

### 2. 실제 데이터 구조
```
hasSite 컬럼 실제 값 분포:
- SHU: 1,456건 → 현장(Site)
- AGI: 1,341건 → 현장(Site)  
- DAS: 1,289건 → 창고(Warehouse) ⚠️ 온톨로지에서는 Site로 분류됨
- MIR: 1,244건 → 현장(Site)
- Das: 16건 → 창고(Warehouse, 대소문자 변형) ⚠️ 온톨로지에서는 Site로 분류됨
```

### 3. 분류 결과 오류
```
온톨로지 기준 실행 결과:
✅ 현장 데이터: 5,330개 레코드 (AGI + DAS + MIR + SHU + Das)
❌ 창고 데이터: 0개 레코드 (온톨로지 정의된 창고들이 실제 데이터에 없음)

올바른 분류 결과:
✅ 현장 데이터: 4,041개 레코드 (AGI + MIR + SHU)
✅ 창고 데이터: 1,305개 레코드 (DAS + Das)
```

## 🛠️ **해결방안**

### 방안 1: 실제 데이터 기준 온톨로지 수정
```python
# 수정된 온톨로지 정의 (실제 데이터 기준)
WAREHOUSE = ["DAS", "Das"]           # ✅ 실제 존재하는 창고
SITE = ["AGI", "MIR", "SHU"]         # ✅ 실제 현장들

def get_location_group_real_data(name):
    """실제 데이터 기준 온톨로지 분류"""
    if pd.isna(name):
        return "UNKNOWN"
    
    n = str(name).strip()
    
    if n in ["DAS", "Das"]:          # 실제 창고
        return "Warehouse"
    elif n in ["AGI", "MIR", "SHU"]: # 실제 현장
        return "Site"
    else:
        return "UNKNOWN"
```

### 방안 2: 하이브리드 접근법 (온톨로지 + 실제 데이터)
```python
# 온톨로지 정의 (이론적)
ONTOLOGY_WAREHOUSE = ["DSV Indoor", "DSV Al Markaz", "Hauler Indoor", "DSV Outdoor", "DSV MZP", "MOSB"]
ONTOLOGY_SITE = ["AGI", "MIR", "SHU"]
ONTOLOGY_DANGEROUS = ["AAA Storage", "Dangerous Storage"]

# 실제 데이터 매핑 (실무적)
ACTUAL_WAREHOUSE = ["DAS", "Das"]
ACTUAL_SITE = ["AGI", "MIR", "SHU"]

def get_location_group_hybrid(name):
    """하이브리드 온톨로지 분류 (실제 데이터 우선)"""
    if pd.isna(name):
        return "UNKNOWN"
    
    n = str(name).strip()
    
    # 실제 데이터 우선 체크
    if n in ACTUAL_WAREHOUSE:
        return "Warehouse"
    elif n in ACTUAL_SITE:
        return "Site"
    
    # 온톨로지 정의 체크 (미래 확장용)
    elif n in ONTOLOGY_WAREHOUSE:
        return "IndoorWarehouse"  # 또는 "OutdoorWarehouse"
    elif n in ONTOLOGY_SITE:
        return "Site"
    elif n in ONTOLOGY_DANGEROUS:
        return "DangerousCargoWarehouse"
    else:
        return "UNKNOWN"
```

## 📊 **수정 후 예상 결과**

### 창고별 월별 입출고 흐름:
```
창고명    위치그룹    월       입고    출고    재고
DAS      Warehouse   2023-12   100     0      100
DAS      Warehouse   2024-01   150     0      250
Das      Warehouse   2023-12   5       0      5
Das      Warehouse   2024-01   8       0      13
```

### 현장별 배송 현황:
```
현장명    월       배송수량    배송횟수    배송금액
AGI      2023-12   200        15         240000
MIR      2023-12   180        12         216000
SHU      2023-12   220        18         264000
```

## ⚡ **즉시 실행 가능한 수정 코드**

```python
# hvdc_ontology_based_classifier.py 수정
WAREHOUSE = ["DAS", "Das"]  # 실제 데이터 기준
SITE = ["AGI", "MIR", "SHU"]

def get_location_group_fixed(name):
    """수정된 온톨로지 기준 위치 그룹 분류"""
    if pd.isna(name):
        return "UNKNOWN"
    
    n = str(name).strip()
    
    if n in WAREHOUSE:
        return "Warehouse"
    elif n in SITE:
        return "Site"
    else:
        return "UNKNOWN"
```

## 🎯 **검증 방법**

### 1. 분류 정확성 검증
```python
# 예상 결과
validation_result = {
    'Warehouse': 1305,  # DAS(1289) + Das(16)
    'Site': 4041,       # AGI(1341) + MIR(1244) + SHU(1456)
    'UNKNOWN': 0        # 모든 데이터가 분류됨
}
```

### 2. 창고 흐름 분석 검증
- DAS 창고의 월별 입고/출고/재고 데이터 정상 생성 확인
- 18개월 전체 기간 데이터 누락 없음 확인

### 3. 현장 배송 분석 검증
- AGI, MIR, SHU 현장별 배송 현황 정상 생성 확인
- 월별 배송수량, 배송횟수, 배송금액 정확성 확인

## 📈 **수정 후 기대 효과**

1. **✅ 창고 분석 정상화**: 1,305개 창고 레코드 정상 처리
2. **✅ 현장 분석 정확성**: 4,041개 현장 레코드 정확 분류
3. **✅ 데이터 손실 제로**: 5,346개 전체 레코드 100% 분류
4. **✅ 월별 흐름 분석**: 창고별 18개월 입출고 흐름 정상 생성
5. **✅ Excel 리포트**: 8시트 완전 생성 (현재 2시트 → 8시트)

## ⚠️ **중요 결론**

**온톨로지 이론과 실제 데이터 간의 간극**이 시스템 실패의 주요 원인입니다. 
**실제 데이터를 우선**으로 하여 온톨로지를 조정하는 것이 실무적으로 올바른 접근법입니다.

---
**다음 단계**: 실제 데이터 기준으로 온톨로지 정의를 수정하고 재실행하여 완전한 8시트 리포트를 생성해야 합니다. 