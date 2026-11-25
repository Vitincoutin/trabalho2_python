"""Cadastro e consulta do Plano Mestre de Produção (MPS)."""

import os
from contextlib import contextmanager

import persistencia
from itens import ARQUIVO_ITENS, buscar_item
from utils import ler_codigo, ler_numero, ler_opcao


if os.name == "nt":
    import msvcrt
else:
    import fcntl


ARQUIVO_MPS = "mps.json"
HORIZONTE = 8
SEMANAS = range(1, HORIZONTE + 1)


def listar_produtos_acabados():
    itens = persistencia.carregar_json(ARQUIVO_ITENS)
    return [item for item in itens if item["tipo"] == "PA"]


def carregar_mps():
    """Retorna um dicionário de códigos PA e listas de oito demandas."""
    try:
        planos = persistencia.carregar_json(ARQUIVO_MPS)
    except FileNotFoundError:
        return {}

    if not isinstance(planos, dict):
        raise ValueError("Formato inválido no arquivo do MPS.")

    codigos_pa = {item["codigo"] for item in listar_produtos_acabados()}
    for codigo, demandas in planos.items():
        if codigo not in codigos_pa:
            raise ValueError(f"O MPS de {codigo} exige um PA cadastrado.")
        if (
            not isinstance(demandas, list)
            or len(demandas) > HORIZONTE
            or any(type(valor) is not int or valor < 0 for valor in demandas)
        ):
            raise ValueError(f"Demandas inválidas no MPS de {codigo}.")
        planos[codigo] = obter_demandas(planos, codigo)
    return planos


@contextmanager
def acesso_mps():
    """Mantém a leitura e a gravação de uma alteração na mesma operação."""
    pasta = persistencia.PASTA_DATA
    pasta.mkdir(parents=True, exist_ok=True)
    with (pasta / "mps_acesso.tmp").open("a+b") as trava:
        trava.seek(0)
        if os.name == "nt":
            msvcrt.locking(trava.fileno(), msvcrt.LK_LOCK, 1)
        else:
            fcntl.flock(trava.fileno(), fcntl.LOCK_EX)
        yield


def ler_produto_acabado():
    codigo = ler_codigo("Código do produto acabado: ")
    item = buscar_item(persistencia.carregar_json(ARQUIVO_ITENS), codigo)
    if item is None:
        raise ValueError(f"Item {codigo} não encontrado no cadastro.")
    if item["tipo"] != "PA":
        raise ValueError("Somente produtos acabados (PA) podem possuir MPS.")
    return item


def obter_demandas(planos, codigo):
    """Retorna as demandas nas semanas 1 a 8, com zero onde faltam dados."""
    demandas = planos.get(codigo, [])
    return demandas + [0] * (HORIZONTE - len(demandas))


def salvar_e_atualizar(planos, atualizados):
    persistencia.salvar_json(ARQUIVO_MPS, atualizados)
    planos.clear()
    planos.update(atualizados)


def cadastrar_mps(planos):
    item = ler_produto_acabado()
    codigo = item["codigo"]
    aviso = f"{codigo} já possui MPS. Use a opção de alterar uma semana."
    if codigo in planos:
        raise ValueError(aviso)

    print("Pressione Enter para deixar a demanda da semana em zero.")
    demandas = [
        ler_numero(f"Demanda da semana {semana}: ", atual=0)
        for semana in SEMANAS
    ]

    with acesso_mps():
        atualizados = carregar_mps()
        if codigo in atualizados:
            planos.update(atualizados)
            raise ValueError(aviso)
        atualizados[codigo] = demandas
        salvar_e_atualizar(planos, atualizados)
    print(f"MPS de {codigo} cadastrado com sucesso.")


def alterar_demanda(planos):
    item = ler_produto_acabado()
    codigo = item["codigo"]
    escolha = ler_opcao(
        f"Semana a alterar (1 a {HORIZONTE}): ", tuple(map(str, SEMANAS))
    )
    semana = int(escolha)
    demanda = ler_numero(f"Nova demanda da semana {semana}: ")

    with acesso_mps():
        atualizados = carregar_mps()
        demandas = obter_demandas(atualizados, codigo)
        demandas[semana - 1] = demanda
        atualizados[codigo] = demandas
        salvar_e_atualizar(planos, atualizados)
    print(f"Demanda de {codigo} na semana {semana} alterada com sucesso.")


def exibir_tabela(produtos, planos):
    semanas = [f"Sem {semana}" for semana in SEMANAS]
    linhas = [["Produto", *semanas, "Descrição"]]
    for produto in produtos:
        codigo = produto["codigo"]
        demandas = obter_demandas(planos, codigo)
        linhas.append([codigo, *map(str, demandas), produto["descricao"]])

    larguras = [max(map(len, coluna)) for coluna in zip(*linhas)]
    for linha in linhas:
        campos = [
            valor.rjust(largura)
            for valor, largura in zip(linha[:-1], larguras)
        ]
        print(" | ".join([*campos, linha[-1]]))


def consultar_mps(planos):
    produto = ler_produto_acabado()
    exibir_tabela([produto], planos)


def exibir_mps_completo(planos):
    produtos = listar_produtos_acabados()
    if not produtos:
        print("Nenhum produto acabado cadastrado.")
        return
    exibir_tabela(produtos, planos)
