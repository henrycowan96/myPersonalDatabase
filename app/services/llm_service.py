import os
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

class LLMService:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="openai/gpt-oss-20b:free",
            temperature=0.7,
            openai_api_key=os.getenv("OPEN_ROUTER_API_KEY"),
            openai_api_base="https://openrouter.ai/api/v1"
        )

    async def generate_response(self, prompt: str, model: str = "openai/gpt-oss-20b:free") -> str:
        """Generate a response from the LLM based on the given prompt"""
        try:
            system_message = "You are a helpful AI assistant analyzing personal life insights. Be thoughtful, insightful, and constructive in your responses."
            full_prompt = f"{system_message}\n\n{prompt}"
            message = HumanMessage(content=full_prompt)
            response = await self.llm.ainvoke([message])
            return response.content.strip()

        except Exception as e:
            print(f"Error generating LLM response: {e}")
            raise e
