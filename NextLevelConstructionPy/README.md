# Next Level Construction — Material List (Python)

Versão em Python do app de computador. Está sendo portada do app Java (`../NextLevelConstruction`) em etapas.
O Java continua funcionando até o Python ter as mesmas telas.

## Estado

- **Pronto (núcleo, sem telas):** cálculo de QTY, ItemKey, preços, Ordered (soma por GROUP), Received (entregue x pedido),
  Audit Log (ADDED/CHANGED/REMOVED), formatação igual à do web, banco SQLite e acesso aos dados.
- **Telas (PySide6):** janela principal com barra de cima/baixo, Home com os círculos dos jobs e "+ New Job", menu do job com os
  19 círculos, a Lista (All Jobs), **Ordered (auto)** e **Audit Log** (com Export CSV), **Suppliers & Tax** e **Materials DB** (tabelas editáveis, salvam na hora) e a navegação de volta. As demais telas mostram um aviso "ainda não foi portada".
- **Falta:** Dashboard, seções de takeoff, Received e Config.

## Estrutura

| Arquivo | O que é |
|---|---|
| `nlc/calc.py` | Toda a regra de negócio (porta do `CalcEngine.java`) |
| `nlc/seed.py` | Listas fixas (GROUP, SPECIES, LENGTH, ...), geradas a partir do `SeedData.java` |
| `nlc/db.py`, `nlc/schema.sql` | Banco SQLite. Por padrão o mesmo arquivo do Java: `~/NextLevelConstruction/material_list.db` (ou a variável `NLC_DB`) |
| `nlc/dao.py` | Leitura e gravação de cada tabela |
| `nlc/audit.py` | Linha de base e comparação do Audit Log |
| `nlc/inputs.py` | Leitura de números digitados nas células (campo vazio = 0, texto inválido é recusado) |
| `nlc/reports.py` | Linhas das tabelas e texto do CSV de Ordered e Audit Log (iguais aos do web) |
| `nlc/formatting.py` | Formatação de datas igual à do web ("Oct 16, 2026") |
| `nlc/tiles.py` | Os 19 círculos do menu do job e as abreviações |
| `nlc/ui/` | Telas em PySide6 (tema, círculos, Home, Lista, menu do job, Ordered, Audit Log, Suppliers, Materials DB, janela principal) |
| `tests/` | Testes (`unittest`, sem instalar nada) |

## Como rodar

```powershell
cd NextLevelConstructionPy
python -m venv .venv                      # só na primeira vez
.\.venv\Scripts\python -m pip install PySide6   # só na primeira vez
.\.venv\Scripts\python -m nlc                   # abre o app
```

## Testes

```powershell
$env:QT_QPA_PLATFORM = "offscreen"        # testa as telas sem abrir janela
.\.venv\Scripts\python -I -m unittest discover -s tests -t . -v
```

Sem o PySide6 (usando o `python` do sistema) os testes de tela são pulados e o resto roda.

`tests/test_parity_java.py` roda o `CalcEngine` do Java e o `calc.py` nas mesmas ~45 mil entradas e compara QTY, comprimento
e ItemKey. Precisa do Java compilado em `../NextLevelConstruction/bin` (senão é pulado).

## Diferença conhecida em relação ao Java

Texto de comprimento inválido: o Java aceita `12d`, `5f`, `NaN` e `Infinity` como número (peculiaridade do
`Double.parseDouble`), o web lê só o começo do texto (`parseFloat`: `5f` vira 5) e o Excel (`VALUE`) rejeita todos.
O Python rejeita (sem comprimento), como o Excel. Em uso normal o comprimento vem da lista, então isso quase não aparece.
