import os
import json
import html
import re
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import quote

WEBHOOK = os.environ.get("DISCORD_WEBHOOK")

RSS_URL = (
    "https://news.google.com/rss/search?q="
    + quote("site:tse.jus.br/noticias")
    + "&hl=pt-BR&gl=BR&ceid=BR:pt-419"
)

HISTORICO = "noticias_enviadas.json"


def limpar_html(texto):
    texto = re.sub(r"<[^>]+>", " ", texto or "")
    texto = html.unescape(texto)
    return re.sub(r"\s+", " ", texto).strip()


def buscar_noticias():
    req = urllib.request.Request(
        RSS_URL,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(req, timeout=30) as resposta:
        raiz = ET.fromstring(resposta.read())

    noticias = []

    for item in raiz.findall(".//item"):
        titulo = limpar_html(item.findtext("title", "Notícia do TSE"))
        link = item.findtext("link", "").strip()
        descricao = limpar_html(item.findtext("description", ""))

        if titulo and link:
            noticias.append({
                "titulo": titulo,
                "link": link,
                "descricao": descricao
            })

    return noticias


def enviar_discord(noticia):
    embed = {
        "title": noticia["titulo"][:256],
        "url": noticia["link"],
        "description": (
            noticia["descricao"][:4000]
            if noticia["descricao"]
            else "Confira os detalhes na publicação original."
        ),
        "color": 0x164B8C,
        "footer": {"text": "Notícias eleitorais • Fonte: Google Notícias"},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    payload = json.dumps({
        "username": "Notícias do TSE",
        "embeds": [embed],
        "allowed_mentions": {"parse": []}
    }).encode("utf-8")

    req = urllib.request.Request(
        WEBHOOK,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=20) as resposta:
        if resposta.status not in (200, 204):
            raise RuntimeError(
                f"Discord respondeu com HTTP {resposta.status}"
            )


def carregar_historico():
    try:
        with open(HISTORICO, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
            return set(dados)
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def salvar_historico
