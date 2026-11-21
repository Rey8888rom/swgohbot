import asyncio
import os

import aiohttp
from dotenv import load_dotenv
from google import genai

# ВАЖНО: ключи нужно загрузить из файла .env ДО строк с os.getenv ниже.
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


async def _call_groq(prompt: str, system_prompt: str) -> str:
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is missing")
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "temperature": 0.4,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
    }
    timeout = aiohttp.ClientTimeout(total=25)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, headers=headers, json=payload) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"Groq HTTP {resp.status}: {text}")
            data = await resp.json()
            return data["choices"][0]["message"]["content"].strip()


def _call_gemini_sync(prompt: str, system_prompt: str) -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is missing")
    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=f"{system_prompt}\n\nЗапрос:\n{prompt}",
    )
    return (response.text or "").strip()


async def ask_ai(prompt: str, system_prompt: str = "Ты полезный ассистент на русском языке.") -> str:
    try:
        return await _call_groq(prompt, system_prompt)
    except Exception as e_groq:
        print("[ИИ] Groq не ответил:", repr(e_groq), flush=True)

    try:
        loop = asyncio.get_running_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(None, _call_gemini_sync, prompt, system_prompt),
            timeout=40,
        )
    except Exception as e_gemini:
        print("[ИИ] Gemini не ответил:", repr(e_gemini), flush=True)
        return "Не получилось получить ответ от ИИ. Причина написана в окне, где запущен бот."