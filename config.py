# config.py
from pathlib import Path
import yaml, datetime as dt

BASE_DIR = Path(__file__).resolve().parent

def load_expected_stock(as_of: str | None = None) -> dict:
    """
    기대 재고(YAML) 로드.
    as_of: 'YYYY-MM-DD' 문자열 — 없으면 오늘 날짜 사용.
    """
    as_of = as_of or dt.date.today().isoformat()
    cfg_file = BASE_DIR / "expected_stock.yml"
    with open(cfg_file, "r", encoding="utf-8") as fp:
        data: dict = yaml.safe_load(fp)
    return data.get(as_of, {})            # 날짜 키가 없으면 빈 dict 