# Next Level Construction — Material List (Python)

Versão em Python do app de computador. Está sendo portada do app Java (`../NextLevelConstruction`) em etapas.
O Java continua funcionando até o Python ter as mesmas telas.

## Estado

- **Pronto (núcleo, sem telas):** cálculo de QTY, ItemKey, preços, Ordered (soma por GROUP), Received (entregue x pedido),
  Audit Log (ADDED/CHANGED/REMOVED), formatação igual à do web, banco SQLite e acesso aos dados.
- **Falta:** todas as telas (decidir a biblioteca: PySide6 ou Tkinter) e a tela Config.

## Estrutura

| Arquivo | O que é |
|---|---|
| `nlc/calc.py` | Toda a regra de negócio (porta do `CalcEngine.java`) |
| `nlc/seed.py` | Listas fixas (GROUP, SPECIES, LENGTH, ...), geradas a partir do `SeedData.java` |
| `nlc/db.py`, `nlc/schema.sql` | Banco SQLite. Por padrão o mesmo arquivo do Java: `~/NextLevelConstruction/material_list.db` (ou a variável `NLC_DB`) |
| `nlc/dao.py` | Leitura e gravação de cada tabela |
| `nlc/audit.py` | Linha de base e comparação do Audit Log |
| `tests/` | Testes (`unittest`, sem instalar nada) |

## Testes

```powershell
cd NextLevelConstructionPy
python -I -m unittest discover -s tests -t . -v
```

`tests/test_parity_java.py` roda o `CalcEngine` do Java e o `calc.py` nas mesmas ~45 mil entradas e compara QTY, comprimento
e ItemKey. Precisa do Java compilado em `../NextLevelConstruction/bin` (senão é pulado).

## Diferença conhecida em relação ao Java

Texto de comprimento inválido: o Java aceita `12d`, `5f`, `NaN` e `Infinity` como número (peculiaridade do
`Double.parseDouble`), o web lê só o começo do texto (`parseFloat`: `5f` vira 5) e o Excel (`VALUE`) rejeita todos.
O Python rejeita (sem comprimento), como o Excel. Em uso normal o comprimento vem da lista, então isso quase não aparece.
