from capacidade import (
    exibir_centros,
    exibir_crp,
    exibir_roteiros,
    informar_centro,
    informar_roteiro,
)
from custos import exibir_custo_padrao
from estoque import exibir_kardex, exibir_saldo, informar_movimento
from estrutura import (
    alterar_quantidade,
    cadastrar_componente,
    consultar_estrutura,
    exibir_estrutura_completa,
    remover_componente,
)
from graficos import (
    grafico_capacidade,
    grafico_estoque_atual,
    grafico_estoque_projetado,
    grafico_ordens,
)
from itens import alterar_item, cadastrar_item, consultar_item, listar_itens
from mps import (
    alterar_demanda,
    cadastrar_mps,
    carregar_mps,
    consultar_mps,
    exibir_mps_completo,
)
from mrp import consultar_mrp, exibir_atrasos
from ordens import (
    apontar_producao,
    calcular_previsao,
    exibir_ordens,
    firmar_ordem,
    informar_ordem,
    liberar_ordem,
    recalcular_ordens,
    receber_compra,
)
from relatorios import exportar_estoque, exportar_ordens
from utils import ler_codigo, ler_opcao, ler_texto


def menu_cadastros():
    acoes = {
        "1": cadastrar_item,
        "2": listar_itens,
        "3": consultar_item,
        "4": alterar_item,
        "5": cadastrar_componente,
        "6": consultar_estrutura,
        "7": alterar_quantidade,
        "8": remover_componente,
        "9": exibir_estrutura_completa,
    }

    while True:
        print("\nCadastros de itens e estruturas")
        print("1. Cadastrar item")
        print("2. Listar itens")
        print("3. Consultar item")
        print("4. Alterar item")
        print("5. Cadastrar componente")
        print("6. Consultar estrutura do produto")
        print("7. Alterar quantidade de componente")
        print("8. Remover componente")
        print("9. Exibir estrutura completa")
        print("0. Voltar")
        opcao = ler_opcao("Escolha uma opção: ", ("0", *acoes))
        if opcao == "0":
            return
        try:
            acoes[opcao]()
        except (OSError, ValueError) as erro:
            print(f"Erro ao acessar os dados: {erro}")


def menu_estoque():
    tipos = {"1": "ENTRADA", "2": "SAIDA", "3": "AJUSTE"}
    while True:
        print("\nEstoque")
        print("1. Registrar entrada")
        print("2. Registrar saída")
        print("3. Ajustar inventário")
        print("4. Consultar saldo")
        print("5. Exibir kardex")
        print("0. Voltar")
        opcao = ler_opcao("Escolha uma opção: ", tuple("012345"))
        if opcao == "0":
            return
        try:
            if opcao in tipos:
                informar_movimento(tipos[opcao])
            elif opcao == "4":
                exibir_saldo()
            else:
                exibir_kardex()
        except (OSError, ValueError) as erro:
            print(erro)


def menu_mps(planos):
    acoes = {
        "1": cadastrar_mps,
        "2": alterar_demanda,
        "3": consultar_mps,
        "4": exibir_mps_completo,
    }

    while True:
        print("\nPlano Mestre de Produção (MPS)")
        print("1. Cadastrar demanda semanal")
        print("2. Alterar demanda de uma semana")
        print("3. Consultar MPS de um produto")
        print("4. Exibir MPS de todos os produtos acabados")
        print("0. Voltar")
        opcao = ler_opcao("Escolha uma opção: ", ("0", *acoes))
        if opcao == "0":
            return
        try:
            acoes[opcao](planos)
        except (OSError, ValueError) as erro:
            print(erro)


def menu_mrp():
    resultados = None
    while True:
        print("\nPlanejamento de necessidades de materiais (MRP)")
        print("1. Executar cálculo MRP")
        print("2. Consultar registro de um item")
        print("0. Voltar")
        opcao = ler_opcao("Escolha uma opção: ", ("0", "1", "2"))
        if opcao == "0":
            return
        try:
            if opcao == "1":
                resultados = recalcular_ordens()
                print(f"MRP calculado para {len(resultados)} item(ns).")
                print("Propostas atualizadas no menu de ordens.")
                for registro in resultados.values():
                    exibir_atrasos(registro)
            elif resultados is None:
                print("Execute o cálculo antes de consultar um item.")
            else:
                consultar_mrp(resultados)
        except (OSError, ValueError) as erro:
            print(f"Erro no MRP: {erro}")


