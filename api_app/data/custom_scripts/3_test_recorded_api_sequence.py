#!/usr/bin/env python3
"""Executable pytest case generated from a recorded browser API flow."""

from __future__ import annotations

import json
import os
import re
from copy import deepcopy
from typing import Any

import pytest
import requests


REQUESTS: list[dict[str, Any]] = [{'name': 'listExams',
  'group': 'recorded_api_flow',
  'url': "https://{'__var__': 'domain'}/qbank/{'__var__': 'env'}/exam/exam/listExams",
  'method': 'POST',
  'headers': {'__var__': 'user_exam_app'},
  'params': {},
  'json_data': {'classifyAlias': 'teach_material', 'page': 1, 'pageSize': 20, 'name': '', 'gradeId': 0},
  'data': None,
  'extract': [],
  'expected_status': 200},
 {'name': 'listExams',
  'group': 'recorded_api_flow',
  'url': "https://{'__var__': 'domain'}/qbank/{'__var__': 'env'}/exam/exam/listExams",
  'method': 'POST',
  'headers': {'__var__': 'user_exam_app'},
  'params': {},
  'json_data': {'classifyAlias': 'teach_material', 'page': 1, 'pageSize': 20, 'name': '测试', 'gradeId': 0},
  'data': None,
  'extract': [],
  'expected_status': 200}]
REF_KEY = "__var__"
# 字符串内嵌占位（URL 中）：{'__var__': '键'}
INLINE_REF_PATTERN = re.compile(r'''\{\s*['"]__var__['"]\s*:\s*['"]([^'"]+)['"]\s*\}''')


@pytest.fixture(scope="session")
def recorded_session() -> requests.Session:
    """Use a dedicated fixture name so this file can coexist with spectesting."""
    with requests.Session() as client:
        yield client


def get_json_path(value: Any, path: str) -> Any:
    current = value
    tokens = path.replace("$", "", 1).strip(".")
    if not tokens:
        return current
    for part in tokens.split("."):
        while "[" in part:
            key, rest = part.split("[", 1)
            if key:
                current = current[key]
            list_index, part = rest.split("]", 1)
            current = current[int(list_index)]
        if part:
            current = current[part]
    return current


def resolve_refs(value: Any, variables: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        if set(value) == {REF_KEY}:
            return variables[value[REF_KEY]]
        return {key: resolve_refs(child, variables) for key, child in value.items()}
    if isinstance(value, list):
        return [resolve_refs(child, variables) for child in value]
    if isinstance(value, str):
        # 字符串内嵌占位替换，未命中保留原样
        return INLINE_REF_PATTERN.sub(lambda m: str(variables.get(m.group(1), m.group(0))), value)
    return value


def response_json_or_none(response: requests.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None


def step_label(index: int, request_item: dict[str, Any]) -> str:
    label = request_item.get("name") or request_item.get("group") or request_item["url"]
    return f"step {index} ({label})"


def test_recorded_api_sequence(recorded_session: requests.Session) -> None:
    # 变量池：平台执行前注入同目录 script_vars.json（按脚本文件名索引）
    # 两级结构：__common__ 公共层（domain/env/全量头）全执行一份 + 本脚本入参层，合并后入参最高优先级；
    # 兼容旧格式（无 __common__ 键时本层即完整种子）
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "script_vars.json"), encoding="utf-8") as f:
        _vars_data = json.load(f)
    variables: dict[str, Any] = {**(_vars_data.get('__common__') or {}), **(_vars_data.get(os.path.basename(__file__)) or {})}

    for index, request_item in enumerate(REQUESTS, start=1):
        method = request_item["method"].upper()
        url = resolve_refs(request_item["url"], variables)
        response = recorded_session.request(
            method=method,
            url=url,
            headers=resolve_refs(deepcopy(request_item.get("headers") or {}), variables),
            params=resolve_refs(deepcopy(request_item.get("params") or {}), variables),
            json=resolve_refs(deepcopy(request_item.get("json_data")), variables),
            data=resolve_refs(deepcopy(request_item.get("data")), variables),
            timeout=float(os.getenv("RECORDER_TIMEOUT", "30")),
        )

        expected_status = int(request_item.get("expected_status") or 200)
        assert response.status_code == expected_status, (
            f"{step_label(index, request_item)} {method} {url} returned {response.status_code}, "
            f"expected {expected_status}; response={response.text[:2000]}"
        )

        response_json = response_json_or_none(response)
        for extractor in request_item.get("extract", []):
            assert response_json is not None, (
                f"{step_label(index, request_item)} has extractors but response is not JSON"
            )
            variables[extractor["name"]] = get_json_path(
                response_json, extractor["path"]
            )
