"""ontology_mapper.py – v0.4 (2025‑06‑24)

HVDC Warehouse / 물류 DataFrame → RDF 트리플 변환기
====================================================

주요 변경 내역 (v0.4)
---------------------
* **`dataframe_to_rdf(df, output_path)`** 헬퍼 함수 추가 → 테스트·파이프라인에서 직접 호출 가능.
* `hasAmount`(xsd:decimal) 포함한 field→property 매핑 룰(`mapping_rules_v2.5.json`) 기본 로드.
* `__all__` 에 `dataframe_to_rdf` 노출.

사용 예시
~~~~~~~~
>>> from ontology_mapper import dataframe_to_rdf
>>> rdf_path = dataframe_to_rdf(df, "rdf_output/transport_events.ttl")

"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any

import pandas as pd
from rdflib import Graph, Namespace, Literal, RDF, XSD
import yaml
import json

__all__ = ["dataframe_to_rdf"]

# ---------------------------------------------------------------------------
# 매핑 룰 로드
# ---------------------------------------------------------------------------
_DEFAULT_RULE_PATH = Path(__file__).with_suffix("").parent / "mapping_rules_v2.5.json"

with open(_DEFAULT_RULE_PATH, "r", encoding="utf-8") as f:
    _RULES: Dict[str, Any] = json.load(f)

NS = {k: Namespace(v) for k, v in _RULES["namespaces"].items()}
_FIELD_MAP: Dict[str, str] = _RULES["field_map"]


def _create_graph() -> Graph:
    g = Graph()
    for prefix, ns in NS.items():
        g.bind(prefix, ns)
    return g


def dataframe_to_rdf(df: pd.DataFrame, output_path: str | Path = "rdf_output/output.ttl") -> Path:
    """DataFrame → RDF Turtle 파일로 직렬화.

    Parameters
    ----------
    df : pd.DataFrame
        표준 컬럼(Shipment No, Operation Month, Amount …)을 포함한 데이터프레임
    output_path : str | Path, default "rdf_output/output.ttl"
        출력 .ttl 파일 경로
    Returns
    -------
    Path
        직렬화된 Turtle 파일 경로
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    g = _create_graph()

    for idx, row in df.iterrows():
        # 각 행마다 TransportEvent_* 식별자 생성
        event_uri = NS["ex"][f"TransportEvent_{idx+1:05d}"]
        g.add((event_uri, RDF.type, NS["ex"].TransportEvent))

        for col, val in row.items():
            if pd.isna(val):
                continue  # 결측치는 스킵
            if col not in _FIELD_MAP:
                continue  # 매핑되지 않은 컬럼은 무시

            prop = NS["ex"][_FIELD_MAP[col]]

            # 숫자/문자/날짜 타입별 Literal 캐스팅
            if isinstance(val, (int, float, pd.Int64Dtype)):
                lit = Literal(val, datatype=XSD.decimal)
            else:
                try:
                    # 날짜 문자열 → xsd:date
                    lit = Literal(pd.to_datetime(val).date(), datatype=XSD.date)
                except (ValueError, TypeError):
                    lit = Literal(str(val))

            g.add((event_uri, prop, lit))

    g.serialize(destination=str(output_path), format="turtle")
    return output_path 