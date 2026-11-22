"""Analyze Northwind discounts, sales reps and product bundling.

Usage: python analysis.py [xlsx_path] [output_dir]
Defaults: data/Northwind Database.xlsx and outputs/.
"""
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

XLSX = sys.argv[1] if len(sys.argv) > 1 else "data/Northwind Database.xlsx"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "outputs")
OUT.mkdir(exist_ok=True)

sheets = pd.read_excel(XLSX, sheet_name=None)
details = sheets["Orders Details"].copy()
orders = sheets["Orders"].copy()
employees = sheets["Employees"].copy()
products = sheets["Product"][["ProductID", "ProductName", "CategoryID"]]
categories = sheets["Categories"][["CategoryID", "CategoryName"]]

details["GrossRevenue"] = details.UnitPrice * details.Quantity
details["NetRevenue"] = details.GrossRevenue * (1 - details.Discount)
details["Discounted"] = details.Discount > 0
details = details.merge(products, on="ProductID").merge(categories, on="CategoryID")


# ---------- Q1: Do discounted orders sell more product? ----------
def q1_discounts():
    """Compare each product's discounted and full-price order lines.

    Only products sold both with and without a discount are kept, so
    every comparison pairs a product with itself. Also writes
    ``q1_per_product.csv`` and ``q1_by_level.csv`` to ``OUT``.

    Args:
        None.

    Returns:
        dict: Results keyed as follows.
            per_product (pandas.DataFrame): Lines, mean quantity and
                mean net revenue per line for full-price and discounted
                sales, plus their differences, one row per product.
            by_level (pandas.DataFrame): Paired comparison against
                full price for each discount level (5%-25%), with
                Wilcoxon p-values for quantity and net revenue.
            n_products (int): Products compared.
            excluded (numpy.ndarray): Names of products dropped for
                lacking discounted or full-price sales.
            n_lines (int): Order lines in the compared products.
            n_disc_lines (int): Discounted lines among ``n_lines``.
            qty_t_p (float): Paired t-test p-value, quantity.
            qty_w_p (float): Wilcoxon signed-rank p-value, quantity.
            rev_t_p (float): Paired t-test p-value, net revenue.
            rev_w_p (float): Wilcoxon signed-rank p-value, net revenue.
            discount_cost (float): Gross minus net revenue, in dollars.
            total_gross (float): Gross revenue before discounts.
    """
    # One-to-one comparison: keep only products sold both with and without a discount,
    # then compare each product's discounted lines against its own full-price lines.
    both = details.groupby("ProductID").Discounted.nunique().eq(2)
    m = details[details.ProductID.map(both)].copy()
    excluded = details.loc[~details.ProductID.map(both), "ProductName"].unique()

    per_product = (m.groupby(["ProductName", "Discounted"])
                   .agg(lines=("Quantity", "size"), mean_qty=("Quantity", "mean"),
                        mean_net_rev=("NetRevenue", "mean"))
                   .unstack("Discounted"))
    per_product.columns = [f"{stat}_{'disc' if d else 'full'}" for stat, d in per_product.columns]
    per_product["qty_diff"] = per_product.mean_qty_disc - per_product.mean_qty_full
    per_product["qty_ratio"] = per_product.mean_qty_disc / per_product.mean_qty_full
    per_product["rev_diff"] = per_product.mean_net_rev_disc - per_product.mean_net_rev_full
    per_product = per_product.sort_values("qty_diff", ascending=False)

    # Paired tests across products (each product is one pair: discounted vs full price).
    qty_t = stats.ttest_rel(per_product.mean_qty_disc, per_product.mean_qty_full)
    qty_w = stats.wilcoxon(per_product.mean_qty_disc, per_product.mean_qty_full)
    rev_t = stats.ttest_rel(per_product.mean_net_rev_disc, per_product.mean_net_rev_full)
    rev_w = stats.wilcoxon(per_product.mean_net_rev_disc, per_product.mean_net_rev_full)

    # Same paired comparison at each discount level, against that product's full-price mean.
    # Discounts are stored as floats (0.1 may read as 0.10000000149), so round before banding.
    m["Pct"] = (m.Discount * 100).round().astype(int)
    full = m[m.Pct == 0].groupby("ProductID").Quantity.mean()
    full_rev = m[m.Pct == 0].groupby("ProductID").NetRevenue.mean()
    level_rows = []
    for pct in (5, 10, 15, 20, 25):
        lvl = m[m.Pct == pct].groupby("ProductID").agg(q=("Quantity", "mean"),
                                                        r=("NetRevenue", "mean"),
                                                        n=("Quantity", "size"))
        level_rows.append(dict(
            discount=f"{pct}%", products=len(lvl), lines=lvl.n.sum(),
            mean_qty_full=full[lvl.index].mean(), mean_qty_disc=lvl.q.mean(),
            median_qty_lift=(lvl.q / full[lvl.index] - 1).median(),
            share_products_higher=(lvl.q > full[lvl.index]).mean(),
            mean_rev_diff=(lvl.r - full_rev[lvl.index]).mean(),
            qty_wilcoxon_p=stats.wilcoxon(lvl.q, full[lvl.index]).pvalue,
            rev_wilcoxon_p=stats.wilcoxon(lvl.r, full_rev[lvl.index]).pvalue,
        ))
    by_level = pd.DataFrame(level_rows).set_index("discount")

    discount_cost = (m.GrossRevenue - m.NetRevenue).sum()

    per_product.to_csv(OUT / "q1_per_product.csv")
    by_level.to_csv(OUT / "q1_by_level.csv")
    return dict(
        per_product=per_product, by_level=by_level, n_products=len(per_product),
        excluded=excluded, n_lines=len(m), n_disc_lines=int(m.Discounted.sum()),
        qty_t_p=qty_t.pvalue, qty_w_p=qty_w.pvalue, rev_t_p=rev_t.pvalue, rev_w_p=rev_w.pvalue,
        discount_cost=discount_cost, total_gross=m.GrossRevenue.sum(),
    )


