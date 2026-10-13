import os
import json
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import quote

WEBHOOK = os.environ.get("DISCORD_WEBHOOK")

# Feed principal e alternativa
RSS_URLS = [
    "https://www.tse.jus.br/noticias-em-rss",
    "https://news.google.com/rss/search?q=" + quote("site:tse.jus.br notícias") + "&hl=pt-BR&gl=BR&ceid=BR:pt-419",
]

HISTORICO = "noticias_enviadas.json"


def buscar_rss(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
            ),
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        },
    )

    with urllib.request.urlopen(req, timeout=30) as resposta:
        conteudo = resposta.read()

    raiz = ET.fromstring(conteudo)
    return raiz.findall(".//item")


def enviar_discord(titulo, link, descricao):
    embed = {
        "title": titulo[:256],
        "url": link,
        "description": descricao[:4000] or "Nova notícia publicada.",
        "color": 0x164B8C,
        "footer": {"text": "Monitor de notícias eleitorais"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    payload = json.dumps({
        "username": "Notícias do TSE",
        "embeds": [embed],
    }).encode("utf-8")

    req = urllib.request.Request(
        WEBHOOK,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=20) as resposta:
        if resposta.status not in (200, 204):
            raise RuntimeError(f"Discord respondeu: {resposta.status}")


def main():
    if not WEBHOOK:
        raise RuntimeError(
            "Configure o segredo DISCORD_WEBHOOK em Settings > Secrets and variables > Actions."
        )

    enviados = set()

    try:
        with open(HISTORICO, "r", encoding="utf-8") as arquivo:
            enviados = set(json.load(arquivo))
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    itens = None

    for url in RSS_URLS:
        try:
            itens = buscar_rss(url)
            print(f"Feed acessado: {url}")
            break
        except (urllib.error.URLError, ET.ParseError, TimeoutError) as erro:
            print(f"Falha no feed {url}: {erro}")

    if itens is None:
        raise RuntimeError("Não foi possível acessar nenhum feed de notícias.")

    novos = 0

    for item in reversed(itens):
        titulo = item.findtext("title", default="Notícia").strip()
        link = item.findtext("link", default="").strip()
        descricao = item.findtext("description", default="").strip()

        if not link or link in enviados:
            continue

        enviar_discord(titulo, link, descricao)
        enviados.add(link)
        novos += 1
        print(f"Notícia enviada: {titulo}")

    with open(HISTORICO, "w", encoding="utf-8") as arquivo:
        json.dump(sorted(enviados), arquivo, ensure_ascii=False, indent=2)

    print(f"Concluído. Novas notícias enviadas: {novos}")


if __name__ == "__main__":
    main()
