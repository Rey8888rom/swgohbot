import asyncio
import logging
import os

import aiohttp
import discord
from aiohttp import web
from discord import app_commands
from dotenv import load_dotenv

# Ключи из файла .env грузим ПЕРВЫМ делом (файл лежит рядом с этим файлом)
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from ai_router import ask_ai  # noqa: E402
from mod_card import build_mod_set_image  # noqa: E402

# Показываем в окне командной строки, что происходит
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("swgohbot")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
PORT = int(os.getenv("PORT", "8080"))

TOP_MOD_PRESETS = {
    "рей": {
        "name": "Рей (Rey)",
        "sets": [("Speed", 4), ("Health", 2)],
        "primaries": [
            "Arrow: Speed",
            "Triangle: Crit Damage / Offense",
            "Circle: Health",
            "Cross: Offense / Health",
        ],
        "note": "Максимум скорости и здоровья для ульты и выживаемости.",
    },
    "слкр": {
        "name": "Кайло Рен (SLKR)",
        "sets": [("Speed", 4), ("Critical Chance", 2)],
        "primaries": [
            "Arrow: Speed",
            "Triangle: Crit Damage",
            "Circle: Health",
            "Cross: Offense",
        ],
        "note": "Высокая скорость, крит-урон и атака.",
    },
}


async def fetch_news_summary() -> str:
    if not NEWS_API_KEY:
        return ""
    url = f"https://newsapi.org/v2/top-headlines?language=ru&pageSize=5&apiKey={NEWS_API_KEY}"
    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return ""
                data = await resp.json()
                articles = data.get("articles", [])[:5]
                lines = [
                    f"- {a.get('title')} ({a.get('source', {}).get('name', '')})"
                    for a in articles
                    if a.get("title")
                ]
                return "\n".join(lines)
    except Exception:
        return ""


class SwgohBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        synced = await self.tree.sync()
        print(f"Команды зарегистрированы в Дискорде: {len(synced)}", flush=True)


bot = SwgohBot()


@bot.event
async def on_ready():
    print("=" * 50, flush=True)
    print("Бот запущен как", bot.user, flush=True)
    print("Серверов, где он есть:", len(bot.guilds), flush=True)
    print("=" * 50, flush=True)


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    # Любая необработанная ошибка команды: пишем в окно и отвечаем в Дискорде
    log.error("Ошибка команды: %r", error)
    text = f"Ошибка команды: {str(error)[:300]}"
    try:
        if interaction.response.is_done():
            await interaction.followup.send(text)
        else:
            await interaction.response.send_message(text)
    except Exception:
        log.exception("Не удалось отправить сообщение об ошибке")


@bot.tree.command(name="ping", description="Проверка: бот жив? (без ИИ)")
async def slash_ping(interaction: discord.Interaction):
    await interaction.response.send_message("Понг! Бот работает.")


@bot.tree.command(name="mods", description="Прислать набор топ-модов и картинку сетов для персонажа")
@app_commands.describe(character="Имя персонажа, например: Рей")
async def slash_mods(interaction: discord.Interaction, character: str):
    await interaction.response.defer()
    try:
        key = character.strip().lower()
        preset = TOP_MOD_PRESETS.get(key)

        if preset:
            img_buf = build_mod_set_image(preset["name"], preset["sets"], preset["primaries"])
            file = discord.File(fp=img_buf, filename="mod_set.png")
            ai_text = await ask_ai(
                f"Дай краткий совет по расстановке модов для {preset['name']}: {preset['note']}",
                "Ты эксперт по Star Wars Galaxy of Heroes. Отвечай коротко и по делу на русском.",
            )
            await interaction.followup.send(content=f"**{preset['name']}**\n{ai_text}"[:1950], file=file)
        else:
            answer = await ask_ai(
                f"Назови рекомендуемые сеты модов и статы для персонажа '{character}' в Star Wars Galaxy of Heroes.",
                "Ты эксперт по Star Wars Galaxy of Heroes. Отвечай кратко и структурированно на русском.",
            )
            await interaction.followup.send((answer or "Пустой ответ от ИИ.")[:1950])
    except Exception as e:
        log.exception("Ошибка в /mods")
        await interaction.followup.send(f"Ошибка в /mods: {str(e)[:300]}")


@bot.tree.command(name="ask", description="Задать вопрос ИИ по игре или на любую тему")
@app_commands.describe(question="Ваш вопрос")
async def slash_ask(interaction: discord.Interaction, question: str):
    await interaction.response.defer()
    try:
        news_context = ""
        if any(w in question.lower() for w in ["новост", "главные новости", "что нового в мире"]):
            news_context = await fetch_news_summary()

        prompt = question if not news_context else f"Свежие новости:\n{news_context}\n\nЗадача пользователя: {question}"
        answer = await ask_ai(prompt, "Ты умный помощник. Отвечай чётко на русском языке.")
        await interaction.followup.send((answer or "Пустой ответ от ИИ.")[:1950])
    except Exception as e:
        log.exception("Ошибка в /ask")
        await interaction.followup.send(f"Ошибка в /ask: {str(e)[:300]}")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    mentioned = bot.user in message.mentions
    content = message.content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
    if not mentioned and not content.lower().startswith(("бот,", "бот ")):
        return

    clean_text = content[4:].strip() if content.lower().startswith(("бот,", "бот ")) else content
    if not clean_text:
        return

    try:
        async with message.channel.typing():
            if "рей" in clean_text.lower() and ("мод" in clean_text.lower() or "сет" in clean_text.lower()):
                preset = TOP_MOD_PRESETS["рей"]
                img_buf = build_mod_set_image(preset["name"], preset["sets"], preset["primaries"])
                file = discord.File(fp=img_buf, filename="rey_mods.png")
                await message.reply(content=f"Вот набор сетов модов на **{preset['name']}**:\n{preset['note']}", file=file)
                return

            news_context = ""
            if any(w in clean_text.lower() for w in ["новост", "главные новости", "новости дня"]):
                news_context = await fetch_news_summary()

            prompt = clean_text if not news_context else f"Свежие новости:\n{news_context}\n\nЗапрос: {clean_text}"
            reply = await ask_ai(prompt, "Ты универсальный ИИ-помощник на русском языке.")
            await message.reply((reply or "Пустой ответ от ИИ.")[:1950])
    except Exception as e:
        log.exception("Ошибка в on_message")
        await message.reply(f"Ошибка: {str(e)[:300]}")


async def start_health_server():
    # Мини-сервер нужен только для хостинга. Дома он не обязателен:
    # если порт занят, просто пропускаем.
    try:
        app = web.Application()
        app.router.add_get("/", lambda req: web.Response(text="Bot is alive"))
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", PORT)
        await site.start()
    except OSError as e:
        print(f"Мини-сервер на порту {PORT} не запущен (это не страшно): {e}", flush=True)


async def main():
    if not DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN не найден. Проверь файл .env рядом с botswg.py")
    await start_health_server()
    async with bot:
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен.")