# ---------- Q2: How does performance vary among sales reps? ----------
def q2_reps():
    """Summarize sales performance for each employee who took orders.

    Adds a ``Rep`` full-name column to the module-level ``employees``
    table and writes ``q2_reps.csv`` and ``q2_monthly_run_rate.csv``
    to ``OUT``.

    Args:
        None.

    Returns:
        dict: Results keyed as follows.
            reps (pandas.DataFrame): Orders, customers, net revenue,
                average order value, late-shipment rate, discount
                given, revenue share and revenue per customer per rep,
                and average units per order, each with the same average
                over all other reps' orders and a Welch t-test p-value
                comparing the two, sorted by net revenue.
            run_rate (pandas.DataFrame): Net revenue per month for
                each year, rows in the same order as ``reps``.
            months (pandas.Series): Months with orders in each year.
    """
    o = orders.merge(details.groupby("OrderID").agg(net=("NetRevenue", "sum"),
                                                    gross=("GrossRevenue", "sum"),
                                                    units=("Quantity", "sum")),
                     on="OrderID")
    o["Late"] = o.ShippedDate > o.RequiredDate
    o["Year"] = o.OrderDate.dt.year
    employees["Rep"] = employees.FirstName + " " + employees.LastName
    o = o.merge(employees[["EmployeeID", "Rep", "Title", "Country"]], on="EmployeeID")

    reps = o.groupby(["Rep", "Title", "Country"]).agg(
        orders=("OrderID", "size"), customers=("CustomerID", "nunique"),
        net_revenue=("net", "sum"), gross=("gross", "sum"),
        avg_order_value=("net", "mean"), late_rate=("Late", "mean"),
    ).reset_index()
    reps["discount_given_pct"] = 1 - reps.net_revenue / reps.gross
    reps["revenue_share"] = reps.net_revenue / reps.net_revenue.sum()
    reps["rev_per_customer"] = reps.net_revenue / reps.customers
    reps = reps.drop(columns="gross").sort_values("net_revenue", ascending=False)

    # Do each rep's orders differ from everyone else's in value ($) or in
    # units? Welch t-tests (unequal variances) of the rep's orders against
    # all other reps' orders.
    for col, prefix in (("net", "aov"), ("units", "units")):
        rest_mean, t_p = [], []
        for rep in reps.Rep:
            mine = o.loc[o.Rep == rep, col]
            rest = o.loc[o.Rep != rep, col]
            rest_mean.append(rest.mean())
            t_p.append(stats.ttest_ind(mine, rest, equal_var=False).pvalue)
        if prefix == "units":
            reps["avg_units"] = reps.Rep.map(o.groupby("Rep").units.mean())
        reps[f"{prefix}_others"] = rest_mean
        reps[f"{prefix}_t_p"] = t_p

    # 1996 covers Jul-Dec and 1998 covers Jan-May, so compare monthly run-rates.
    months = o.groupby("Year").OrderDate.apply(lambda s: s.dt.to_period("M").nunique())
    yearly = o.pivot_table(index="Rep", columns="Year", values="net", aggfunc="sum").fillna(0)
    run_rate = yearly.div(months, axis=1)
    run_rate.columns = [f"monthly_{c}" for c in run_rate.columns]

    reps.to_csv(OUT / "q2_reps.csv", index=False)
    run_rate.to_csv(OUT / "q2_monthly_run_rate.csv")
    return dict(reps=reps, run_rate=run_rate.loc[reps.Rep], months=months)


