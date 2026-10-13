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
    + quote("site:tse.jus.br notícias")
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
            else "Confira a publicação original."
        ),
        "color": 0x164B8C,
        "footer": {"text": "Notícias eleitorais"},
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
        print(f"Discord respondeu: HTTP {resposta.status}")


def carregar_historico():
    try:
        with open(HISTORICO, "r", encoding="utf-8") as arquivo:
            return set(json.load(arquivo))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def salvar_historico(enviados):
    temporario = HISTORICO + ".tmp"

    with open(temporario, "w", encoding="utf-8") as arquivo:
        json.dump(
            sorted(enviados),
            arquivo,
            ensure_ascii=False,
            indent=2
        )

    os.replace(temporario, HISTORICO)


def main():
    if not WEBHOOK:
        raise RuntimeError("Configure o segredo DISCORD_WEBHOOK.")

    enviados = carregar_historico()
    noticias = buscar_noticias()

    novas = [
        noticia
        for noticia in reversed(noticias)
        if noticia["link"] not in enviados
    ]

    for noticia in novas:
        enviar_discord(noticia)
        enviados.add(noticia["link"])
        salvar_historico(enviados)
        print("Notícia enviada:", noticia["titulo"])

    print(f"Concluído. Novas notícias enviadas: {len(novas)}")


if __name__ == "__main__":
    main()
