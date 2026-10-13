import os
import json
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import quote

WEBHOOK = os.environ.get("DISCORD_WEBHOOK")

RSS_URLS = [
    "https://www.tse.jus.br/noticias-em-rss",
    "https://news.google.com/rss/search?q="
    + quote("site:tse.jus.br notícias")
    + "&hl=pt-BR&gl=BR&ceid=BR:pt-419",
]

HISTORICO = "noticias_enviadas.json"


def buscar_rss(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; NoticiasTSEBot/1.0)",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        },
    )

    with urllib.request.urlopen(req, timeout=30) as resposta:
        xml = resposta.read()

    raiz = ET.fromstring(xml)
    return raiz.findall(".//item")


def enviar_discord(titulo, link, descricao):
    if not WEBHOOK:
        raise RuntimeError(
            "Configure DISCORD_WEBHOOK em Settings > Secrets and variables > Actions."
        )

    if "discord.com/api/webhooks/" not in WEBHOOK:
        raise RuntimeError(
            "O segredo DISCORD_WEBHOOK não parece conter um webhook válido."
        )

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
        headers={
            "Content-Type": "application/json",
            "User-Agent": "NoticiasTSEBot/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resposta:
            print(f"Discord respondeu: HTTP {resposta.status}")
    except urllib.error.HTTPError as erro:
        detalhes = erro.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Erro do Discord: HTTP {erro.code}. "
            f"Resposta: {detalhes[:1000]}"
        ) from erro


def carregar_historico():
    try:
        with open(HISTORICO, "r", encoding="utf-8") as arquivo:
            return set(json.load(arquivo))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def salvar_historico(enviados):
    with open(HISTORICO, "w", encoding="utf-8") as arquivo:
        json.dump(
            sorted(enviados),
            arquivo,
            ensure_ascii=False,
            indent=2,
        )


def main():
    enviados = carregar_historico()
    itens = None

    for url in RSS_URLS:
        try:
            itens = buscar_rss(url)
            print(f"Feed acessado com sucesso: {url}")
            break
        except (
            urllib.error.URLError,
            ET.ParseError,
            TimeoutError,
        ) as erro:
            print(f"Falha ao acessar feed: {erro}")

    if itens is None:
        raise RuntimeError("Não foi possível acessar nenhum feed.")

    novos = 0

    for item in reversed(itens):
        titulo = item.findtext("title", default="Notícia eleitoral").strip()
        link = item.findtext("link", default="").strip()
        descricao = item.findtext("description", default="").strip()

        if not link or link in enviados:
            continue

        enviar_discord(titulo, link, descricao)

        enviados.add(link)
        salvar_historico(enviados)
        novos += 1

        print(f"Notícia enviada: {titulo}")

    print(f"Execução concluída. Notícias novas enviadas: {novos}")


if __name__ == "__main__":
    main()
