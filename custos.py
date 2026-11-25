"""Composição do custo padrão por unidade de um produto fabricado."""

from decimal import Decimal

import persistencia
from capacidade import carregar_centros, carregar_roteiros, obter_roteiro
from estrutura import carregar_estruturas
from itens import ARQUIVO_ITENS
from mrp import preparar_bom
from utils import ler_codigo


def _acumular(linhas, codigo, quantidade, custo):
    linha = linhas.setdefault(codigo, {
        "quantidade": Decimal(0), "custo_unitario": custo,
    })
    linha["quantidade"] += quantidade
    linha["subtotal"] = linha["quantidade"] * custo


def calcular_custo_padrao(codigo):
    itens = {
        item["codigo"]: item
        for item in persistencia.carregar_json(ARQUIVO_ITENS)
    }
    if codigo not in itens or itens[codigo]["tipo"] not in ("PA", "SA"):
        raise ValueError("Informe um item PA ou SA cadastrado.")

    bom = preparar_bom(carregar_estruturas(), itens)
    centros = carregar_centros()
    roteiros = carregar_roteiros()
    materiais = {}
    mao_de_obra = {}

    def acumular_item(item, quantidade):
        if itens[item]["tipo"] == "MP":
            custo = Decimal(str(itens[item]["custo_unitario"]))
            _acumular(materiais, item, quantidade, custo)
            return

        componentes = bom.get(item)
        if not componentes:
            raise ValueError(f"Cadastre a estrutura do item {item}.")
        centro, tempo = obter_roteiro(item, roteiros, centros)
        custo_hora = Decimal(str(centros[centro]["custo_hora"]))
        _acumular(mao_de_obra, item, quantidade * tempo, custo_hora)
        mao_de_obra[item]["centro"] = centro

        for componente, consumo in componentes.items():
            acumular_item(componente, quantidade * consumo)

    acumular_item(codigo, Decimal(1))
    total_material = sum(linha["subtotal"] for linha in materiais.values())
    total_mao_de_obra = sum(
        linha["subtotal"] for linha in mao_de_obra.values()
    )
    return {
        "codigo": codigo,
        "materiais": materiais,
        "mao_de_obra": mao_de_obra,
        "total_material": total_material,
        "total_mao_de_obra": total_mao_de_obra,
        "total": total_material + total_mao_de_obra,
    }


def exibir_custo_padrao():
    custo = calcular_custo_padrao(ler_codigo("Código do item fabricado: "))
    print(f'\nCusto padrão por unidade de {custo["codigo"]}')
    print("Material | Consumo | Custo unitário (R$) | Subtotal (R$)")
    for codigo, linha in custo["materiais"].items():
        print(
            f'{codigo} | {linha["quantidade"]} | '
            f'{linha["custo_unitario"]:.2f} | {linha["subtotal"]:.2f}'
        )
    print("\nItem | Centro | Horas | Custo-hora (R$) | Subtotal (R$)")
    for codigo, linha in custo["mao_de_obra"].items():
        print(
            f'{codigo} | {linha["centro"]} | {linha["quantidade"]} | '
            f'{linha["custo_unitario"]:.2f} | {linha["subtotal"]:.2f}'
        )
    print(f'Compras de materiais: R$ {custo["total_material"]:.2f}')
    print(f'Mão de obra: R$ {custo["total_mao_de_obra"]:.2f}')
    print(f'Total por unidade: R$ {custo["total"]:.2f}')
