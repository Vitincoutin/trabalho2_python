# Sistema MRP II — Pedal Forte Bicicletas

Trabalho individual de Programação em Python do CEFET-MG. O sistema usa o
plano de demanda de oito semanas para propor compras e produção, acompanhar
o estoque e verificar capacidade e custo dos produtos.

## Instalação e execução

Use Python 3.10 ou superior e instale o Matplotlib. Execute os comandos na
raiz do projeto.

**Windows (PowerShell)**

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

**Linux**

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
```

Na primeira execução, o sistema cria `data/itens.json` a partir de
`itens_demonstracao.json`. A base inclui 14 itens, duas bicicletas, quatro
semiacabados, suas estruturas e os roteiros de fabricação em dois centros
de trabalho. O sistema usa os arquivos operacionais já existentes e cria
os arquivos de nova operação quando necessário.

## Como utilizar

| Menu principal | Requisitos | Operações |
| --- | --- | --- |
| **1. Cadastros** | RF01 e RF02 | Cadastre, liste, consulte ou altere um item. Informe o pai e o componente para cadastrar, alterar ou remover um vínculo da BOM. Use a opção 9 para ver todos os níveis. |
| **2. Estoque** | RF03 e RF04 | Registre entrada ou saída com um documento. No ajuste, informe o saldo contado e o motivo. Consulte o saldo ou o kardex por item. No kardex, pressione Enter para listar todos. |
| **3. MPS** | RF05 | Informe a demanda de cada semana de um PA. Enter registra zero no cadastro. Altere uma semana ou consulte o plano individual e o consolidado. |
| **4. MRP** | RF07 a RF09 | Execute o cálculo para atualizar propostas. Consulte as oito semanas de um item e veja as necessidades e liberações anteriores à semana 1. |
| **5. Ordens** | RF09 a RF11 | Liste os identificadores, firme as propostas e libere as ordens firmes. Receba as OCs para abastecer o estoque. Aponte primeiro as OPs de SA e depois as de PA. |
| **6. Centros, roteiros e CRP** | RF06 e RF12 | Cadastre, liste ou edite centros com capacidade e custo-hora. Associe um centro e um tempo por unidade a cada PA ou SA. Consulte carga, capacidade, utilização e sobrecarga por semana. |
| **7. Custo padrão** | RF13 | Informe um PA ou SA para conferir consumo e subtotal dos materiais, horas e subtotal da mão de obra e o total em reais por unidade. |
| **8. Relatórios e gráficos** | RF14 e RF16 | Exporte estoque e ordens em CSV. Gere os gráficos de estoque atual, estoque projetado de um item, contagem de OPs e OCs por entrega e carga por centro. |

A associação dos módulos iniciais a RF01–RF05, RF07 e RF08 é provisória.
A definição de RF15 depende da conferência do enunciado original.

Os CSVs são gravados em UTF-8 e os gráficos em PNG na pasta `saida/`,
criada no primeiro uso. O gráfico também abre em uma janela quando o
Matplotlib dispõe de um backend interativo. Em ambiente sem tela, o arquivo
pode ser gerado com `MPLBACKEND=Agg` no Linux, ou
`$env:MPLBACKEND = 'Agg'` no PowerShell.

## Como o MRP calcula

1. O cálculo usa o MPS como necessidade bruta de cada PA e processa os
   itens na ordem PA, SA e MP. O consumo de cada pai é acumulado no
   respectivo componente.
2. A cada semana, some ao estoque anterior os recebimentos programados de
   ordens firmes ou liberadas. A necessidade líquida é o maior valor entre
   zero e a necessidade bruta mais o estoque de segurança menos esse saldo.
3. Se houver necessidade líquida, proponha recebimento na maior quantidade
   entre ela e o lote mínimo. A liberação ocorre na semana de entrega menos
   o lead time. O estoque projetado inclui os recebimentos e desconta a
   necessidade bruta.
4. Multiplique a quantidade de cada OP planejada, firme ou liberada pelo
   consumo unitário de cada componente direto. Lance a necessidade do
   componente na semana de liberação da OP. Some as contribuições de pais
   diferentes. As necessidades anteriores à semana 1 afetam o saldo de
   abertura e têm seção própria na consulta.

## Regras de negócio verificadas

- Os códigos seguem o formato `PA-001`, `SA-010` ou `MP-100`, são únicos e
  determinam o tipo. Um PA pode conter SA e MP, um SA pode conter MP e uma MP
  é folha da estrutura. Cada vínculo guarda um consumo positivo.
- As saídas exigem saldo suficiente. O ajuste registra no kardex a diferença
  entre o saldo contado e o anterior. O histórico identifica cada documento
  ou ordem e registra o saldo resultante.
- O MPS guarda demandas inteiras e não negativas de PA nas semanas 1 a 8.
  As quantidades dos componentes e as movimentações aceitam frações.
- As OPs são para PA e SA e as OCs para MP. O fluxo segue
  `PLANEJADA → FIRME → LIBERADA → ENCERRADA`. A coluna de atraso sinaliza
  liberação calculada antes da semana 1. A semana original fica registrada.
- Um recálculo substitui as ordens planejadas e preserva firmes, liberadas
  e encerradas. O recebimento de OC e o apontamento de OP exigem liberação.
  Para uma OP, cada componente direto deve estar disponível antes da
  confirmação da baixa e da entrada. Uma ordem encerrada rejeita repetição.
- O CRP soma `quantidade × horas por unidade` das OPs liberadas por centro,
  na semana de liberação, dentro do horizonte. A utilização é a carga
  dividida pela capacidade em porcentagem. Acima de 100% há sobrecarga.
- O custo padrão soma as matérias-primas de toda a BOM e a mão de obra de
  cada etapa de fabricação. Um SA contribui com seus insumos e suas horas.
  As horas de uma etapa são multiplicadas pelo custo-hora do centro.

A [matriz de auditoria](docs/auditoria.md) lista RF01 a RF16 e RN01 a RN10,
com as evidências e os pontos que dependem do enunciado original.

## Organização e estruturas de dados

| Arquivo ou pasta | Conteúdo |
| --- | --- |
| `main.py`, `menu.py`, `utils.py` | Entrada da aplicação, menus e validação de entrada. |
| `itens.py`, `estrutura.py`, `estoque.py` | Cadastro dos itens, estrutura de produto, saldos e kardex. |
| `mps.py`, `mrp.py`, `ordens.py` | Demanda, cálculo semanal e fluxo de compras e produção. |
| `capacidade.py`, `custos.py`, `relatorios.py`, `graficos.py` | Centros, roteiros, CRP, custos e saídas. |
| `persistencia.py` | Leitura e gravação de JSON UTF-8 e inicialização dos itens. |
| `data/itens_demonstracao.json`, `itens.json` | Lista de itens com código, tipo, descrição, unidade, custo, lead time, segurança e lote mínimo. |
| `data/estrutura.json` | Dicionário de pais. Cada pai mapeia os códigos dos componentes aos consumos por unidade. |
| `data/mps.json` | Código do PA associado a uma lista de oito demandas. |
| `data/estoque.json`, `movimentos.csv` | Saldos por item e kardex cronológico. O saldo é recuperável pelo kardex. |
| `data/ordens.json` | Lista de ordens com identificador, tipo, item, quantidade, semanas, status e atraso. |
| `data/centros.json`, `roteiros.json` | Centros por código e roteiros por código de item. |
| `tests/`, `docs/`, `saida/` | Testes, auditoria e roteiros de vídeo, relatórios e gráficos gerados. |

Quantidades nas ordens e nos saldos são gravadas como texto decimal. A
finalização de ordens usa a trava do estoque e um registro temporário em
`data/operacao_ordem.json`. Uma interrupção após a confirmação é recuperada
no próximo acesso a estoque ou ordens, sem duplicar as movimentações.

## Testes e apresentação

Com o mesmo interpretador usado na instalação, execute:

```sh
python -m unittest discover -s tests -v
```

Se criou o ambiente virtual acima, substitua `python` pelo caminho do seu
interpretador no exemplo de Windows ou Linux. Os testes usam diretórios
temporários e geram os quatro PNGs com o backend Agg.

- [Roteiro de demonstração](docs/roteiro_demonstracao.md), com cerca de
  8 minutos e 30 segundos.
- [Roteiro de explicação do código](docs/roteiro_codigo.md), com cerca de
  8 minutos.

O `.gitignore` exclui o ambiente virtual, as saídas e os dados operacionais
locais. Antes de publicar futuramente, revise os cadastros de demonstração
em `data/estrutura.json`, `data/centros.json` e `data/roteiros.json`, pois
esses arquivos também recebem alterações feitas pelo menu.
