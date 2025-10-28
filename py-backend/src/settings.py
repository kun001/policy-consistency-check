import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# 明确从后端目录加载
BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env", override=False)
load_dotenv(find_dotenv(), override=False)


def _env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return str(val).strip().lower() in {"1", "true", "yes", "on"}

# FastAPI server
APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT: int = int(os.getenv("APP_PORT", "10010"))

# Collections / datasets
DEFAULT_COLLECTION_NAME: str = os.getenv("DEFAULT_COLLECTION_NAME", "policy_documents")

# SiliconFlow
SILICONFLOW_API_TOKEN: str | None = os.getenv("SILICONFLOW_API_TOKEN")

# Weaviate defaults
WEAVIATE_HTTP_HOST: str = os.getenv("WEAVIATE_HTTP_HOST", "115.190.118.177")
WEAVIATE_HTTP_PORT: int = int(os.getenv("WEAVIATE_HTTP_PORT", "8080"))
WEAVIATE_HTTP_SECURE: bool = _env_bool("WEAVIATE_HTTP_SECURE", False)

WEAVIATE_GRPC_HOST: str = os.getenv("WEAVIATE_GRPC_HOST", WEAVIATE_HTTP_HOST)
WEAVIATE_GRPC_PORT: int = int(os.getenv("WEAVIATE_GRPC_PORT", "50051"))
WEAVIATE_GRPC_SECURE: bool = _env_bool("WEAVIATE_GRPC_SECURE", False)

WEAVIATE_API_KEY: str = os.getenv("WEAVIATE_API_KEY", "key_kunkun")

# Zhipu BigModel
ZHIPU_API_TOKEN: str | None = os.getenv("ZHIPU_API_TOKEN")
ZHIPU_UPLOAD_URL: str = os.getenv(
    "ZHIPU_UPLOAD_URL",
    "https://open.bigmodel.cn/api/paas/v4/files/parser/create?file",
)
ZHIPU_RESULT_BASE: str = os.getenv(
    "ZHIPU_RESULT_BASE",
    "https://open.bigmodel.cn/api/paas/v4/files/parser/result",
)

# Storage root (optional). Defaults to <project>/storage
DEFAULT_STORAGE_ROOT: Path = (Path(__file__).resolve().parents[1] / "storage").resolve()
STORAGE_ROOT: Path = Path(os.getenv("STORAGE_ROOT", str(DEFAULT_STORAGE_ROOT))).resolve()