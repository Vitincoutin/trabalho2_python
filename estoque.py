"""Consultas, movimentações e histórico de estoque."""

import csv
import os
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal, DecimalException, Inexact, localcontext

import persistencia
from itens import ARQUIVO_ITENS, buscar_item
from utils import ler_codigo, ler_texto


if os.name == "nt":
    import msvcrt
else:
    import fcntl


ARQUIVO_ESTOQUE = "estoque.json"
ARQUIVO_KARDEX = "movimentos.csv"
ARQUIVO_OPERACAO = "operacao_ordem.json"
CAMPOS_KARDEX = (
    "data", "codigo", "tipo", "quantidade", "documento_motivo",
    "saldo_resultante",
)


@contextmanager
def acesso_estoque():
    """Permite uma operação de estoque por vez, mesmo em outros terminais."""
    pasta = persistencia.PASTA_DATA
    pasta.mkdir(parents=True, exist_ok=True)
    with (pasta / "estoque_acesso.tmp").open("a+b") as trava:
        trava.seek(0)
        if os.name == "nt":
            msvcrt.locking(trava.fileno(), msvcrt.LK_LOCK, 1)
        else:
            fcntl.flock(trava.fileno(), fcntl.LOCK_EX)
        sincronizar_operacao_ordem()
        yield


def ler_kardex():
    caminho = persistencia.PASTA_DATA / ARQUIVO_KARDEX
    try:
        with caminho.open(encoding="utf-8", newline="") as arquivo:
            leitor = csv.DictReader(arquivo, strict=True)
            if tuple(leitor.fieldnames or ()) != CAMPOS_KARDEX:
                raise ValueError("Cabeçalho inválido no kardex.")
            movimentos = list(leitor)
    except FileNotFoundError:
        return []
    except csv.Error as erro:
        raise ValueError("Formato inválido no kardex.") from erro

    for movimento in movimentos:
        if None in movimento or None in movimento.values():
            raise ValueError("Movimentação incompleta no kardex.")
    return movimentos


def gravar_kardex(movimentos):
    caminho = persistencia.PASTA_DATA / ARQUIVO_KARDEX
    temporario = caminho.with_suffix(".tmp")
    with temporario.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS_KARDEX)
        escritor.writeheader()
        escritor.writerows(movimentos)
    temporario.replace(caminho)


def sincronizar_operacao_ordem():
    """Reaplica uma operação confirmada após a interrupção de uma gravação."""
    try:
        operacao = persistencia.carregar_json(ARQUIVO_OPERACAO)
    except FileNotFoundError:
        return
    gravar_kardex(operacao["movimentos"])
    persistencia.salvar_json(ARQUIVO_ESTOQUE, operacao["saldos"])
    persistencia.salvar_json("ordens.json", operacao["ordens"])
    (persistencia.PASTA_DATA / ARQUIVO_OPERACAO).unlink()


def confirmar_operacao_ordem(movimentos, saldos, ordens):
    """Confirma o conjunto por uma única gravação, sob a trava do estoque."""
    persistencia.salvar_json(ARQUIVO_OPERACAO, {
        "movimentos": movimentos, "saldos": saldos, "ordens": ordens,
    })
    try:
        sincronizar_operacao_ordem()
    except OSError:
        # A operação confirmada será reaplicada antes do próximo acesso.
        return False
    return True


def carregar_estado(*, sincronizar=True):
    """Recupera os saldos pelo kardex após uma interrupção."""
    movimentos = ler_kardex()
    saldos = {
        movimento["codigo"]: movimento["saldo_resultante"]
        for movimento in movimentos
    }
    try:
        saldos_salvos = persistencia.carregar_json(ARQUIVO_ESTOQUE)
    except FileNotFoundError:
        saldos_salvos = {}

    if saldos_salvos != saldos:
        if not movimentos:
            raise ValueError("Há saldos salvos, mas o kardex está vazio.")
        if sincronizar:
            persistencia.salvar_json(ARQUIVO_ESTOQUE, saldos)
    return movimentos, saldos


def buscar_item_estoque(codigo):
    item = buscar_item(persistencia.carregar_json(ARQUIVO_ITENS), codigo)
    if item is None:
        raise ValueError(f"Item {codigo} não encontrado no cadastro.")
    return item


def validar_quantidade(valor, tipo):
    try:
        quantidade = Decimal(str(valor).strip().replace(",", "."))
    except DecimalException as erro:
        raise ValueError("Informe uma quantidade numérica.") from erro

    if not quantidade.is_finite():
        raise ValueError("Informe uma quantidade finita.")
    if tipo == "AJUSTE":
        if quantidade < 0:
            raise ValueError("O saldo contado deve ser maior ou igual a zero.")
    elif quantidade <= 0:
        raise ValueError("Informe uma quantidade maior que zero.")
    if quantidade == 0:
        return Decimal(0)
    return quantidade