def menu_acoes(titulo, acoes):
    """Exibe ações que dispensam argumentos e trata erros no próprio menu."""
    while True:
        print(f"\n{titulo}")
        for numero, (rotulo, _) in acoes.items():
            print(f"{numero}. {rotulo}")
        print("0. Voltar")
        opcao = ler_opcao("Escolha uma opção: ", ("0", *acoes))
        if opcao == "0":
            return
        try:
            _, acao = acoes[opcao]
            acao()
        except (OSError, ValueError) as erro:
            print(f"Erro: {erro}")


def menu_ordens():
    menu_acoes("Ordens de produção e compra", {
        "1": ("Listar ordens", exibir_ordens),
        "2": ("Firmar ordem planejada", lambda: informar_ordem(firmar_ordem)),
        "3": ("Liberar ordem firme", lambda: informar_ordem(liberar_ordem)),
        "4": ("Apontar produção", lambda: informar_ordem(apontar_producao)),
        "5": ("Receber compra", lambda: informar_ordem(receber_compra)),
    })


def menu_capacidade():
    menu_acoes("Centros de trabalho, roteiros e CRP", {
        "1": ("Consultar carga e capacidade (CRP)", exibir_crp),
        "2": ("Cadastrar centro de trabalho", informar_centro),
        "3": ("Listar centros de trabalho", exibir_centros),
        "4": ("Alterar centro de trabalho", lambda: informar_centro(True)),
        "5": ("Cadastrar ou alterar roteiro", informar_roteiro),
        "6": ("Listar roteiros", exibir_roteiros),
    })


def exibir_saida(gerar):
    print(f"Arquivo salvo em {gerar()}")


def gerar_projecao():
    codigo = ler_codigo("Código do item: ")
    resultados = calcular_previsao()
    exibir_saida(lambda: grafico_estoque_projetado(resultados, codigo))


def gerar_grafico_centro():
    codigo = ler_texto("Código do centro: ").upper()
    exibir_saida(lambda: grafico_capacidade(codigo))


def menu_relatorios():
    menu_acoes("Relatórios CSV e gráficos PNG", {
        "1": (
            "Exportar posição de estoque", lambda: exibir_saida(exportar_estoque)
        ),
        "2": ("Exportar ordens", lambda: exibir_saida(exportar_ordens)),
        "3": (
            "Gráfico de estoque atual", lambda: exibir_saida(grafico_estoque_atual)
        ),
        "4": ("Gráfico de estoque projetado", gerar_projecao),
        "5": (
            "Gráfico de ordens por semana", lambda: exibir_saida(grafico_ordens)
        ),
        "6": ("Gráfico de carga e capacidade", gerar_grafico_centro),
    })


def menu_principal():
    acoes = {
        "1": menu_cadastros,
        "2": menu_estoque,
        "3": lambda: menu_mps(carregar_mps()),
        "4": menu_mrp,
        "5": menu_ordens,
        "6": menu_capacidade,
        "7": exibir_custo_padrao,
        "8": menu_relatorios,
    }
    while True:
        print("\nSistema MRP II — Pedal Forte Bicicletas")
        print("1. Cadastros")
        print("2. Estoque")
        print("3. Plano Mestre de Produção (MPS)")
        print("4. Executar MRP")
        print("5. Ordens de produção e compra")
        print("6. Centros de trabalho, roteiros e CRP")
        print("7. Custo padrão")
        print("8. Relatórios e gráficos")
        print("0. Sair")

        opcao = ler_opcao("Escolha uma opção: ", ("0", *acoes))
        if opcao == "0":
            print("Sistema encerrado.")
            return
        try:
            acoes[opcao]()
        except (OSError, ValueError) as erro:
            print(f"Erro: {erro}")
