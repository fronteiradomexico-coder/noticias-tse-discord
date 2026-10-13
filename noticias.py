import os
import json
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

WEBHOOK = os.environ.get("https://discord.com/api/webhooks/1559362537898770492/4OwrX_V3RwVvKWDEKoCTj-ELOuw9BSTgC1UfTdQ_yGwzKoxF9kUaEZnG4q8Gp6MvMWmf")
RSS_URL = "https://www.tse.jus.br/noticias-em-rss"

if not WEBHOOK:
    raise RuntimeError("Configure o secret DISCORD_WEBHOOK no GitHub.")

def enviar_discord(titulo, link, descricao, data):
    embed = {
        "title": titulo[:256],
        "url": link,
        "description": descricao[:4000] or "Nova notícia publicada pelo TSE.",
        "color": 0x164B8C,
        "footer": {"text": "Fonte: Tribunal Superior Eleitoral"},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    payload = json.dumps({
        "username": "Notícias do TSE",
        "embeds": [embed]
    }).encode("utf-8")

    req = urllib.request.Request(
        WEBHOOK,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=20) as resposta:
        if resposta.status not in (200, 204):
            raise RuntimeError(f"Discord respondeu: {resposta.status}")

def main():
    req = urllib.request.Request(
        RSS_URL,
        headers={"User-Agent": "NoticiasTSEBot/1.0"}
    )

    with urllib.request.urlopen(req, timeout=30) as resposta:
        xml = resposta.read()

    raiz = ET.fromstring(xml)
    itens = raiz.findall(".//item")

    if not itens:
        print("Nenhuma notícia encontrada no feed.")
        return

    arquivo = "noticias_enviadas.json"

    try:
        with open(arquivo, "r", encoding="utf-8") as f:
            enviados = set(json.load(f))
    except FileNotFoundError:
        enviados = set()

    novos = []

    for item in itens:
        titulo = item.findtext("title", default="Notícia do TSE").strip()
        link = item.findtext("link", default="").strip()
        descricao = item.findtext("description", default="").strip()
        data = item.findtext("pubDate", default="").strip()

        if not link or link in enviados:
            continue

        enviar_discord(titulo, link, descricao, data)
        enviados.add(link)
        novos.append(link)
        print("Notícia enviada:", titulo)

    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(sorted(enviados), f, ensure_ascii=False, indent=2)

    if not novos:
        print("Nenhuma notícia nova.")

if __name__ == "__main__":
    main()
