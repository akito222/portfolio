"""Tiny interpreter for the DataBrew recipe in databrew/recipe.json (pandas).

Only the operations used by this project are implemented. The point is to verify,
offline, that the *same recipe file* produces the same schema on two different
datasets - i.e. what "reusing a recipe" means.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def _lower(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    df[p["targetColumn"]] = df[p["sourceColumn"]].astype("string").str.lower()
    return df


def _group_by(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    keys = json.loads(p["sourceColumns"])
    aggs = json.loads(p["groupByAggFunctionOptions"])
    if p.get("useNewDataFrame", "false") == "true":
        raise NotImplementedError("only 'group as new column' is used in this project")
    func_map = {"MEAN": "mean", "SUM": "sum", "COUNT": "count", "MIN": "min", "MAX": "max"}
    for agg in aggs:
        values = df.groupby(keys, dropna=False)[agg["sourceColumnName"]].transform(func_map[agg["functionName"]])
        df[agg["targetColumnName"]] = (
            values.astype("float64") if agg.get("targetColumnDataType") == "double" else values
        )
    return df


def _one_hot(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    col = p["sourceColumn"]
    for value in sorted(df[col].dropna().unique()):
        df[f"{col}_{value}"] = (df[col] == value).astype("int32")
    return df


def _rename(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    return df.rename(columns={p["sourceColumn"]: p["targetColumn"]})


OPERATIONS = {
    "LOWER": _lower,
    "GROUP_BY": _group_by,
    "ONE_HOT_ENCODING": _one_hot,
    "RENAME": _rename,
}


def load_recipe(path: Path) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def apply_recipe(df: pd.DataFrame, steps: list[dict]) -> pd.DataFrame:
    df = df.copy()
    for step in steps:
        action = step["Action"]
        df = OPERATIONS[action["Operation"]](df, action.get("Parameters", {}))
    return df
