import json
import openpyxl



def read_single_case(file_path: str, sheet_name: str = None):
    """
    读取 Excel，返回 list[dict]
    固定 7 列结构，表头不匹配返回空列表
    """
    wb = openpyxl.load_workbook(file_path, read_only=True)
    ws = wb[sheet_name] if sheet_name else wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        wb.close()
        return []
    headers = [str(h) for h in rows[0]]
    if headers != ['CaseID', '用例名称', '是否执行', '请求体', '预期状态码', '断言', '描述']:
        wb.close()
        return []
    data = []
    for row in rows[1:]:
        row_dict = {}
        for idx, header in enumerate(headers):
            value = row[idx]
            if value is None:
                value = ""
            elif isinstance(value, str):
                value = value.strip()
                if (value.startswith("{") and value.endswith("}")) or \
                   (value.startswith("[") and value.endswith("]")):
                    try:
                        value = json.loads(value)
                    except json.JSONDecodeError:
                        pass
            row_dict[header] = value
        if not row_dict.get("请求体") or not row_dict.get("预期状态码") or not row_dict.get("断言"):
            wb.close()
            return []
        if ";" in row_dict["断言"]:
            row_dict["断言"] = [a.strip() for a in row_dict["断言"].split(";") if a.strip()]
        data.append(row_dict)
    wb.close()
    return data

if __name__ == '__main__':
    print(read_single_case('./xlsx/test.xlsx'))