# ---------- Q3: Which products are bought together? ----------
def q3_bundles(min_orders=5):
    """Find product pairs and categories bought in the same order.

    Writes ``q3_pairs.csv`` and ``q3_category_lift.csv`` to ``OUT``.

    Args:
        min_orders (int): Fewest shared orders for a pair to be scored.

    Returns:
        dict: Results keyed as follows.
            pairs (pandas.DataFrame): Pairs with at least
                ``min_orders`` shared orders, with support, confidence
                each way, lift and chi-square test p-value, sorted
                by lift.
            n_orders (int): Orders analyzed.
            multi_share (float): Share of orders with 2+ products.
            basket_size (pandas.Series): Summary statistics of
                distinct products per order.
            cat_lift (pandas.DataFrame): Symmetric category-by-category
                lift; the diagonal is NaN.
            n_pairs_total (int): Distinct pairs seen at least once.
    """
    baskets = details.groupby("OrderID").ProductName.apply(lambda s: sorted(set(s)))
    n = len(baskets)
    item_cnt = details.groupby("ProductName").OrderID.nunique()
    pair_cnt = {}
    for items in baskets:
        for a, b in combinations(items, 2):
            pair_cnt[(a, b)] = pair_cnt.get((a, b), 0) + 1

    rows = []
    for (a, b), c in pair_cnt.items():
        if c < min_orders:
            continue
        sa, sb = item_cnt[a] / n, item_cnt[b] / n
        # Chi-square test: does the pair co-occur more or less often than chance?
        table = [[c, item_cnt[a] - c], [item_cnt[b] - c, n - item_cnt[a] - item_cnt[b] + c]]
        p = stats.chi2_contingency(table)[1]
        rows.append(dict(product_a=a, product_b=b, orders_together=c, support=c / n,
                         conf_a_to_b=c / item_cnt[a], conf_b_to_a=c / item_cnt[b],
                         lift=(c / n) / (sa * sb), chisq_p=p))
    pairs = pd.DataFrame(rows).sort_values(["lift", "orders_together"], ascending=False)

    multi = (baskets.str.len() > 1).mean()
    basket_size = baskets.str.len().describe()

    # Category-level lift: which categories co-occur more than chance?
    cat_baskets = details.groupby("OrderID").CategoryName.apply(lambda s: set(s))
    cat_cnt = pd.Series([c for s in cat_baskets for c in s]).value_counts()
    cats = sorted(cat_cnt.index)
    cat_lift = pd.DataFrame(np.nan, index=cats, columns=cats)
    for a, b in combinations(cats, 2):
        c = sum(1 for s in cat_baskets if a in s and b in s)
        cat_lift.loc[a, b] = cat_lift.loc[b, a] = (c / n) / ((cat_cnt[a] / n) * (cat_cnt[b] / n))

    pairs.to_csv(OUT / "q3_pairs.csv", index=False)
    cat_lift.round(3).to_csv(OUT / "q3_category_lift.csv")
    return dict(pairs=pairs, n_orders=n, multi_share=multi, basket_size=basket_size,
                cat_lift=cat_lift, n_pairs_total=len(pair_cnt))


if __name__ == "__main__":
    pd.set_option("display.width", 200, "display.max_columns", 20)
    r1 = q1_discounts()
    print("=== Q1 DISCOUNTS (products sold both ways only) ===")
    pp = r1["per_product"]
    print(f"{r1['n_products']} products, {r1['n_lines']} lines ({r1['n_disc_lines']} discounted); "
          f"excluded: {list(r1['excluded'])}")
    print(f"Avg of per-product mean qty: full {pp.mean_qty_full.mean():.1f} vs disc "
          f"{pp.mean_qty_disc.mean():.1f}; median ratio {pp.qty_ratio.median():.2f}; "
          f"{(pp.qty_diff > 0).sum()}/{len(pp)} products sell more when discounted")
    print(f"Qty paired t p={r1['qty_t_p']:.2g}, Wilcoxon p={r1['qty_w_p']:.2g}")
    print(f"Net rev/line: full ${pp.mean_net_rev_full.mean():.0f} vs disc ${pp.mean_net_rev_disc.mean():.0f}; "
          f"{(pp.rev_diff > 0).sum()}/{len(pp)} higher; paired t p={r1['rev_t_p']:.2g}, "
          f"Wilcoxon p={r1['rev_w_p']:.2g}")
    print(r1["by_level"].round(3).to_string())
    print(pp[["lines_full", "lines_disc", "mean_qty_full", "mean_qty_disc", "qty_ratio"]]
          .round(2).iloc[np.r_[0:5, -5:0]].to_string())
    print(f"Discount cost: ${r1['discount_cost']:,.0f} ({r1['discount_cost'] / r1['total_gross']:.1%} of gross)")

    r2 = q2_reps()
    print("\n=== Q2 REPS ===")
    print(r2["reps"].round(3).to_string(index=False))
    print(r2["run_rate"].round(0))
    print("months per year:", r2["months"].to_dict())

    r3 = q3_bundles()
    print("\n=== Q3 BUNDLES ===")
    print(f"{r3['n_orders']} orders, {r3['multi_share']:.0%} multi-product, "
          f"{r3['n_pairs_total']} distinct pairs")
    print(r3["basket_size"].round(2).to_dict())
    print(r3["pairs"].head(15).round(3).to_string(index=False))
    print("\nMost frequent pairs:")
    print(r3["pairs"].sort_values("orders_together", ascending=False).head(8)
          .round(3).to_string(index=False))
    print(r3["cat_lift"].round(2))
