import asyncio
import os

import aiohttp
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))


async def main():
    key = os.getenv("GROQ_API_KEY", "")
    if not key:
        print("GROQ_API_KEY не найден в .env")
        return
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {key}"},
        ) as resp:
            data = await resp.json()
            if resp.status != 200:
                print("Ошибка Groq:", resp.status, data)
                return
            ids = sorted(m["id"] for m in data.get("data", []))
            print("Модели, доступные твоему ключу Groq:")
            for model_id in ids:
                print("  ", model_id)


asyncio.run(main())