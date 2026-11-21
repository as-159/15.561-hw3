# Northwind Sales Insights (15.561 HW 3)

Analysis of the Northwind Traders order data (July 1996 – May 1998) answering three business questions:

1. **Do discounted orders actually sell more product?** Each product's discounted order lines are compared one-to-one with its own full-price lines (all 77 products were sold both ways), using paired t-tests and Wilcoxon signed-rank tests, overall and by discount level.
2. **How does performance vary among the sales representatives?** Net revenue, orders, customers, average order value, discount rate and late-shipment rate per employee, plus monthly revenue run-rate by year.
3. **Which products tend to be bundled or bought together?** Market-basket analysis (support, confidence, lift) on product pairs seen together in at least 5 orders, with one-sided Fisher exact tests and a Bonferroni correction, plus category-level lift.

**Webpage:** https://as-159.github.io/15.561-hw3/

## Repository layout

| Path | Contents |
|---|---|
| `data/Northwind Database.xlsx` | The provided Northwind dataset (input) |
| `analysis.py` | All calculations for the three questions; prints results and writes CSV tables to `outputs/` |
| `build_site.py` | Runs the analysis and builds the four-page website with interactive Plotly charts into `docs/` |
| `outputs/` | CSV tables behind every number and chart |
| `docs/index.html` | Overview page: short answer, key numbers and implication for each question |
| `docs/discounts.html`, `docs/sales-reps.html`, `docs/bundles.html` | One page per question with the full approach, charts, tables and findings |
| `requirements.txt` | Python dependencies |

## How to reproduce

Requires Python 3.9+.

```bash
pip install -r requirements.txt
python analysis.py        # prints all results and writes outputs/*.csv
python build_site.py      # rebuilds every page in docs/
```

Both scripts read `data/Northwind Database.xlsx` by default; pass a different path as the first argument to use another copy, e.g. `python analysis.py path/to/Northwind.xlsx`.

Every number, chart and table on the webpage is computed by `build_site.py` from the dataset at build time, so rerunning it reproduces the page exactly. Open `docs/index.html` in a browser to view it locally; the tab bar links the pages (the charts load Plotly from its CDN, so an internet connection is needed).

## Definitions

- **Net revenue** = unit price × quantity × (1 − discount), per order line.
- **Late shipment** = shipped after the order's required date.
- **Lift** = P(A and B in the same order) ÷ (P(A) × P(B)); 1.0 means the pair is bought together exactly as often as chance.
- Monthly run-rates are used for year comparisons because the data covers only 6 months of 1996 and 5 months of 1998.
