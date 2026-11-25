# Vídeo 2 — Explicação do código

**Duração prevista** 7 minutos e 55 segundos.

| Tempo | Arquivo | O que explicar |
| --- | --- | --- |
| 0:00–0:40 | `main.py` e `menu.py` | Comece por `main()`. Mostre a inicialização e siga o caminho da opção 4 até o cálculo e a geração das propostas. |
| 0:40–1:30 | `itens.py`, `estrutura.py` e `mps.py` | Abra os JSONs de exemplo e mostre lista, dicionário de componentes e vetor de oito demandas. Explique como o tipo PA, SA ou MP limita os vínculos da BOM. |
| 1:30–2:45 | `mrp.py` | Em `calcular_item()`, mostre a conta de uma semana com valores pequenos. Se a necessidade é 6, a segurança é 5 e o saldo é 2, faltam 9 unidades. Lote mínimo de 10 leva à proposta de 10. Em `somar_componentes()`, explique por que duas rodas por bicicleta geram 20 rodas para uma ordem de 10 bicicletas. |
| 2:45–4:25 | `ordens.py` e `estoque.py` | Siga o fluxo planejada, firme, liberada e encerrada. Mostre `_encerrar_ordem()` validando a BOM e preparando movimentos em memória. Explique como o arquivo de operação permite concluir uma gravação interrompida e como o status impede que uma nova tentativa movimente o estoque outra vez. |
| 4:25–5:35 | `capacidade.py` e `custos.py` | Compare capacidade semanal e horas das OPs liberadas. Siga a função recursiva de custo por um produto, um semiacabado e uma matéria-prima. Mostre onde entram o consumo unitário e o custo-hora. |
| 5:35–6:25 | `relatorios.py` e `graficos.py` | Mostre o caminho dos dados de estoque e ordens até os CSVs e os gráficos. Indique onde o gráfico é salvo e como ele funciona com o backend Agg. |
| 6:25–7:55 | `tests/test_sistema.py` | Execute a suíte e abra o teste do ciclo pelo menu. Mostre as conferências de saldo, kardex e arquivos. Use o teste de falta de componente ou o de falha de gravação para explicar o que está sendo protegido. |

Use dois trechos de código por etapa e reserve tempo para explicar as
quantidades que aparecem no terminal.
