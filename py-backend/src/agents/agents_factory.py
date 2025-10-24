"""Agents构建工厂"""
from agently import Agently

class AgentFactory:
    _instances = {}
    _config = None

    @classmethod
    def get_agent(cls, instance_name="default"):
        if instance_name not in cls._instances:
            cls._instances[instance_name] = cls._create_new_instance()
        return cls._instances[instance_name]._get_agent()
    
    @classmethod
    def create_agent_by_name(cls, name):
        instance = cls._create_new_instance()
        return instance._get_agent()
    
    @classmethod
    def _create_new_instance(cls, ):
        instance = super(AgentFactory, cls).__new__(cls)
        instance._initialize()
        return instance
    
    def _initialize(self):
        """初始化实例，使用配置文件中的设置"""
        Agently.set_settings("response.streaming_parse", True)
        Agently.set_settings(
                "OpenAICompatible",
                {
                    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                    "model": "qwen3-max",
                    "model_type": "chat",
                    "api_key": "sk-4a81eb844a224ca284962ee9e900a92a",
                },
            )
        self.agent = Agently.create_agent()
        return self.agent

    def _get_agent(self):
        return self.agent

# if __name__ == "__main__":
#     # 创建一个名为"qa_agent"的agent
#     qa_agent = AgentFactory.create_agent_by_name("qa_agent")

#     # 后续可以通过名称再次获取同一个agent
#     same_agent = AgentFactory.create_agent_by_name("qa_agent")
