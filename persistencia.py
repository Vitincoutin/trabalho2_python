import json
from pathlib import Path


PASTA_DATA = Path(__file__).resolve().parent / "data"


def carregar_json(nome):
    caminho = PASTA_DATA / nome
    with caminho.open(encoding="utf-8") as arquivo:
        return json.load(arquivo)


def salvar_json(nome, dados):
    PASTA_DATA.mkdir(parents=True, exist_ok=True)
    caminho = PASTA_DATA / nome
    temporario = caminho.with_suffix(".tmp")
    with temporario.open("w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=4)
        arquivo.write("\n")
    temporario.replace(caminho)


def inicializar_dados():
    caminho = PASTA_DATA / "itens.json"
    if caminho.exists():
        return

    dados = carregar_json("itens_demonstracao.json")
    try:
        with caminho.open("x", encoding="utf-8") as arquivo:
            json.dump(dados, arquivo, ensure_ascii=False, indent=4)
            arquivo.write("\n")
    except FileExistsError:
        pass
