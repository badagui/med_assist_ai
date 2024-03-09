import queue
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

class GPTClient:
    def __init__(self, api_key):
        self.client = AsyncOpenAI(api_key=api_key)
    
    async def send_query(self, messages, cback):
        model = "gpt-4-turbo-preview"
        pricing = {
            "gpt-3.5-turbo-0125": [0.0005, 0.0015],
            "gpt-4-turbo-preview": [0.01, 0.03]
        }
        price = [pricing[model][0] if model in pricing else 0, pricing[model][1] if model in pricing else 0]
        try:
            completion = await self.client.chat.completions.create(
                model=model,
                messages=messages,
            )
            print('LLM: completion id ', completion.id)
            print('LLM: usage ', completion.usage)
            print('LLM: in cents ', completion.usage.prompt_tokens * price[0] / 1000 * 100)
            print('LLM: out cents ', completion.usage.completion_tokens * price[1] / 1000 * 100)
            cback(completion.choices[0].message.content)
            # return completion.choices[0].message
        except Exception as e:
            print('Exception send query', e)
