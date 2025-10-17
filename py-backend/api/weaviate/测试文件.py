import weaviate
from weaviate.auth import AuthApiKey

client = weaviate.connect_to_custom(
    skip_init_checks=False,
    http_host="192.168.213.129",
    http_port=8080,
    http_secure=False,
    grpc_host="192.168.213.129",
    grpc_port=50051,
    grpc_secure=False,
    auth_credentials=AuthApiKey("key_kunkun")
)

# 检查连接是否成功
print(client.is_ready())

# 关闭连接
print(client.close())