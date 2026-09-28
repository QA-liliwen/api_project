#!/usr/bin/env python3
"""Executable pytest case generated from a recorded browser API flow."""

from __future__ import annotations

import os
from copy import deepcopy
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import pytest
import requests


REQUESTS: list[dict[str, Any]] = [{'name': 'listExams',
  'group': 'recorded_api_flow',
  'url': 'https://devapi1.lingshi.com/qbank/vs2/exam/exam/listExams',
  'method': 'POST',
  'headers': {'Content-Type': 'application/json;charset=UTF-8',
              'Referer': 'https://vs2php.51tyty.com/',
              'XX-Token': '462821:1850198136:f48cc157-b4f1-4837-ab79-c0a65822abba:93d360c9695ac331bd14215574b273ca:1201v',
              'serverId': '1201',
              'accept-language': 'zh-CN,zh;q=0.9',
              'content-type': 'application/json;charset=UTF-8',
              'priority': 'u=1, i',
              'referer': 'https://vs2php.51tyty.com/',
              'serverid': '1201',
              'xx-token': '462821:1850198136:f48cc157-b4f1-4837-ab79-c0a65822abba:93d360c9695ac331bd14215574b273ca:1201v'},
  'params': {},
  'json_data': {'classifyAlias': 'teach_material', 'page': 1, 'pageSize': 20, 'name': '', 'gradeId': 0},
  'data': None,
  'extract': [],
  'expected_status': 200},
 {'name': 'listExams',
  'group': 'recorded_api_flow',
  'url': 'https://devapi1.lingshi.com/qbank/vs2/exam/exam/listExams',
  'method': 'POST',
  'headers': {'Content-Type': 'application/json;charset=UTF-8',
              'Referer': 'https://vs2php.51tyty.com/',
              'XX-Token': '462821:1850198136:f48cc157-b4f1-4837-ab79-c0a65822abba:93d360c9695ac331bd14215574b273ca:1201v',
              'serverId': '1201',
              'accept-language': 'zh-CN,zh;q=0.9',
              'content-type': 'application/json;charset=UTF-8',
              'priority': 'u=1, i',
              'referer': 'https://vs2php.51tyty.com/',
              'serverid': '1201',
              'xx-token': '462821:1850198136:f48cc157-b4f1-4837-ab79-c0a65822abba:93d360c9695ac331bd14215574b273ca:1201v'},
  'params': {},
  'json_data': {'classifyAlias': 'teach_material', 'page': 1, 'pageSize': 20, 'name': '测试', 'gradeId': 0},
  'data': None,
  'extract': [],
  'expected_status': 200}]
REF_KEY = "__var__"


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
    return value


def target_url(recorded_url: str) -> str:
    """Optionally replace the recorded origin while preserving path and query."""
    override = os.getenv("RECORDER_BASE_URL", "").strip()
    if not override:
        return recorded_url
    source = urlsplit(recorded_url)
    target = urlsplit(override if "://" in override else f"https://{override}")
    return urlunsplit((target.scheme, target.netloc, source.path, source.query, source.fragment))


def response_json_or_none(response: requests.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None


def step_label(index: int, request_item: dict[str, Any]) -> str:
    label = request_item.get("name") or request_item.get("group") or request_item["url"]
    return f"step {index} ({label})"


def test_recorded_api_sequence(recorded_session: requests.Session) -> None:
    variables: dict[str, Any] = {}

    for index, request_item in enumerate(REQUESTS, start=1):
        method = request_item["method"].upper()
        url = target_url(request_item["url"])
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
