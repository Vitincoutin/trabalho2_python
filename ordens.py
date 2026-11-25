"""Ordens de produção e de compra geradas pelo MRP."""

from decimal import DecimalException, Inexact, localcontext
from uuid import uuid4

import persistencia
from estoque import (
    acesso_estoque,
    carregar_estado,
    confirmar_operacao_ordem,
    preparar_movimento,
)
from estrutura import carregar_estruturas
from itens import ARQUIVO_ITENS
from mps import carregar_mps
from mrp import calcular_mrp, preparar_bom, quantidade_positiva
from utils import ler_texto


ARQUIVO_ORDENS = "ordens.json"


def _ler_ordens():
    try:
        ordens = persistencia.carregar_json(ARQUIVO_ORDENS)
    except FileNotFoundError:
        return []
    if not isinstance(ordens, list):
        raise ValueError("Formato inválido no arquivo de ordens.")
    return ordens


def carregar_ordens():
    with acesso_estoque():
        return _ler_ordens()


def _nova_ordem(proposta):
    tipo = "OP" if proposta["tipo"] == "PRODUCAO" else "OC"
    return {
        "id": f"{tipo}-{uuid4().hex[:12].upper()}",
        "tipo": tipo,
        "codigo": proposta["codigo"],
        "quantidade": str(proposta["quantidade"]),
        "semana_liberacao": proposta["semana_liberacao"],
        "semana_recebimento": proposta["semana_recebimento"],
        "status": "PLANEJADA",
        "atrasada": proposta["semana_liberacao"] < 1,
    }


def recalcular_ordens():
    """Calcula o MRP e substitui as propostas ainda planejadas."""
    with acesso_estoque():
        ordens = [
            ordem for ordem in _ler_ordens() if ordem["status"] != "PLANEJADA"
        ]
        resultados = _calcular_com_ordens(ordens)
        ordens.extend(
            _nova_ordem(proposta)
            for registro in resultados.values()
            for proposta in registro["ordens_planejadas"]
        )
        persistencia.salvar_json(ARQUIVO_ORDENS, ordens)
        return resultados


def calcular_previsao():
    """Consulta a projeção a partir do mesmo estado de estoque e ordens."""
    with acesso_estoque():
        return _calcular_com_ordens(_ler_ordens())


def _calcular_com_ordens(ordens):
    _, saldos = carregar_estado(sincronizar=False)
    return calcular_mrp(
        persistencia.carregar_json(ARQUIVO_ITENS),
        carregar_mps(),
        carregar_estruturas(),
        saldos,
        ordens,
    )


def _buscar_ordem(ordens, identificador):
    for ordem in ordens:
        if ordem["id"] == identificador:
            return ordem
    raise ValueError(f"Ordem {identificador} não encontrada.")


def _avancar_ordem(identificador, origem, destino):
    with acesso_estoque():
        ordens = _ler_ordens()
        ordem = _buscar_ordem(ordens, identificador)
        if ordem["status"] != origem:
            raise ValueError(f"A ordem precisa estar no status {origem}.")
        ordem["status"] = destino
        persistencia.salvar_json(ARQUIVO_ORDENS, ordens)


def firmar_ordem(identificador):
    _avancar_ordem(identificador, "PLANEJADA", "FIRME")


def liberar_ordem(identificador):
    _avancar_ordem(identificador, "FIRME", "LIBERADA")


def _encerrar_ordem(identificador, tipo):
    """Efetiva os movimentos da ordem inteira e retorna a sincronização."""
    with acesso_estoque():
        ordens = _ler_ordens()
        ordem = _buscar_ordem(ordens, identificador)
        if ordem["tipo"] != tipo or ordem["status"] != "LIBERADA":
            raise ValueError(f"A operação exige uma {tipo} LIBERADA.")

        cadastro = {
            item["codigo"]: item
            for item in persistencia.carregar_json(ARQUIVO_ITENS)
        }
        codigo = ordem["codigo"]
        tipos = ("PA", "SA") if tipo == "OP" else ("MP",)
        if codigo not in cadastro or cadastro[codigo]["tipo"] not in tipos:
            raise ValueError(
                f"Tipo de item incompatível com a ordem {identificador}."
            )

        movimentos, saldos = carregar_estado(sincronizar=False)
        quantidade = quantidade_positiva(ordem["quantidade"], identificador)
        if tipo == "OP":
            bom = preparar_bom(carregar_estruturas(), cadastro)
            componentes = bom.get(codigo)
            if not componentes:
                raise ValueError(f"Cadastre a estrutura do item {codigo}.")
            for componente, consumo in componentes.items():
                try:
                    with localcontext() as contexto:
                        contexto.traps[Inexact] = True
                        necessaria = consumo * quantidade
                except DecimalException as erro:
                    raise ValueError(
                        "Consumo fora da precisão do estoque."
                    ) from erro
                movimentos.append(preparar_movimento(
                    saldos, componente, "SAIDA", necessaria, identificador
                ))

        movimentos.append(preparar_movimento(
            saldos, codigo, "ENTRADA", quantidade, identificador
        ))
        ordem["status"] = "ENCERRADA"
        return confirmar_operacao_ordem(movimentos, saldos, ordens)


def apontar_producao(identificador):
    return _encerrar_ordem(identificador, "OP")


def receber_compra(identificador):
    return _encerrar_ordem(identificador, "OC")


def exibir_ordens():
    ordens = carregar_ordens()
    if not ordens:
        print("Nenhuma ordem registrada. Execute o MRP para gerar propostas.")
        return
    print("ID | Tipo | Item | Quantidade | Liberação | Entrega | Status | Atraso")
    for ordem in ordens:
        atraso = "Sim" if ordem["atrasada"] else "Não"
        print(
            f'{ordem["id"]} | {ordem["tipo"]} | {ordem["codigo"]} | '
            f'{ordem["quantidade"]} | {ordem["semana_liberacao"]} | '
            f'{ordem["semana_recebimento"]} | {ordem["status"]} | {atraso}'
        )


def informar_ordem(acao):
    identificador = ler_texto("Identificador da ordem: ").upper()
    sincronizada = acao(identificador)
    print(f"Operação confirmada para {identificador}.")
    if sincronizada is False:
        print("Os arquivos serão sincronizados no próximo acesso.")
