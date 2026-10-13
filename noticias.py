import os
import json
import html
import re
import time
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

from datetime import datetime, timezone
from urllib.parse import quote

WEBHOOK = os.environ.get("DISCORD_WEBHOOK")
HISTORICO = "noticias_enviadas.json"

# Pesquisas de notícias em RSS
FONTES = [
    (
        "Google Notícias - TSE",
        "https://news.google.com/rss/search?q="
        + quote("site:tse.jus.br/noticias")
        + "&hl=pt-BR&gl=BR&ceid=BR:pt-419",
    ),
    (
        "Google Notícias - eleições",
        "https://news.google.com/rss/search?q="
        + quote("TSE eleições")
        + "&hl=pt-BR&gl=BR&ceid=BR:pt-419",
    ),
]


def limpar_texto(texto):
    texto = re.sub(r"<[^>]*>", " ", texto or "")
    texto = html.unescape(texto)
    return re.sub(r"\s+", " ", texto).strip()


def requisitar(url, tentativas=3):
    for tentativa in range(1, tentativas + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (X11; Linux x86_64) "
                        "AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
                    ),
                    "Accept": (
                        "application/rss+xml, application/xml, "
                        "text/xml, */*"
                    ),
                },
            )

            with urllib.request.urlopen(req, timeout=25) as resposta:
                return resposta.read()

        except (
            urllib.error.URLError,
            TimeoutError,
            OSError,
        ) as erro:
            print(
                f"Tentativa {tentativa}/{tentativas} falhou: {erro}"
            )

            if tentativa < tentativas:
                time.sleep(tentativa * 3)

    return None


def buscar_noticias():
    encontradas = {}

    for nome, url in FONTES:
        conteudo = requisitar(url)

        if conteudo is None:
            print(f"Fonte indisponível: {nome}")
            continue

        try:
            raiz = ET.fromstring(conteudo)
        except ET.ParseError as erro:
            print(f"RSS inválido em {nome}: {erro}")
            continue

        itens = raiz.findall(".//item")

        for item in itens:
            titulo = limpar_texto(
                item.findtext("title", "Notícia eleitoral")
            )
            link = item.findtext("link", "").strip()
            descricao = limpar_texto(
                item.findtext("description", "")
            )
            data = limpar_texto(
                item.findtext("pubDate", "")
            )

            if not titulo or not link:
                continue

            # A pesquisa geral pode conter assuntos não relacionados.
            # Mantemos apenas resultados que mencionam TSE ou Tribunal
            # Superior Eleitoral no título.
            titulo_min = titulo.lower()

            if (
                "tse" not in titulo_min
                and "tribunal superior eleitoral" not in titulo_min
            ):
                continue

            encontradas[link] = {
                "titulo": titulo,
                "link": link,
                "descricao": descricao,
                "data": data,
            }

        print(f"Fonte consultada: {nome}; itens: {len(itens)}")

    return list(encontradas.values())


def carregar_historico():
    try:
        with open(HISTORICO, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)

        if isinstance(dados, list):
            return set(dados)

        return set()

    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def salvar_historico(enviados):
    temporario = HISTORICO + ".tmp"

    with open(temporario, "w", encoding="utf-8") as arquivo:
        json.dump(
            sorted(enviados),
            arquivo,
            ensure_ascii=False,
            indent=2,
        )

    os.replace(temporario, HISTORICO)


def enviar_discord(noticia):
    if not WEBHOOK:
        raise RuntimeError(
            "Segredo DISCORD_WEBHOOK não configurado no GitHub."
        )

    embed = {
        "title": noticia["titulo"][:256],
        "url": noticia["link"],
        "description": (
            noticia["descricao"][:4000]
            or "Abra a publicação original para ler a notícia."
        ),
        "color": 0x164B8C,
        "footer": {
            "text": "Monitor automático de notícias eleitorais"
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    payload = json.dumps(
        {
            "username": "Notícias do TSE",
            "embeds": [embed],
            "allowed_mentions": {"parse": []},
        },
        ensure_ascii=False,
    ).encode("utf-8")

    req = urllib.request.Request(
        WEBHOOK,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resposta:
            print(f"Discord: HTTP {resposta.status}")

    except urllib.error.HTTPError as erro:
        detalhes = erro.read().decode(
            "utf-8", errors="replace"
        )

        raise RuntimeError(
            f"Discord recusou o envio: HTTP {erro.code}; "
            f"detalhes: {detalhes[:500]}"
        ) from erro


def main():
    noticias = buscar_noticias()

    if not noticias:
        raise RuntimeError(
            "Nenhuma notícia foi encontrada. "
            "As fontes podem estar temporariamente indisponíveis."
        )

    enviados = carregar_historico()
    novas = [
        noticia
        for noticia in noticias
        if noticia["link"] not in enviados
    ]

    print(f"Notícias encontradas: {len(noticias)}")
    print(f"Notícias novas: {len(novas)}")

    for noticia in reversed(novas):
        enviar_discord(noticia)

        # Salva depois de cada envio confirmado.
        enviados.add(noticia["link"])
        salvar_historico(enviados)

        print(f"Enviada: {noticia['titulo']}")

        # Evita enviar mensagens em sequência muito rápida.
        time.sleep(1)

    print("Monitor finalizado.")


if __name__ == "__main__":
    main()
