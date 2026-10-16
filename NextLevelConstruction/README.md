# Next Level Construction — Material List (Java / Eclipse / Swing / SQLite)

Porta em Java desta base do app web "Next Level Construction — Material List".
Esta é a **base sólida** combinada: estrutura completa do projeto, motor de
cálculo completo (fórmula QTY original, ItemKey, preço com imposto), e as
telas Home → Dashboard → Sub-Floor → Materials DB → Suppliers & Tax,
prontas para você estender às outras 12 seções.

## Como importar no Eclipse

1. Abra o Eclipse → `File → Import... → General → Existing Projects into Workspace`
2. Selecione a pasta `NextLevelConstruction` (a que contém `.project`)
3. Eclipse detecta tudo sozinho: código-fonte em `src/`, o driver SQLite já
   incluso em `lib/sqlite-jdbc-3.36.0.3.jar` (sem precisar de internet nem Maven)
4. Rode `com.nlc.materiallist.Main` (botão direito → `Run As → Java Application`)

**Requisito:** JDK 17 ou mais novo (testado com o 21). Se o Eclipse reclamar da
versão, ajuste em `Project → Properties → Java Build Path → Libraries → JRE`.

## Onde os dados ficam salvos

Um único arquivo SQLite local, criado automaticamente na primeira execução:

```
~/NextLevelConstruction/material_list.db
```

Cada projeto/job fica isolado dentro desse mesmo arquivo (uma linha na tabela
`projects`, com todo o resto referenciando `project_id`). Não há sincronização
em nuvem nesta versão — é 100% local no computador, como você pediu.

## O que já funciona

- **Home** → círculos dos jobs, "+ New Job" para criar um novo (sigla + nome)
- **Menu do projeto** → círculos: Dashboard, Sub-Floor, Materials DB, Suppliers & Tax
- **Dashboard** → KPIs (itens, total estimado, pedido, recebido) + campos do projeto
- **Sub-Floor** (seção de exemplo, mas 100% genérica — veja abaixo) → tabela
  editável completa: Group, Purpose, Material, Length, Species, LF/SF/SP/EA,
  QTY (calculado), Location, Unit $ / Total (calculados), Status (clique para
  ciclar Pending → Ordered → Received), exportar CSV, filtro de busca
- **Materials DB** e **Suppliers & Tax** → catálogo de preços e tabela de
  impostos por fornecedor, exatamente como no app web
- **Dropdown dependente Species → Material** — implementado de forma nativa
  do Swing (`MaterialCellEditor`), sem o problema que existia na versão HTML

## Como adicionar as outras 12 seções

`SectionPanel` já é genérico — funciona para qualquer `sectionId` presente em
`SeedData.SECTIONS` (todas as 13 seções originais já estão lá, com as listas
reais de Purpose). Só falta um círculo de menu para cada uma. Em
`ProjectMenuPanel.java`, no bloco `static { TILES.put(...) }`, adicione:

```java
TILES.put("1st-walls", "1st Floor Walls");
TILES.put("2nd-walls", "2nd Floor Walls");
// ... etc, os ids batem com SeedData.SECTIONS
```

Pronto — nenhuma outra mudança de código é necessária.

## Arquitetura

```
com.nlc.materiallist
 ├─ Main.java                  ponto de entrada
 ├─ calc/CalcEngine.java       fórmula QTY, ItemKey, preço — o "coração" do app
 ├─ data/SeedData.java         grupos, comprimentos, espécies, catálogo Species→Material
 │                             (gerado automaticamente a partir dos mesmos dados do app web)
 ├─ db/Database.java           abre/cria o material_list.db e roda o schema.sql
 ├─ dao/                       uma classe por tabela (ProjectDao, TakeoffItemDao, ...)
 ├─ model/                     classes de dados simples (Project, TakeoffItem, ...)
 └─ ui/
     ├─ MainFrame.java         janela principal, CardLayout, botão voltar, menu inferior
     ├─ HomePanel.java         tela de círculos dos jobs
     ├─ ProjectMenuPanel.java  tela de círculos das seções dentro do job
     ├─ DashboardPanel.java
     ├─ SectionPanel.java      tabela editável genérica (JTable + TakeoffTableModel)
     ├─ TakeoffTableModel.java lógica da tabela — cada edição grava no SQLite na hora
     ├─ MaterialCellEditor.java   combo Material dependente da Species
     ├─ SuggestCellEditor.java    combo genérico com sugestões (Group, Length, ...)
     ├─ MaterialsDbPanel.java, SuppliersPanel.java
     └─ CircleButton.java, TableRenderers.java   componentes visuais reutilizáveis
```

## Como isso foi testado

Sem acesso a um ambiente gráfico real neste momento, a verificação foi feita
em duas camadas, ambas passando 100%:

1. **Motor de cálculo** (`CalcEngine`) — testado isoladamente contra os
   mesmos casos usados para validar a versão web (espaçamento, "N Ply",
   "End Stud", desperdício de 5% em roof sheathing, etc.) — todos batendo.
2. **Camada de UI, sem display** — as classes Swing (`JPanel`, `JTable`, etc.)
   não exigem uma tela para *serem construídas*, só para serem *exibidas* numa
   janela. Isso permitiu simular o fluxo completo de um usuário real:
   construir cada tela, clicar em "+ Add line" (via seu listener real),
   editar células (Purpose, Material, Length, Species, LF), conferir que o
   QTY e o preço calculados batem, ciclar o Status, apagar a linha, e
   adicionar material/fornecedor — 22 verificações, todas passando.

O que isso **não** cobre é a aparência visual final (alinhamento, cores,
tamanho das colunas) — isso só se confirma abrindo de verdade no seu Eclipse.
Se algo parecer torto ou um componente não aparecer do jeito esperado, me
mande um print que eu ajusto.

## Limitações desta entrega (por escopo, não por bug)

- Só as 4 telas pedidas estão com círculo de menu (as outras 12 seções já
  funcionam via `SectionPanel`, só faltam os círculos — 1 linha cada, veja acima)
- Sem sincronização entre pessoas/dispositivos (banco local, como combinado)
- Sem log de auditoria nem tela de Received/Ordered automático (existiam na
  versão web) — dá pra portar depois com o mesmo padrão dos DAOs já prontos
- "Lista" no menu inferior hoje reaproveita a tela Home; pode virar uma lista
  de verdade depois, é só trocar uma linha em `MainFrame.bottomNav()`
