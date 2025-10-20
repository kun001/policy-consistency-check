"""
    使用硅基流动的API端口
"""

from typing import List, Sequence, Union

import requests

SILICONFLOW_API_BASE_URL = "https://api.siliconflow.cn/v1"
EMBEDDING_URL = f"{SILICONFLOW_API_BASE_URL}/embeddings"
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-large-zh-v1.5"
# DEFAULT_EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-8B"
MAX_EMBED_INPUT_CHARS = 512


def _normalize_inputs(texts: Union[str, Sequence[str]]) -> List[str]:
    """
    将输入统一为字符串列表
    """
    if isinstance(texts, str):
        return [texts]

    if isinstance(texts, Sequence):
        if not texts:
            raise ValueError("输入列表不能为空")

        normalized: List[str] = []
        for item in texts:
            if not isinstance(item, str):
                raise ValueError("输入列表必须仅包含字符串")
            normalized.append(item)

        return normalized

    raise TypeError(f"不支持的输入类型: {type(texts)}")


def get_embeddings_from_siliconflow(
    inputs: Union[str, Sequence[str]],
    api_token: str,
    model: str = DEFAULT_EMBEDDING_MODEL,
    timeout: Union[int, float] = 10,
) -> dict:
    """
    调用硅基流动嵌入API，返回 embedding 结果
    - 输入文本将被截断至最多 512 字（MAX_EMBED_INPUT_CHARS）
    """
    if not api_token:
        raise ValueError("必须提供有效的 API token")

    try:
        normalized_inputs = _normalize_inputs(inputs)
    except (TypeError, ValueError) as error:
        print(f"参数错误: {error}")
        return {}

    # 限制每段文本最多 512 字，超过则截断
    truncated_inputs = [text[:MAX_EMBED_INPUT_CHARS] for text in normalized_inputs]

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "input": truncated_inputs,
    }

    try:
        response = requests.post(
            EMBEDDING_URL,
            json=payload,
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as error:
        print(f"请求失败，状态码 {response.status_code}: {response.text}")
        print(f"错误详情: {error}")
    except requests.exceptions.RequestException as error:
        print(f"网络请求错误: {error}")

    return {}


if __name__ == "__main__":
    text = "使用硅基流动的API端口"
    result = get_embeddings_from_siliconflow(
        inputs=text,
        api_token="sk-dybroxxstjaxkyrnevsqdjikzardzzsppbvwbmimrflpoyfj",
        model="Qwen/Qwen3-Embedding-8B"
    )
    print(result)