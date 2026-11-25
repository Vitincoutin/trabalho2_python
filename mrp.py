"""Cálculo do planejamento de necessidades de materiais (MRP)."""

from decimal import Decimal, InvalidOperation

from estoque import consultar_saldos
from estrutura import TIPOS_COMPONENTES, carregar_estruturas
from itens import ARQUIVO_ITENS
from mps import SEMANAS, carregar_mps, obter_demandas
from persistencia import carregar_json
from utils import ler_codigo


ZERO = Decimal(0)
CAMPOS_TABELA = (
    ("necessidade_bruta", "Necessidade bruta"),
    ("recebimento_programado", "Recebimentos programados"),
    ("estoque_projetado", "Estoque projetado"),
    ("necessidade_liquida", "Necessidade líquida"),
    ("recebimento_planejado", "Recebimentos planejados"),
    ("liberacao_planejada", "Liberações planejadas"),
)


def quantidade_positiva(valor, origem):
    try:
        quantidade = Decimal(str(valor))
    except InvalidOperation as erro:
        raise ValueError(f"Quantidade inválida em {origem}.") from erro
    if not quantidade.is_finite() or quantidade <= ZERO:
        raise ValueError(f"Quantidade inválida em {origem}.")
    return quantidade


def agrupar_recebimentos(ordens, itens):
    """Soma os recebimentos firmes ou liberados por item e semana."""
    recebimentos = {}
    for ordem in ordens:
        if ordem["status"] not in ("FIRME", "LIBERADA"):
            continue
        semana = ordem["semana_recebimento"]
        if type(semana) is not int:
            raise ValueError("A semana de recebimento deve ser inteira.")
        if semana > SEMANAS.stop - 1:
            continue
        codigo = ordem["codigo"]
        if codigo not in itens:
            raise ValueError(f"Item {codigo} da ordem não cadastrado.")
        quantidade = quantidade_positiva(ordem["quantidade"], codigo)
        agenda = recebimentos.setdefault(codigo, {})
        agenda[semana] = agenda.get(semana, ZERO) + quantidade
    return recebimentos


def preparar_bom(estruturas, itens):
    """Confere os vínculos e converte os consumos unitários para Decimal."""
    bom = {}
    for pai, componentes in estruturas.items():
        if pai not in itens or not isinstance(componentes, dict):
            raise ValueError(f"Estrutura inválida para {pai}.")
        tipos = TIPOS_COMPONENTES[itens[pai]["tipo"]]
        bom[pai] = {}
        for codigo, quantidade in componentes.items():
            vinculo = f"{pai} → {codigo}"
            if codigo not in itens or itens[codigo]["tipo"] not in tipos:
                raise ValueError(f"Vínculo inválido na BOM. {vinculo}.")
            bom[pai][codigo] = quantidade_positiva(quantidade, vinculo)
    return bom


def calcular_item(item, necessidades, recebimentos, saldo_inicial):
    estoque = saldo_inicial
    seguranca = Decimal(item["estoque_seguranca"])
    lote_minimo = Decimal(item["lote_minimo"])
    lead_time = item["lead_time"]
    anteriores = sorted(
        semana for semana in necessidades.keys() | recebimentos.keys()
        if semana < 1
    )
    registros = {}
    propostas = []
    liberacoes = {}

    # Os consumos anteriores à semana 1 afetam a abertura do horizonte.
    for semana in [*anteriores, *SEMANAS]:
        bruta = necessidades.get(semana, ZERO)
        programado = recebimentos.get(semana, ZERO)
        disponivel = estoque + programado
        liquida = max(ZERO, bruta + seguranca - disponivel)
        planejado = ZERO
        if liquida > ZERO:
            planejado = max(liquida, lote_minimo)
            liberacao = semana - lead_time
            status = "ATRASADA" if liberacao < 1 else "PLANEJADA"
            propostas.append({
                "codigo": item["codigo"],
                "tipo": "COMPRA" if item["tipo"] == "MP" else "PRODUCAO",
                "quantidade": planejado,
                "semana_recebimento": semana,
                "semana_liberacao": liberacao,
                "status": status,
            })
            liberacoes[liberacao] = planejado

        estoque = disponivel + planejado - bruta
        registros[semana] = {
            "semana": semana,
            "necessidade_bruta": bruta,
            "recebimento_programado": programado,
            "estoque_projetado": estoque,
            "necessidade_liquida": liquida,
            "recebimento_planejado": planejado,
        }

    for semana, registro in registros.items():
        registro["liberacao_planejada"] = liberacoes.get(semana, ZERO)

    return {
        "item": item,
        "saldo_inicial": saldo_inicial,
        "semanas": [registros[semana] for semana in SEMANAS],
        "necessidades_anteriores": [
            registros[semana] for semana in anteriores
        ],
        "ordens_planejadas": propostas,
    }


