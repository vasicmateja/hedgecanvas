"""Pure filtering/sorting/extraction over already-verified historical DataFrames.

No arithmetic on stored values happens here: filtering, sorting by
``decision_month`` (a zero-padded ``YYYY-MM`` string that sorts correctly
lexicographically -- no date parsing needed), and reading out
``wealth_end`` as stored. Nothing here recomputes, reconstructs, or
renormalizes anything.
"""

from __future__ import annotations

import pandas as pd

from hedgecanvas.historical.keys import HistoricalView, is_valid_asset, strategies_for_view


def filter_metrics(dataframe: pd.DataFrame, asset: str, view: HistoricalView) -> pd.DataFrame:
    """Rows for the given literal asset and the view's canonical strategy set."""
    if not is_valid_asset(asset):
        raise ValueError(f"Unknown canonical asset key: {asset!r}")
    strategies = strategies_for_view(view)
    mask = (dataframe["asset"] == asset) & (dataframe["strategy"].isin(strategies))
    return dataframe.loc[mask].copy()


def filter_wealth_path(dataframe: pd.DataFrame, asset: str, view: HistoricalView) -> pd.DataFrame:
    """Rows for the given literal asset and view, sorted by decision_month.

    Returns the full filtered/sorted row set including ``wealth_end`` --
    the sole source for the wealth chart. No reconstruction, no
    cumulative product, no use of ``wealth_start`` or ``strategy_return``.
    """
    filtered = filter_metrics(dataframe, asset, view)
    return filtered.sort_values("decision_month", kind="stable").reset_index(drop=True)


def wealth_end_series(dataframe: pd.DataFrame, asset: str, strategy: str) -> pd.DataFrame:
    """The stored (decision_month, wealth_end) pairs for one asset+strategy,
    in decision_month order -- exactly as recorded, nothing derived.
    """
    mask = (dataframe["asset"] == asset) & (dataframe["strategy"] == strategy)
    rows = dataframe.loc[mask, ["decision_month", "wealth_end"]]
    return rows.sort_values("decision_month", kind="stable").reset_index(drop=True)
