"""Cadastro de centros, roteiros e planejamento de capacidade (CRP)."""

import re
from decimal import Decimal, InvalidOperation

import persistencia
from itens import ARQUIVO_ITENS, buscar_item
from mps import SEMANAS
from mrp import quantidade_positiva
from ordens import carregar_ordens
from utils import ler_codigo, ler_texto


ARQUIVO_CENTROS = "centros.json"
ARQUIVO_ROTEIROS = "roteiros.json"


def _carregar_cadastro(nome):
    try:
        dados = persistencia.carregar_json(nome)
    except FileNotFoundError:
        return {}
    if not isinstance(dados, dict):
        raise ValueError(f"Formato inválido no arquivo {nome}.")
    return dados


def carregar_centros():
    return _carregar_cadastro(ARQUIVO_CENTROS)


def carregar_roteiros():
    return _carregar_cadastro(ARQUIVO_ROTEIROS)


def salvar_centro(codigo, descricao, capacidade, custo_hora, *, alterar=False):
    codigo = codigo.strip().upper()
    descricao = descricao.strip()
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]*", codigo) or not descricao:
        raise ValueError("Informe um código como CT-01 e a descrição.")

    capacidade = quantidade_positiva(capacidade, "capacidade semanal")
    try:
        custo_hora = Decimal(str(custo_hora))
    except InvalidOperation as erro:
        raise ValueError("Informe um custo-hora válido.") from erro
    if not custo_hora.is_finite() or custo_hora < 0:
        raise ValueError("O custo-hora deve ser finito e não negativo.")

    centros = carregar_centros()
    if codigo in centros and not alterar:
        raise ValueError(f"O centro {codigo} já está cadastrado.")
    if codigo not in centros and alterar:
        raise ValueError(f"Centro {codigo} não encontrado.")
    centros[codigo] = {
        "descricao": descricao,
        "capacidade_semanal": str(capacidade),
        "custo_hora": str(custo_hora),
    }
    persistencia.salvar_json(ARQUIVO_CENTROS, centros)


def salvar_roteiro(codigo, centro, tempo):
    item = buscar_item(persistencia.carregar_json(ARQUIVO_ITENS), codigo)
    if item is None or item["tipo"] not in ("PA", "SA"):
        raise ValueError("O roteiro exige um item PA ou SA cadastrado.")
    if centro not in carregar_centros():
        raise ValueError(f"Centro {centro} não encontrado.")
    tempo = quantidade_positiva(tempo, "tempo por unidade")

    roteiros = carregar_roteiros()
    roteiros[codigo] = {"centro": centro, "tempo_unitario": str(tempo)}
    persistencia.salvar_json(ARQUIVO_ROTEIROS, roteiros)


def obter_roteiro(codigo, roteiros, centros):
    if codigo not in roteiros:
        raise ValueError(f"Cadastre o roteiro do item {codigo}.")
    roteiro = roteiros[codigo]
    centro = roteiro["centro"]
    if centro not in centros:
        raise ValueError(
            f"Centro {centro} do roteiro de {codigo} não encontrado."
        )
    tempo = quantidade_positiva(roteiro["tempo_unitario"], codigo)
    return centro, tempo


def calcular_crp():
    centros = carregar_centros()
    roteiros = carregar_roteiros()
    cargas = {centro: dict.fromkeys(SEMANAS, Decimal(0)) for centro in centros}
    for ordem in carregar_ordens():
        if ordem["tipo"] != "OP" or ordem["status"] != "LIBERADA":
            continue
        semana = ordem["semana_liberacao"]
        if semana not in SEMANAS:
            continue
        centro, tempo = obter_roteiro(ordem["codigo"], roteiros, centros)
        quantidade = quantidade_positiva(ordem["quantidade"], ordem["id"])
        cargas[centro][semana] += quantidade * tempo

    resultados = {}
    for codigo, centro in centros.items():
        capacidade = quantidade_positiva(centro["capacidade_semanal"], codigo)
        resultados[codigo] = []
        for semana, carga in cargas[codigo].items():
            resultados[codigo].append({
                "semana": semana,
                "carga": carga,
                "capacidade": capacidade,
                "utilizacao": 100 * carga / capacidade,
                "sobrecarga": carga > capacidade,
            })
    return resultados


def informar_centro(alterar=False):
    codigo = ler_texto("Código do centro: ").upper()
    centros = carregar_centros()
    if alterar and codigo not in centros:
        raise ValueError(f"Centro {codigo} não encontrado.")
    dados = centros[codigo] if alterar else {}
    if alterar:
        print("Pressione Enter para manter os valores atuais.")
    descricao = ler_texto("Descrição: ", dados.get("descricao"))
    capacidade = ler_texto(
        "Capacidade (h/semana): ", dados.get("capacidade_semanal")
    ).replace(",", ".")
    custo = ler_texto("Custo (R$/h): ", dados.get("custo_hora"))
    custo = custo.replace(",", ".")
    salvar_centro(codigo, descricao, capacidade, custo, alterar=alterar)
    print(f"Centro {codigo} salvo.")


def exibir_centros():
    print("Centro | Descrição | Capacidade (h/semana) | Custo (R$/h)")
    for codigo, centro in carregar_centros().items():
        print(
            f'{codigo} | {centro["descricao"]} | '
            f'{centro["capacidade_semanal"]} | {centro["custo_hora"]}'
        )


def informar_roteiro():
    codigo = ler_codigo("Código do item fabricado: ")
    centro = ler_texto("Código do centro: ").upper()
    tempo = ler_texto("Tempo (h/unidade): ").replace(",", ".")
    salvar_roteiro(codigo, centro, tempo)
    print(f"Roteiro de {codigo} salvo.")


def exibir_roteiros():
    print("Item | Centro | Tempo (h/unidade)")
    for codigo, roteiro in carregar_roteiros().items():
        print(f'{codigo} | {roteiro["centro"]} | {roteiro["tempo_unitario"]}')


def exibir_crp():
    resultados = calcular_crp()
    if not resultados:
        print("Nenhum centro cadastrado.")
    for codigo, semanas in resultados.items():
        print(f"\n{codigo} | Carga e capacidade em horas")
        print("Semana | Carga (h) | Capacidade (h) | Utilização | Sobrecarga")
        for semana in semanas:
            alerta = "Sim" if semana["sobrecarga"] else "Não"
            print(
                f'{semana["semana"]:>6} | {semana["carga"]:>9.2f} | '
                f'{semana["capacidade"]:>14.2f} | '
                f'{semana["utilizacao"]:>9.1f}% | {alerta}'
            )