def calcular_mrp(itens, planos, estruturas, saldos, ordens=()):
    """Retorna os registros por código, incluindo propostas de ordem."""
    ordens = list(ordens)
    cadastro = {item["codigo"]: item for item in itens}
    bom = preparar_bom(estruturas, cadastro)
    recebimentos = agrupar_recebimentos(ordens, cadastro)
    necessidades = {codigo: {} for codigo in cadastro}
    resultados = {}

    # OPs abertas ainda exigem seus componentes, mesmo sem uma nova proposta.
    for ordem in ordens:
        if (
            ordem.get("tipo") != "OP"
            or ordem["status"] not in ("FIRME", "LIBERADA")
        ):
            continue
        semana = ordem["semana_liberacao"]
        if type(semana) is not int:
            raise ValueError("A semana de liberação deve ser inteira.")
        if semana in SEMANAS or semana < 1:
            somar_componentes(ordem, bom, necessidades)

    for tipo in ("PA", "SA", "MP"):
        for codigo, item in cadastro.items():
            if item["tipo"] != tipo:
                continue
            brutas = necessidades[codigo]
            if tipo == "PA":
                demandas = obter_demandas(planos, codigo)
                brutas.update(zip(SEMANAS, map(Decimal, demandas)))

            saldo = Decimal(str(saldos.get(codigo, ZERO)))
            registro = calcular_item(
                item, brutas, recebimentos.get(codigo, {}), saldo
            )
            resultados[codigo] = registro

            for proposta in registro["ordens_planejadas"]:
                somar_componentes(proposta, bom, necessidades)
    return resultados


def somar_componentes(ordem, bom, necessidades):
    codigo = ordem["codigo"]
    semana = ordem["semana_liberacao"]
    quantidade = quantidade_positiva(ordem["quantidade"], codigo)
    for componente, consumo in bom.get(codigo, {}).items():
        agenda = necessidades[componente]
        agenda[semana] = agenda.get(semana, ZERO) + quantidade * consumo


def executar_mrp(ordens=()):
    """Calcula com os dados atuais, sem gravar propostas ou saldos.

    A integração de ordens pode passar dicionários com codigo, status,
    semana_recebimento e quantidade. As propostas ficam em ordens_planejadas
    no resultado de cada item e preservam a semana calculada de liberação.
    """
    itens = carregar_json(ARQUIVO_ITENS)
    return calcular_mrp(
        itens,
        carregar_mps(),
        carregar_estruturas(),
        consultar_saldos(),
        ordens,
    )


def exibir_atrasos(registro):
    unidade = registro["item"]["unidade"]
    for proposta in registro["ordens_planejadas"]:
        if proposta["status"] == "ATRASADA":
            print(
                f'ATRASADA | {proposta["codigo"]} | '
                f'{formatar_valor(proposta["quantidade"])} {unidade} | '
                f'liberação na semana {proposta["semana_liberacao"]} | '
                f'recebimento na semana {proposta["semana_recebimento"]}'
            )


def formatar_valor(valor):
    inteiro, _, fracao = format(valor, "f").partition(".")
    fracao = fracao.rstrip("0")
    return f"{inteiro},{fracao}" if fracao else inteiro


def exibir_registro(registro):
    item = registro["item"]
    print(f'\n{item["codigo"]} | {item["descricao"]} | {item["unidade"]}')
    saldo = formatar_valor(registro["saldo_inicial"])
    seguranca = item["estoque_seguranca"]
    print(f"Saldo inicial {saldo} | Estoque de segurança {seguranca}")

    linhas = [["Registro", *(f"Sem {semana}" for semana in SEMANAS)]]
    for chave, rotulo in CAMPOS_TABELA:
        valores = [formatar_valor(sem[chave]) for sem in registro["semanas"]]
        linhas.append([rotulo, *valores])
    larguras = [max(map(len, coluna)) for coluna in zip(*linhas)]
    for rotulo, *valores in linhas:
        colunas = [
            valor.rjust(largura)
            for valor, largura in zip(valores, larguras[1:])
        ]
        print(" | ".join([rotulo.ljust(larguras[0]), *colunas]))

    if registro["necessidades_anteriores"]:
        print("Necessidades anteriores ao horizonte")
        for dados in registro["necessidades_anteriores"]:
            print(
                f'Semana {dados["semana"]} | '
                f'NB {formatar_valor(dados["necessidade_bruta"])} | '
                f'NL {formatar_valor(dados["necessidade_liquida"])} | '
                f'EP {formatar_valor(dados["estoque_projetado"])}'
            )
    exibir_atrasos(registro)


def consultar_mrp(resultados):
    codigo = ler_codigo("Código do item: ")
    if codigo not in resultados:
        print(f"Item {codigo} não encontrado no cálculo atual.")
        return
    exibir_registro(resultados[codigo])
