from persistencia import carregar_json, salvar_json
from utils import ler_codigo, ler_numero, ler_texto


ARQUIVO_ITENS = "itens.json"


def buscar_item(itens, codigo):
    for item in itens:
        if item["codigo"] == codigo:
            return item
    return None


def preencher_item(codigo, atual=None):
    dados = {} if atual is None else atual
    return {
        "codigo": codigo,
        "tipo": codigo.split("-")[0],
        "descricao": ler_texto("Descrição: ", dados.get("descricao")),
        "unidade": ler_texto("Unidade de medida: ", dados.get("unidade")),
        "custo_unitario": ler_numero(
            "Custo unitário (R$): ", float, atual=dados.get("custo_unitario")
        ),
        "lead_time": ler_numero(
            "Lead time em semanas: ", atual=dados.get("lead_time")
        ),
        "estoque_seguranca": ler_numero(
            "Estoque de segurança: ", atual=dados.get("estoque_seguranca")
        ),
        "lote_minimo": ler_numero(
            "Lote mínimo: ", minimo=1, atual=dados.get("lote_minimo")
        ),
    }


def cadastrar_item():
    itens = carregar_json(ARQUIVO_ITENS)
    codigo = ler_codigo("Código do novo item (PA, SA ou MP): ")
    if buscar_item(itens, codigo) is not None:
        print("Já existe um item com esse código.")
        return

    itens.append(preencher_item(codigo))
    salvar_json(ARQUIVO_ITENS, itens)
    print("Item cadastrado com sucesso.")


def listar_itens():
    itens = carregar_json(ARQUIVO_ITENS)
    if not itens:
        print("Nenhum item cadastrado.")
        return

    for item in itens:
        print(f'{item["codigo"]} | {item["descricao"]} | {item["unidade"]}')


def exibir_item(item):
    print(f'Código: {item["codigo"]}')
    print(f'Tipo: {item["tipo"]}')
    print(f'Descrição: {item["descricao"]}')
    print(f'Unidade de medida: {item["unidade"]}')
    custo = f'{item["custo_unitario"]:.2f}'.replace(".", ",")
    print(f"Custo unitário: R$ {custo}")
    print(f'Lead time: {item["lead_time"]} semana(s)')
    print(f'Estoque de segurança: {item["estoque_seguranca"]}')
    print(f'Lote mínimo: {item["lote_minimo"]}')


def consultar_item():
    itens = carregar_json(ARQUIVO_ITENS)
    item = buscar_item(itens, ler_codigo("Código para consulta: "))
    if item is None:
        print("Item não encontrado.")
        return
    exibir_item(item)


def alterar_item():
    itens = carregar_json(ARQUIVO_ITENS)
    codigo = ler_codigo("Código do item a alterar: ")
    item = buscar_item(itens, codigo)
    if item is None:
        print("Item não encontrado.")
        return

    exibir_item(item)
    print("Pressione Enter para manter o valor atual de um campo.")
    item.update(preencher_item(codigo, item))
    salvar_json(ARQUIVO_ITENS, itens)
    print("Item alterado com sucesso.")
