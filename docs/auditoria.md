# Auditoria final — Sistema MRP II

Auditoria realizada em 24 de novembro de 2026. A referência disponível foi o
texto anexado ao pedido. A pasta `docs/` veio sem o PDF do enunciado. A
matriz marca como provisória a associação entre a numeração e os módulos
iniciais, pois o anexo menciona esses módulos sem associá-los a todos os
códigos. Nos demais casos sem definição, a pendência é de verificação do
enunciado.

## Requisitos funcionais

| Código | Implementação observada | Evidência de teste | Pendência |
| --- | --- | --- | --- |
| RF01 | Cadastro, listagem, consulta e alteração de itens | Cadastro e alteração pelo menu, validação de código e duplicidade, persistência entre acessos | Confirmar numeração e redação no PDF |
| RF02 | Cadastro e consulta da BOM, alteração e remoção dos vínculos | Consulta em dois níveis, aceitação de quantidade positiva e rejeição de tipos incompatíveis | Confirmar numeração e redação no PDF |
| RF03 | Estoque com entrada, saída, ajuste e consulta de saldo | Movimentação pelo menu, saída sem saldo rejeitada e alerta de segurança exibido | Confirmar numeração e redação no PDF |
| RF04 | Kardex por item ou consolidado | Histórico conferido no ciclo, com documentos, quantidades e saldo resultante | Confirmar numeração e redação no PDF |
| RF05 | Cadastro, alteração e consulta do MPS | Cadastro com oito semanas, restrição a PA e rejeição de valor negativo e semana inválida | Confirmar numeração e redação no PDF |
| RF06 | Centros de trabalho e roteiros de PA e SA | Alterações persistidas, validação de campos e vínculos, dois centros e seis roteiros de demonstração | — |
| RF07 | Cálculo MRP em oito semanas | Demanda, segurança, lote, lead time, componentes compartilhados e recebimentos programados | Confirmar numeração e redação no PDF |
| RF08 | Consulta dos registros do MRP e indicação de atrasos | Registro com oito colunas, necessidades anteriores e atraso de liberação exibidos no terminal | Confirmar numeração e redação no PDF |
| RF09 | Propostas de OP e OC, estados, atraso, recálculo e persistência | Propostas geradas pelo menu, IDs distintos, substituição seletiva e rejeição de transições inválidas | — |
| RF10 | Apontamento de OP com consumo de componentes, entrada e encerramento | Fabricação de SA e PA, rejeição integral por falta de componente e rejeição de repetição | — |
| RF11 | Recebimento de OC com entrada e encerramento | Recebimento pelo menu, falha de gravação recuperada, duas tentativas simultâneas sem duplicar entrada | — |
| RF12 | CRP com oito semanas, utilização e sobrecarga | Carga de 1,5 h sobre capacidade de 1 h resultou em 150%. Outro centro ficou em 50% | — |
| RF13 | Custo padrão recursivo com material e mão de obra | PA do cenário de teste custou R$ 49,00 por unidade e o SA custou R$ 16,00 | — |
| RF14 | Posição de estoque e ordens exportadas em CSV UTF-8 | Dois CSVs reabertos e conferidos. Os dados de origem mantiveram o mesmo conteúdo | — |
| RF15 | Definição ausente no material disponível | Menu integrado, base de demonstração e persistência exercitados no ciclo | Obter a definição oficial de RF15 para identificar a evidência correspondente |
| RF16 | Quatro gráficos Matplotlib, com exibição interativa quando disponível e geração de PNG | Quatro PNGs reabertos e validados com Agg. As quatro janelas abriram no Windows com TkAgg | — |

## Regras de negócio

| Código | Implementação confirmada pelo anexo | Evidência de teste | Pendência |
| --- | --- | --- | --- |
| RN01 | Redação ausente | — | Obter a definição oficial |
| RN02 | Redação ausente | — | Obter a definição oficial |
| RN03 | Redação ausente | — | Obter a definição oficial |
| RN04 | Redação ausente | — | Obter a definição oficial |
| RN05 | Redação ausente | — | Obter a definição oficial |
| RN06 | Redação ausente | — | Obter a definição oficial |
| RN07 | Redação ausente | — | Obter a definição oficial |
| RN08 | Redação ausente | — | Obter a definição oficial |
| RN09 | CRP considera OPs com status LIBERADA e usa a semana de liberação | As OPs firmes e encerradas ficaram sem carga. As liberadas geraram carga na semana esperada | — |
| RN10 | Redação ausente | — | Obter a definição oficial |

Os comportamentos testados incluem formato e unicidade do código, tipos
permitidos na BOM, saídas sem saldo, demanda semanal de PA, regras de estoque
de segurança, lote mínimo e lead time, recebimentos de ordens firmes ou
liberadas, preservação das ordens ativas e encerradas no recálculo,
atrasos anteriores ao horizonte, rejeição de operações duplicadas e custo
dos semiacabados sem dupla contagem. O PDF é necessário para associar esses
comportamentos aos números das regras.

## Execução

- `python -m unittest discover -s tests -v` executou 17 testes com Python
  3.10.11 no Windows e os mesmos 17 em uma VM Linux x86-64 com Python
  3.10.20. Os 17 passaram em cada ambiente, com Matplotlib 3.10.9.
- O ciclo pelo menu consultou item e BOM, cadastrou demanda, calculou o
  MRP, firmou e liberou cinco ordens, recebeu as compras e fabricou primeiro
  o SA e depois o PA. O saldo final do PA foi de três unidades. Foram
  conferidos nove movimentos no kardex, os cálculos de CRP e custo, dois
  CSVs UTF-8 e quatro PNGs gerados com Agg.
- Um segundo ciclo usou cópias dos cadastros de demonstração e fabricou os
  dois modelos de bicicleta. As ordens terminaram encerradas.
- Um teste interativo adicional no Windows confirmou quatro janelas
  visíveis em TkAgg e reabriu o PNG correspondente a cada uma.
- Os seis arquivos de dados originais permaneceram idênticos, conforme a
  comparação de hashes SHA-256 antes e depois dos testes.

A homologação integral dos itens com definição ausente depende do PDF do
enunciado.
