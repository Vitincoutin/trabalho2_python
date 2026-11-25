# Vídeo 1 — Demonstração do sistema

**Duração prevista** 8 minutos e 30 segundos.

## Preparação

- Use uma cópia de demonstração com `itens_demonstracao.json`,
  `estrutura.json`, `centros.json` e `roteiros.json` em `data/`.
  Mantenha a base que você usa no dia a dia em sua pasta original.
- Instale as dependências e abra o projeto no VS Code. Deixe o terminal e
  a pasta `saida/` acessíveis. Execute `python main.py`.
- Use a semana 8 com demanda de 12 bicicletas urbanas `PA-001` e 8 mountain
  bikes `PA-002`. Nas semanas anteriores, informe zero.

| Tempo | O que mostrar e explicar |
| --- | --- |
| 0:00–0:40 | Apresente a Pedal Forte Bicicletas. Mostre o menu principal e explique que a demanda orienta as compras e a fabricação das próximas oito semanas. |
| 0:40–1:30 | No menu 1, consulte `PA-001` e abra sua estrutura completa. Aponte os dois conjuntos de roda e o quadro por bicicleta. Abra o estoque de uma matéria-prima pelo menu 2. |
| 1:30–2:30 | No menu 3, cadastre as duas demandas. Exiba a tabela consolidada e confira a semana 8. |
| 2:30–3:30 | Execute o MRP no menu 4. Selecione `PA-001` e um componente. Compare necessidade bruta, estoque projetado e liberação. Mostre uma ordem marcada com atraso pela liberação anterior à semana 1. |
| 3:30–4:40 | No menu 5, abra a lista de ordens. Firme e libere uma OC e uma OP, mostrando a mudança de status e o mesmo identificador. Libere também uma OP com semana de liberação dentro do horizonte. Consulte a carga do centro no menu 6 antes de encerrar essa OP. |
| 4:40–6:35 | Em uma cópia já preparada no mesmo cenário, com as ordens firmes e liberadas, tente apontar uma OP de SA antes das compras para mostrar a rejeição por falta de saldo. Receba as OCs, aponte as OPs de SA e depois as OPs de PA. Use um corte no vídeo para as operações repetidas e mantenha uma de cada tipo visível. |
| 6:35–7:25 | Consulte o kardex e o saldo de `PA-001`. Mostre a baixa dos componentes e a entrada do produto com o mesmo identificador. No menu 7, confira o custo por unidade e identifique materiais e mão de obra. |
| 7:25–8:30 | No menu 8, exporte os dois CSVs e gere os quatro gráficos. Use a visão de capacidade antes do encerramento das OPs para mostrar a carga. Abra a pasta de saída e confira os nomes e o conteúdo dos arquivos. |

Fale durante as transições entre menus. Ao fechar, siga no kardex um
identificador que tenha aparecido antes na lista de ordens.
