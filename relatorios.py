"""Exportação UTF-8 da posição de estoque e das ordens."""

import csv

import persistencia
from estoque import consultar_saldos
from itens import ARQUIVO_ITENS
from ordens import carregar_ordens


def pasta_saida():
    pasta = persistencia.PASTA_DATA.parent / "saida"
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def _exportar(nome, campos, linhas):
    caminho = pasta_saida() / nome
    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(linhas)
    return caminho


def exportar_estoque():
    itens = persistencia.carregar_json(ARQUIVO_ITENS)
    saldos = consultar_saldos()
    campos = (
        "codigo", "descricao", "unidade", "saldo_atual", "estoque_seguranca",
    )
    linhas = (
        {
            "codigo": item["codigo"],
            "descricao": item["descricao"],
            "unidade": item["unidade"],
            "saldo_atual": saldos.get(item["codigo"], 0),
            "estoque_seguranca": item["estoque_seguranca"],
        }
        for item in itens
    )
    return _exportar("estoque.csv", campos, linhas)


def exportar_ordens():
    campos = (
        "id", "tipo", "codigo", "quantidade", "semana_liberacao",
        "semana_recebimento", "status", "atrasada",
    )
    linhas = [
        {**ordem, "atrasada": "Sim" if ordem["atrasada"] else "Não"}
        for ordem in carregar_ordens()
    ]
    return _exportar("ordens.csv", campos, linhas)
