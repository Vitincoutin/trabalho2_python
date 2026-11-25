"""Gráficos em PNG e exibição quando há um backend gráfico disponível."""

import persistencia
from capacidade import calcular_crp
from estoque import consultar_saldos
from itens import ARQUIVO_ITENS
from mps import SEMANAS
from ordens import carregar_ordens
from relatorios import pasta_saida


def _criar_figura(*, figsize=None):
    try:
        import matplotlib.pyplot as plt
    except ImportError as erro:
        raise ValueError(
            "Instale o Matplotlib com python -m pip install -r requirements.txt."
        ) from erro
    try:
        figura, eixo = plt.subplots(figsize=figsize)
    except ImportError:
        plt.switch_backend("Agg")
        figura, eixo = plt.subplots(figsize=figsize)
    return plt, figura, eixo


def _salvar(plt, figura, nome, exibir):
    caminho = pasta_saida() / nome
    try:
        figura.savefig(caminho, dpi=140, bbox_inches="tight")
        if exibir and figura.canvas.required_interactive_framework is not None:
            plt.show()
    finally:
        plt.close(figura)
    return caminho


def grafico_estoque_atual(*, exibir=True):
    itens = persistencia.carregar_json(ARQUIVO_ITENS)
    saldos = consultar_saldos()
    rotulos = [f'{item["codigo"]} ({item["unidade"]})' for item in itens]
    posicoes = list(range(len(itens)))
    plt, figura, eixo = _criar_figura(figsize=(9, max(3, 0.38 * len(itens))))
    eixo.barh(
        [i - 0.2 for i in posicoes],
        [saldos.get(item["codigo"], 0) for item in itens],
        height=0.4, label="Saldo atual",
    )
    eixo.barh(
        [i + 0.2 for i in posicoes],
        [item["estoque_seguranca"] for item in itens],
        height=0.4, label="Estoque de segurança",
    )
    eixo.set_yticks(posicoes, rotulos)
    eixo.invert_yaxis()
    eixo.set(
        title="Posição atual dos estoques", xlabel="Quantidade na unidade do item"
    )
    eixo.legend()
    return _salvar(plt, figura, "estoque_atual.png", exibir)


def grafico_estoque_projetado(resultados, codigo, *, exibir=True):
    if codigo not in resultados:
        raise ValueError(f"Item {codigo} não encontrado no cálculo atual.")
    registro = resultados[codigo]
    item = registro["item"]
    projetados = [sem["estoque_projetado"] for sem in registro["semanas"]]
    plt, figura, eixo = _criar_figura()
    eixo.plot(SEMANAS, projetados, marker="o", label="Estoque projetado")
    eixo.axhline(
        item["estoque_seguranca"], color="tab:orange", linestyle="--",
        label="Estoque de segurança",
    )
    eixo.set(
        title=f"Estoque projetado de {codigo}", xlabel="Semana",
        ylabel=f'Quantidade ({item["unidade"]})', xticks=list(SEMANAS),
    )
    eixo.legend()
    return _salvar(plt, figura, f"estoque_projetado_{codigo}.png", exibir)


def grafico_ordens(*, exibir=True):
    contagem = {tipo: dict.fromkeys(SEMANAS, 0) for tipo in ("OP", "OC")}
    for ordem in carregar_ordens():
        semana = ordem["semana_recebimento"]
        if semana in SEMANAS:
            contagem[ordem["tipo"]][semana] += 1

    producao = list(contagem["OP"].values())
    plt, figura, eixo = _criar_figura()
    eixo.bar(SEMANAS, producao, label="Ordens de produção")
    eixo.bar(
        SEMANAS, list(contagem["OC"].values()), bottom=producao,
        label="Ordens de compra",
    )
    eixo.set(
        title="Ordens por semana de entrega", xlabel="Semana",
        ylabel="Número de ordens", xticks=list(SEMANAS),
    )
    eixo.legend()
    return _salvar(plt, figura, "ordens_por_semana.png", exibir)


def grafico_capacidade(codigo, *, exibir=True):
    resultados = calcular_crp()
    if codigo not in resultados:
        raise ValueError(f"Centro {codigo} não encontrado.")
    semanas = resultados[codigo]
    plt, figura, eixo = _criar_figura()
    eixo.bar(
        SEMANAS, [sem["carga"] for sem in semanas], label="Carga",
        color=[
            "tab:red" if sem["sobrecarga"] else "tab:blue" for sem in semanas
        ],
    )
    eixo.plot(
        SEMANAS, [sem["capacidade"] for sem in semanas],
        color="tab:orange", marker="o", label="Capacidade disponível",
    )
    eixo.set(
        title=f"Carga e capacidade de {codigo} (vermelho indica sobrecarga)",
        xlabel="Semana", ylabel="Horas", xticks=list(SEMANAS),
    )
    eixo.legend()
    return _salvar(plt, figura, f"capacidade_{codigo}.png", exibir)
