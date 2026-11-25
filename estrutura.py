"""Cadastro e consulta da estrutura de fabricação dos produtos (BOM)."""

from itens import ARQUIVO_ITENS, buscar_item
from persistencia import carregar_json, salvar_json
from utils import ler_codigo, ler_numero


ARQUIVO_ESTRUTURA = "estrutura.json"

# A sequência mais longa permitida é PA -> SA -> MP.
TIPOS_COMPONENTES = {
    "PA": ("SA", "MP"),
    "SA": ("MP",),
    "MP": (),
}


def carregar_estruturas():
    """Carrega o dicionário de pais, componentes e quantidades."""
    try:
        dados = carregar_json(ARQUIVO_ESTRUTURA)
    except FileNotFoundError:
        return {}
    if not isinstance(dados, dict):
        raise ValueError("Formato inválido no arquivo de estruturas.")
    return dados


def ler_item(itens, mensagem):
    codigo = ler_codigo(mensagem)
    item = buscar_item(itens, codigo)
    if item is None:
        print(f"Item {codigo} não encontrado no cadastro.")
    return item


def ler_quantidade(mensagem):
    while True:
        quantidade = ler_numero(mensagem, float)
        if quantidade > 0:
            return quantidade
        print("Informe uma quantidade maior que zero.")


def cadastrar_componente():
    itens = carregar_json(ARQUIVO_ITENS)
    pai = ler_item(itens, "Código do item pai: ")
    if pai is None:
        return
    tipos = TIPOS_COMPONENTES[pai["tipo"]]
    if not tipos:
        print("Uma matéria-prima não pode possuir componentes.")
        return

    componente = ler_item(itens, "Código do componente: ")
    if componente is None:
        return
    if componente["tipo"] not in tipos:
        permitidos = " ou ".join(tipos)
        print(f'Componentes permitidos para {pai["codigo"]}: {permitidos}.')
        return

    estruturas = carregar_estruturas()
    componentes = estruturas.setdefault(pai["codigo"], {})
    codigo = componente["codigo"]
    if codigo in componentes:
        print("Esse componente já está cadastrado neste item pai.")
        return

    componentes[codigo] = ler_quantidade("Quantidade por unidade do pai: ")
    salvar_json(ARQUIVO_ESTRUTURA, estruturas)
    print("Componente cadastrado com sucesso.")


def alterar_quantidade():
    estruturas = carregar_estruturas()
    pai = ler_codigo("Código do item pai: ")
    codigo = ler_codigo("Código do componente: ")
    componentes = estruturas.get(pai, {})
    if codigo not in componentes:
        print("Componente não encontrado na estrutura deste item pai.")
        return

    atual = formatar_quantidade(componentes[codigo])
    print(f"Quantidade atual por unidade do item pai: {atual}")
    componentes[codigo] = ler_quantidade("Nova quantidade por unidade: ")
    salvar_json(ARQUIVO_ESTRUTURA, estruturas)
    print("Quantidade alterada com sucesso.")


def remover_componente():
    estruturas = carregar_estruturas()
    pai = ler_codigo("Código do item pai: ")
    codigo = ler_codigo("Código do componente: ")
    componentes = estruturas.get(pai, {})
    if codigo not in componentes:
        print("Componente não encontrado na estrutura deste item pai.")
        return

    del componentes[codigo]
    if not componentes:
        del estruturas[pai]
    salvar_json(ARQUIVO_ESTRUTURA, estruturas)
    print("Componente removido com sucesso.")


def formatar_quantidade(quantidade):
    return str(quantidade).removesuffix(".0").replace(".", ",")


def exibir_niveis(itens, estruturas, codigo, quantidade, nivel, limite):
    item = buscar_item(itens, codigo)
    if item is None:
        raise ValueError(f"O item {codigo} da estrutura não está cadastrado.")

    recuo = "    " * nivel
    quantidade = formatar_quantidade(quantidade)
    print(
        f'{recuo}Nível {nivel} | {codigo} | {item["descricao"]} | '
        f'{quantidade} {item["unidade"]}'
    )
    if nivel < limite:
        for componente, consumo in estruturas.get(codigo, {}).items():
            exibir_niveis(
                itens, estruturas, componente, consumo, nivel + 1, limite
            )


def mostrar_estrutura(limite):
    itens = carregar_json(ARQUIVO_ITENS)
    item = ler_item(itens, "Código do produto: ")
    if item is None:
        return

    estruturas = carregar_estruturas()
    codigo = item["codigo"]
    print("\nQuantidades dos componentes por unidade do item pai.")
    exibir_niveis(
        itens, estruturas, codigo, quantidade=1, nivel=0, limite=limite
    )
    if not estruturas.get(codigo):
        print("Este item não possui componentes cadastrados.")


def consultar_estrutura():
    mostrar_estrutura(1)


def exibir_estrutura_completa():
    mostrar_estrutura(2)
