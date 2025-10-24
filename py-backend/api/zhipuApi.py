# ... existing code ...
import os
import time
import json
from typing import Optional, Union, Dict, Any
import requests
# 警告：生产环境不要把 Token 暴露到前端，建议通过后端调用或代理。

ZHIPU_UPLOAD_URL = "https://open.bigmodel.cn/api/paas/v4/files/parser/create?file"
ZHIPU_RESULT_BASE = "https://open.bigmodel.cn/api/paas/v4/files/parser/result"
DEFAULT_ZHIPU_API_TOKEN = "0b85869d46624981bcf282c08425132d.nCgWxCcKe3TrOwkW"

def _detect_file_type(file_path: Union[str, os.PathLike]) -> str:
    """
    根据文件扩展名判断类型，映射到 BigModel 的 file_type 值。
    """
    try:
        ext = os.path.splitext(str(file_path))[1].lower()
    except Exception:
        return "PDF"
    ext_dict = {
        ".pdf": "PDF",
        ".doc": "DOC",
        ".docx": "DOCX",
        ".doc": "DOC",
        ".png": "IMAGE",
        ".jpg": "IMAGE",
        ".jpeg": "IMAGE",
        ".webp": "IMAGE",
        ".gif": "IMAGE",
        ".md": "MD",
        ".txt": "TXT",
    }
    return ext_dict.get(ext, "")


def zhipu_create_task(
    file_path: Union[str, os.PathLike],
    token: str,
    tool_type: str = "lite",
) -> str:
    """
    上传文件并创建解析任务，返回 task_id。
    """
    if not token:
        raise ValueError("缺少智谱 Authorization Token")
    if not file_path or not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    filename = os.path.basename(str(file_path))
    file_type = _detect_file_type(file_path)

    with open(file_path, "rb") as fp:
        files = {"file": (filename, fp)}
        data = {
            "tool_type": tool_type,
            "file_type": file_type,
        }
        headers = {
            "Authorization": f"Bearer {token}",
        }
        resp = requests.post(ZHIPU_UPLOAD_URL, headers=headers, files=files, data=data)

    # 尝试解析 JSON，否则读取文本
    try:
        data = resp.json()
    except ValueError:
        data = {"message": resp.text}

    if not resp.ok:
        raise RuntimeError(f"上传失败({resp.status_code}): {data.get('message') or resp.reason}")

    task_id = data.get("task_id")
    if not task_id:
        raise RuntimeError(f"未返回任务ID: {json.dumps(data, ensure_ascii=False)}")

    return task_id


def zhipu_get_result(task_id: str, token: str) -> Dict[str, Any]:
    """
    根据任务ID获取解析结果（JSON）。
    返回示例：{ status, message, content, task_id, parsing_result_url }
    """
    if not token:
        raise ValueError("缺少智谱 Authorization Token")
    if not task_id:
        raise ValueError("缺少 task_id")

    url = f"{ZHIPU_RESULT_BASE}/{task_id}/text"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers)

    try:
        data = resp.json()
    except ValueError:
        data = {"message": resp.text}

    if not resp.ok:
        raise RuntimeError(f"结果获取失败({resp.status_code}): {data.get('message') or resp.reason}")

    return data


def recognize_document(
    file_path: Union[str, os.PathLike],
    options: Optional[Dict[str, Any]] = None,
    credentials: Optional[Dict[str, Any]] = None,
    max_retries: int = 3,
    retry_interval_ms: int = 2000,
    tool_type: str = "lite",
) -> Dict[str, Any]:
    """
    识别并解析文件为文本内容（最多重试 max_retries 次）。
    """
    if not file_path:
        raise ValueError("未提供文件")
    token = (credentials or {}).get("token")
    if not token:
        raise ValueError("缺少智谱 Authorization Token")

    # 1) 创建解析任务
    task_id = zhipu_create_task(file_path, token, tool_type=tool_type)

    # 2) 轮询获取结果
    last_result: Optional[Dict[str, Any]] = None
    attempts = max(1, int(max_retries))

    for attempt in range(attempts):
        last_result = zhipu_get_result(task_id, token)
        status = str(last_result.get("status", "")).lower()

        if status == "succeeded":
            return last_result
        if status == "failed":
            raise RuntimeError(f"解析失败: {last_result.get('message') or '未知错误'}")

        # 继续等待下一次重试（如状态为 processing/pending 等）
        if attempt < attempts - 1:
            time.sleep(max(0, int(retry_interval_ms)) / 1000.0)

    # 重试结束仍未成功
    raise TimeoutError(f"解析结果未就绪，已重试{attempts}次")


def extract_markdown(response: Union[str, Dict[str, Any], None]) -> str:
    """
    提取文本内容（content 字段）。
    """
    if response is None:
        return ""
    try:
        if isinstance(response, str):
            json_obj = json.loads(response)
            return str(json_obj.get("content") or "")
        if isinstance(response, dict):
            return str(response.get("content") or "")
    except Exception:
        return ""


def zhipu_get_file_content(
    file_path: Union[str, os.PathLike],
    token: str = DEFAULT_ZHIPU_API_TOKEN,
    max_retries: int = 3,
    retry_interval_ms: int = 2000,
    tool_type: str = "lite",
) -> Optional[str]:
    """
    先上传文件（创建任务），再轮询结果，最后提取 content 字段。
    成功返回文件内容字符串；失败返回 None。
    """
    try:
        result = recognize_document(
            file_path=file_path,
            credentials={"token": token},
            max_retries=max_retries,
            retry_interval_ms=retry_interval_ms,
            tool_type=tool_type,
        )
        content = extract_markdown(result)
        return content if content else None
    except Exception as exc:
        print(f"智谱文档解析失败: {exc}")
        return None