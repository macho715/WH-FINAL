import pytest
from config import load_expected_stock
from main import run_full_pipeline, calculate_daily_stock

@pytest.mark.parametrize("as_of", ["2025-07-01", "2025-07-02"])
def test_stock_matches_expected(as_of):
    events = run_full_pipeline(cutoff_date=as_of)
    stock  = calculate_daily_stock(events).loc[as_of]
    expect = load_expected_stock(as_of)

    for wh, exp in expect.items():
        assert abs(stock[wh] - exp) <= 2, f"{wh} 불일치 (Δ {stock[wh]-exp})" 