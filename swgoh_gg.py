import os
import time

import aiohttp
import discord

BASE_URL = "https://swgoh.gg/api"
CACHE_SECONDS = 300
_cache = {}

HEADERS_BASE = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json",
}


def _headers():
    key = os.getenv("SWGOH_API_KEY", "")
    return {**HEADERS_BASE, "X-GG-BOT-ACCESS": key}


async def api_get(path):
    now = time.time()
    hit = _cache.get(path)
    if hit and now - hit[0] < CACHE_SECONDS:
        return hit[1]
    url = f"{BASE_URL}{path}"
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, headers=_headers()) as resp:
            if resp.status == 404:
                raise ValueError("Не найдено. Проверь код.")
            if resp.status != 200:
                raise RuntimeError(f"Сайт ответил статусом {resp.status}")
            data = await resp.json()
    _cache[path] = (now, data)
    return data


def clean_ally_code(text):
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) != 9:
        raise ValueError("Код союзника должен состоять из 9 цифр.")
    return digits


def fmt(n):
    try:
        return f"{int(n):,}".replace(",", " ")
    except (TypeError, ValueError):
        return str(n)


async def player_embed(ally_code):
    code = clean_ally_code(ally_code)
    data = await api_get(f"/player/{code}/")
    p = data["data"]
    embed = discord.Embed(
        title=p.get("name", "Игрок"),
        url="https://swgoh.gg" + p.get("url", ""),
        description=f"Гильдия: {p.get('guild_name') or 'нет'}",
        color=0x2B6CB0,
    )
    embed.add_field(name="Уровень", value=fmt(p.get("level")))
    embed.add_field(name="Общая мощность", value=fmt(p.get("galactic_power")))
    embed.add_field(name="Персонажи", value=fmt(p.get("character_galactic_power")))
    embed.add_field(name="Флот", value=fmt(p.get("ship_galactic_power")))
    embed.add_field(name="Ранг арены", value=fmt(p.get("arena_rank")))
    fleet = p.get("fleet_arena") or {}
    embed.add_field(name="Ранг флота", value=fmt(fleet.get("rank")))
    embed.add_field(name="Рейды гильдии", value=fmt(p.get("guild_raid_won")))
    embed.add_field(name="Вклад в гильдию", value=fmt(p.get("guild_contribution")))
    img = p.get("portrait_image")
    if img:
        embed.set_thumbnail(url=img)
    embed.set_footer(text="Обновлено: " + str(p.get("last_updated", ""))[:16])
    return embed