def registrar_movimento(codigo, tipo, quantidade, documento_motivo):
    """Retorna (saldo resultante, JSON sincronizado).

    Para AJUSTE, a quantidade informada é o saldo contado. O kardex guarda
    a diferença entre esse valor e o saldo anterior, inclusive se for zero.
    """
    buscar_item_estoque(codigo)
    if tipo not in ("ENTRADA", "SAIDA", "AJUSTE"):
        raise ValueError("Tipo de movimentação inválido.")
    quantidade = validar_quantidade(quantidade, tipo)
    if not isinstance(documento_motivo, str) or not documento_motivo.strip():
        raise ValueError("Informe o documento ou motivo da movimentação.")

    with acesso_estoque():
        movimentos, saldos = carregar_estado()
        movimento = preparar_movimento(
            saldos, codigo, tipo, quantidade, documento_motivo
        )
        movimentos.append(movimento)
        gravar_kardex(movimentos)
        saldo = Decimal(movimento["saldo_resultante"])
        try:
            persistencia.salvar_json(ARQUIVO_ESTOQUE, saldos)
        except OSError:
            # O movimento já foi confirmado no kardex e pode ser recuperado.
            return saldo, False
        return saldo, True


def preparar_movimento(saldos, codigo, tipo, quantidade, documento_motivo):
    """Aplica ao saldo em memória um movimento previamente validado."""
    saldo_atual = Decimal(saldos.get(codigo, "0"))
    if tipo == "SAIDA" and quantidade > saldo_atual:
        raise ValueError(
            f"Saldo insuficiente de {codigo}. Saldo atual: {saldo_atual}."
        )
    try:
        with localcontext() as contexto:
            contexto.traps[Inexact] = True
            if tipo == "ENTRADA":
                saldo = saldo_atual + quantidade
            elif tipo == "SAIDA":
                saldo = saldo_atual - quantidade
            else:
                saldo = quantidade
                quantidade = saldo - saldo_atual
    except DecimalException as erro:
        raise ValueError("Quantidade fora da precisão do estoque.") from erro

    saldos[codigo] = str(saldo)
    return {
        "data": datetime.now().astimezone().isoformat(timespec="seconds"),
        "codigo": codigo,
        "tipo": tipo,
        "quantidade": str(quantidade),
        "documento_motivo": documento_motivo.strip(),
        "saldo_resultante": saldos[codigo],
    }


def consultar_saldo(codigo):
    """Retorna os dados do item e seu saldo em Decimal."""
    item = buscar_item_estoque(codigo)
    with acesso_estoque():
        _, saldos = carregar_estado()
    return item, Decimal(saldos.get(codigo, "0"))


def consultar_saldos():
    """Retorna os saldos do kardex sem atualizar o arquivo de estoque."""
    with acesso_estoque():
        _, saldos = carregar_estado(sincronizar=False)
    return {codigo: Decimal(saldo) for codigo, saldo in saldos.items()}


def consultar_kardex(codigo=None):
    """Retorna as movimentações em ordem de registro, com filtro opcional."""
    if codigo is not None:
        buscar_item_estoque(codigo)
    with acesso_estoque():
        movimentos, _ = carregar_estado()
    if codigo is None:
        return movimentos
    return [
        movimento for movimento in movimentos if movimento["codigo"] == codigo
    ]


def exibir_saldo_item(item, saldo):
    codigo = item["codigo"]
    descricao = item["descricao"]
    unidade = item["unidade"]
    seguranca = item["estoque_seguranca"]
    quantidade = str(saldo).replace(".", ",")
    print(f"Saldo de {codigo} | {descricao}: {quantidade} {unidade}.")
    if saldo < seguranca:
        print(
            "Alerta: saldo abaixo do estoque de segurança "
            f"({seguranca} {unidade})."
        )


def informar_movimento(tipo):
    codigo = ler_codigo("Código do item: ")
    item = buscar_item_estoque(codigo)
    if tipo == "AJUSTE":
        mensagem = "Saldo contado no inventário: "
        campo_documento = "Motivo do ajuste: "
    else:
        mensagem = "Quantidade: "
        campo_documento = "Documento ou motivo: "

    while True:
        valor = ler_texto(mensagem)
        try:
            quantidade = validar_quantidade(valor, tipo)
            break
        except ValueError as erro:
            print(erro)

    documento = ler_texto(campo_documento)
    saldo, sincronizado = registrar_movimento(
        codigo, tipo, quantidade, documento
    )
    print("Movimentação registrada no kardex.")
    if not sincronizado:
        print("O arquivo de saldos será atualizado no próximo acesso.")
    exibir_saldo_item(item, saldo)


def exibir_saldo():
    codigo = ler_codigo("Código do item: ")
    item, saldo = consultar_saldo(codigo)
    exibir_saldo_item(item, saldo)


def exibir_kardex():
    codigo = input("Código do item (Enter para todos): ").strip().upper()
    movimentos = consultar_kardex(codigo or None)
    if not movimentos:
        print("Nenhuma movimentação encontrada.")
        return

    print("Data | Item | Tipo | Quantidade | Documento ou motivo | Saldo")
    for movimento in movimentos:
        campos = [movimento[campo] for campo in CAMPOS_KARDEX]
        print(" | ".join(campos))
