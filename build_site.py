"""Build the findings website in docs/: an overview and 3 tabs.

Usage: python build_site.py [xlsx_path]
Every number on the page is computed by analysis.py at build time.
"""
from html import escape
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import plotly.offline

import analysis as A

DOCS = Path("docs")
DOCS.mkdir(exist_ok=True)

# Palette and chrome from the reference data-viz palette (light mode).
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
SEQ = ["#86b6ef", "#2a78d6", "#104281"]  # ordinal blue steps 250 / 450 / 650
DIV_NEG, DIV_MID, DIV_POS = "#e34948", "#f0efec", "#2a78d6"
MUTED_BAR = "#c3c2b7"
INK, INK2, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'


def style(fig, height=420, **layout):
    """Apply the page's shared chart styling to a figure.

    Args:
        fig (plotly.graph_objects.Figure): Figure to style; modified in
            place.
        height (int): Chart height in pixels.
        **layout: Extra Plotly layout settings; override the defaults,
            including ``bargap``.

    Returns:
        plotly.graph_objects.Figure: The same ``fig``, for chaining.
    """
    fig.update_layout(
        height=height, font=dict(family=FONT, size=13, color=INK2),
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE, margin=dict(l=10, r=20, t=10, b=10),
        hoverlabel=dict(bgcolor="white", bordercolor=GRID, font=dict(family=FONT, color=INK)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title_text=""),
        **{"bargap": 0.35, **layout})
    fig.update_xaxes(gridcolor=GRID, linecolor=AXIS, zerolinecolor=AXIS, tickfont_color=MUTED,
                     title_font_color=INK2, automargin=True)
    fig.update_yaxes(gridcolor=GRID, linecolor=AXIS, zerolinecolor=AXIS, tickfont_color=MUTED,
                     title_font_color=INK2, automargin=True)
    return fig


def html(fig):
    """Render a figure as an embeddable HTML fragment.

    Args:
        fig (plotly.graph_objects.Figure): Figure to render.

    Returns:
        str: ``<div>`` and script markup; Plotly.js itself is not
        included and must be loaded by the page.
    """
    return fig.to_html(full_html=False, include_plotlyjs=False,
                       config=dict(displaylogo=False, responsive=True,
                                   modeBarButtonsToRemove=["select2d", "lasso2d"]))


def table(df, fmt):
    """Render a DataFrame as an HTML-escaped table.

    Args:
        df (pandas.DataFrame): Rows and columns to show; the index is
            ignored.
        fmt (dict[str, Callable[[Any], str]]): Formatter per column
            name; columns not listed use ``str``.

    Returns:
        str: Table markup wrapped in a scrollable ``table-wrap`` div.
    """
    head = "".join(f"<th>{escape(str(c))}</th>" for c in df.columns)
    rows = "".join("<tr>" + "".join(
        f"<td>{escape(fmt.get(c, str)(v))}</td>" for c, v in r.items()) + "</tr>"
        for _, r in df.iterrows())
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'


money = lambda v: f"${v:,.0f}"
pct = lambda v: f"{v:.1%}"
pct0 = lambda v: f"{v:.0%}"
num1 = lambda v: f"{v:.1f}"
pval = lambda v: "<0.001" if v < 0.001 else f"{v:.3f}"
ptxt = lambda v: "p < 0.001" if v < 0.001 else f"p = {v:.3f}"

# ---------------- Q1 ----------------
r1 = A.q1_discounts()
pp = r1["per_product"].reset_index()
lim = max(pp.mean_qty_full.max(), pp.mean_qty_disc.max()) * 1.05

q1_scatter = go.Figure()
q1_scatter.add_trace(go.Scatter(x=[0, lim], y=[0, lim], mode="lines", hoverinfo="skip",
                                line=dict(color=AXIS, width=2, dash="dash"), showlegend=False))
q1_scatter.add_trace(go.Scatter(
    x=pp.mean_qty_full, y=pp.mean_qty_disc, mode="markers", showlegend=False,
    marker=dict(size=10, color=BLUE, opacity=0.8, line=dict(color=SURFACE, width=2)),
    customdata=np.c_[pp.ProductName, pp.lines_full, pp.lines_disc, pp.qty_ratio],
    hovertemplate="<b>%{customdata[0]}</b><br>Full price: %{x:.1f} units/line (%{customdata[1]} lines)"
                  "<br>Discounted: %{y:.1f} units/line (%{customdata[2]} lines)"
                  "<br>Ratio: %{customdata[3]:.2f}×<extra></extra>"))
q1_scatter.add_annotation(x=lim * 0.02, y=lim * 0.98, text="Above the line: sells more when discounted",
                          showarrow=False, font=dict(color=INK2, size=12), xanchor="left")
q1_scatter.add_annotation(x=lim * 0.98, y=lim * 0.04, text="Below the line: sells less when discounted",
                          showarrow=False, font=dict(color=INK2, size=12), xanchor="right")
style(q1_scatter, height=460,
      xaxis=dict(title="Average units per order line at full price", range=[0, lim]),
      yaxis=dict(title="Average units per order line when discounted", range=[0, lim]))

lvl = r1["by_level"].reset_index()
q1_levels = go.Figure(go.Bar(
    x=lvl.discount, y=lvl.median_qty_lift, marker=dict(color=BLUE, cornerradius=4),
    text=[f"{v:+.0%}" for v in lvl.median_qty_lift], textposition="outside",
    textfont=dict(color=INK2), cliponaxis=False,
    customdata=np.c_[lvl.products, lvl.share_products_higher, lvl.qty_wilcoxon_p,
                     lvl.mean_rev_diff, lvl.rev_wilcoxon_p],
    hovertemplate="<b>%{x} discount</b><br>Median quantity lift: %{y:+.1%}"
                  "<br>Products compared: %{customdata[0]}<br>Share selling more: %{customdata[1]:.0%}"
                  "<br>Quantity p (Wilcoxon) = %{customdata[2]:.3f}"
                  "<br>Avg net revenue change/line: $%{customdata[3]:+.0f}"
                  "<br>Net revenue p (Wilcoxon) = %{customdata[4]:.3f}<extra></extra>"))
style(q1_levels, height=340,
      xaxis=dict(title="Discount level"),
      yaxis=dict(title="Median quantity lift", tickformat="+.0%",
                 range=[min(0, lvl.median_qty_lift.min()) - 0.03, lvl.median_qty_lift.max() + 0.05]))

q1_level_table = table(
    lvl.rename(columns=dict(discount="Discount", products="Products", lines="Discounted lines",
                            median_qty_lift="Median qty lift", share_products_higher="Products selling more",
                            qty_wilcoxon_p="p, quantity (Wilcoxon)",
                            mean_rev_diff="Avg net revenue change / line",
                            rev_wilcoxon_p="p, net revenue (Wilcoxon)"))
    [["Discount", "Products", "Discounted lines", "Median qty lift", "Products selling more",
      "p, quantity (Wilcoxon)", "Avg net revenue change / line", "p, net revenue (Wilcoxon)"]],
    {"Median qty lift": lambda v: f"{v:+.1%}", "Products selling more": pct0,
     "p, quantity (Wilcoxon)": pval,
     "Avg net revenue change / line": lambda v: f"{'+' if v >= 0 else '−'}${abs(v):,.0f}",
     "p, net revenue (Wilcoxon)": pval})

n_more = int((pp.qty_diff > 0).sum())
n_rev_more = int((pp.rev_diff > 0).sum())

# ---------------- Q2 ----------------
r2 = A.q2_reps()
reps = r2["reps"].reset_index(drop=True)
reps["Short"] = reps.Rep + reps.Title.map(lambda t: "" if t == "Sales Representative" else f" ({t})")
order = reps.sort_values("net_revenue").Short

# Nudge labels that would otherwise collide with a neighbouring rep.
LABEL_POS = {"Robert King": "middle left", "Nancy Davolio": "bottom center"}
q2_scatter = go.Figure()
for country, color in (("USA", BLUE), ("UK", ORANGE)):
    d = reps[reps.Country == country]
    q2_scatter.add_trace(go.Scatter(
        x=d.orders, y=d.avg_order_value, mode="markers+text", name=f"{country} office",
        text=d.Rep, textposition=[LABEL_POS.get(r, "top center") for r in d.Rep],
        textfont=dict(color=INK2, size=12),
        marker=dict(size=d.net_revenue / 9000, color=color, line=dict(color=SURFACE, width=2)),
        customdata=np.c_[d.Title, d.net_revenue, d.customers, d.aov_others, d.aov_t_p],
        hovertemplate="<b>%{text}</b> · %{customdata[0]}<br>Orders: %{x}<br>Avg order value: $%{y:,.0f}"
                      "<br>Other reps' avg order: $%{customdata[3]:,.0f} (t-test p = %{customdata[4]:.3f})"
                      "<br>Net revenue: $%{customdata[1]:,.0f}<br>Customers: %{customdata[2]}<extra></extra>"))
style(q2_scatter, height=460,
      xaxis=dict(title="Number of orders (Jul 1996 – May 1998)", range=[0, 195]),
      yaxis=dict(title="Average net value per order ($)", tickprefix="$", range=[900, 2000]))

rr = r2["run_rate"].reindex(reps.Rep)
q2_growth = go.Figure()
# Horizontal groups stack the first trace at the bottom, so add years newest-first.
for col, color in list(zip(rr.columns, SEQ))[::-1]:
    year = col.split("_")[1]
    q2_growth.add_trace(go.Bar(
        y=reps.Short, x=rr[col].values, orientation="h", name=year,
        marker=dict(color=color, cornerradius=4),
        hovertemplate="<b>%{y}</b><br>" + year + ": $%{x:,.0f} per month<extra></extra>"))
style(q2_growth, height=560, barmode="group", bargap=0.25, bargroupgap=0.08,
      yaxis=dict(categoryorder="array", categoryarray=list(order), title=""),
      xaxis=dict(title="Net revenue per month ($)", tickprefix="$"))
q2_growth.update_layout(legend_traceorder="reversed")

q2_table = table(
    reps[["Rep", "Title", "Country", "orders", "orders_others", "customers", "net_revenue",
          "revenue_share", "avg_order_value", "aov_others", "aov_t_p", "discount_given_pct",
          "late_rate"]]
    .rename(columns=dict(orders="Total orders", orders_others="Other reps' avg total orders",
                         customers="Customers", net_revenue="Net revenue",
                         revenue_share="Share", avg_order_value="Avg order",
                         aov_others="Other reps' avg order", aov_t_p="p, order value (t-test)",
                         discount_given_pct="Discount given", late_rate="Late shipments")),
    {"Net revenue": money, "Share": pct, "Avg order": money, "Other reps' avg order": money,
     "p, order value (t-test)": pval, "Discount given": pct, "Late shipments": pct,
     "Total orders": str, "Other reps' avg total orders": lambda v: f"{v:.1f}",
     "Customers": str})

top3 = reps.head(3)
uk = reps[reps.Country == "UK"]
# Reps whose average order value differs significantly from all other reps' orders.
aov_sig = reps[reps.aov_t_p < 0.05].sort_values("avg_order_value")
aov_sig_names = " and ".join(aov_sig.Rep)
aov_sig_detail = "; ".join(
    f"{r.Rep} {money(r.avg_order_value)} vs. {money(r.aov_others)}, {ptxt(r.aov_t_p)}"
    for r in aov_sig.itertuples())

# ---------------- Q3 ----------------
r3 = A.q3_bundles()
pairs = r3["pairs"].head(12).iloc[::-1].copy()
pairs["Pair"] = pairs.product_a + " + " + pairs.product_b
q3_pairs = go.Figure(go.Bar(
    y=pairs.Pair, x=pairs.lift, orientation="h",
    marker=dict(color=[BLUE if l == pairs.lift.max() else MUTED_BAR for l in pairs.lift], cornerradius=4),
    text=[f"{l:.1f}×" for l in pairs.lift],
    textposition="outside", textfont=dict(color=INK2, size=12), cliponaxis=False,
    customdata=np.c_[pairs.orders_together, pairs.conf_a_to_b, pairs.conf_b_to_a, pairs.chisq_p,
                     pairs.product_a, pairs.product_b],
    hovertemplate="<b>%{y}</b><br>Lift: %{x:.2f}× chance<br>Orders together: %{customdata[0]}"
                  "<br>%{customdata[1]:.0%} of %{customdata[4]} orders include %{customdata[5]}"
                  "<br>%{customdata[2]:.0%} of %{customdata[5]} orders include %{customdata[4]}"
                  "<br>Chi-square p = %{customdata[3]:.4f}<extra></extra>"))
q3_pairs.add_vline(x=1, line=dict(color=AXIS, width=2, dash="dash"))
style(q3_pairs, height=520, xaxis=dict(title="Lift (× chance)",
                                        range=[0, pairs.lift.max() * 1.15]),
      yaxis=dict(title=""))

cl = r3["cat_lift"]
z = cl.values
q3_heat = go.Figure(go.Heatmap(
    z=z, x=cl.columns, y=cl.index, zmid=1, zmin=0.6, zmax=1.4,
    colorscale=[[0, DIV_NEG], [0.5, DIV_MID], [1, DIV_POS]], xgap=2, ygap=2,
    text=np.where(np.isnan(z), "", np.vectorize(lambda v: f"{v:.2f}")(np.nan_to_num(z))),
    texttemplate="%{text}", textfont=dict(size=12, color=INK),
    colorbar=dict(title=dict(text="Lift", side="right"), tickvals=[0.6, 0.8, 1, 1.2, 1.4],
                  ticktext=["0.6", "0.8", "1.0 (chance)", "1.2", "1.4"], thickness=12),
    hovertemplate="%{y} + %{x}<br>Lift: %{z:.2f}<extra></extra>"))
style(q3_heat, height=480, xaxis=dict(showgrid=False, tickangle=-30),
      yaxis=dict(showgrid=False, autorange="reversed"))

top = r3["pairs"].iloc[0]
pairs_table = table(
    r3["pairs"].head(12)[["product_a", "product_b", "orders_together", "lift", "conf_b_to_a", "chisq_p"]]
    .rename(columns=dict(product_a="Product A", product_b="Product B", orders_together="Orders together",
                         lift="Lift", conf_b_to_a="% of B orders with A", chisq_p="Chi-square p")),
    {"Lift": lambda v: f"{v:.2f}×", "% of B orders with A": pct0, "Chi-square p": pval,
     "Orders together": str})

# ---------------- Pages ----------------
PLOTLY_JS = f"https://cdn.plot.ly/plotly-{plotly.offline.get_plotlyjs_version()}.min.js"
TABS = [("index.html", "Overview"), ("discounts.html", "1 · Discounts"),
        ("sales-reps.html", "2 · Sales reps"), ("bundles.html", "3 · Bundles")]
CSS = f"""<style>
  :root {{ color-scheme: light; --page: #f9f9f7; --surface: {SURFACE}; --ink: {INK}; --ink2: {INK2};
          --muted: {MUTED}; --grid: {GRID}; --accent: {BLUE}; --border: rgba(11,11,11,0.10); }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--page); color: var(--ink); font-family: {FONT};
          line-height: 1.6; font-size: 16px; }}
  main {{ max-width: 920px; margin: 0 auto; padding: 48px 16px 80px; }}
  header p.lede {{ font-size: 1.15rem; color: var(--ink2); max-width: 70ch; }}
  h1 {{ font-size: 2.1rem; line-height: 1.2; margin: 0 0 12px; letter-spacing: -0.01em; }}
  h2 {{ font-size: 1.5rem; line-height: 1.3; margin: 0 0 4px; }}
  h3 {{ font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted);
        margin: 28px 0 6px; }}
  .meta {{ color: var(--muted); font-size: 0.9rem; }}
  nav ol {{ padding-left: 20px; }} nav a {{ color: var(--accent); }}
  section.q {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
               padding: 28px 28px 20px; margin: 32px 0; }}
  .qnum {{ color: var(--accent); font-weight: 600; font-size: 0.9rem; }}
  .finding {{ border-left: 3px solid var(--accent); padding: 4px 0 4px 16px; margin: 20px 0;
              font-size: 1.05rem; }}
  .implication {{ background: #f0efec; border-radius: 8px; padding: 14px 18px; }}
  .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px;
            margin: 16px 0; }}
  .stat {{ border: 1px solid var(--border); border-radius: 8px; padding: 12px 14px; }}
  .stat b {{ display: block; font-size: 1.6rem; font-weight: 600; line-height: 1.2; }}
  .stat span {{ color: var(--ink2); font-size: 0.85rem; }}
  .chart-title {{ font-weight: 600; margin: 24px 0 2px; }}
  .chart-sub {{ color: var(--ink2); font-size: 0.9rem; margin: 0 0 8px; }}
  details {{ margin: 8px 0 16px; }} summary {{ cursor: pointer; color: var(--accent); font-size: 0.9rem; }}
  .table-wrap {{ overflow-x: auto; }}
  table {{ border-collapse: collapse; font-size: 0.85rem; width: 100%; font-variant-numeric: tabular-nums; }}
  th, td {{ text-align: left; padding: 6px 10px; border-bottom: 1px solid var(--grid); white-space: nowrap; }}
  th {{ color: var(--ink2); font-weight: 600; }}
  .caveat {{ color: var(--ink2); font-size: 0.9rem; }}
  footer {{ color: var(--muted); font-size: 0.85rem; margin-top: 40px; }}
  @media (max-width: 600px) {{ section.q {{ padding: 20px 16px; }} h1 {{ font-size: 1.7rem; }} }}
  .tabs {{ position: sticky; top: 0; z-index: 10; background: var(--page);
           border-bottom: 1px solid var(--grid); }}
  .tabs ul {{ max-width: 920px; margin: 0 auto; padding: 0 16px; list-style: none; display: flex;
              gap: 4px; overflow-x: auto; }}
  .tabs a {{ display: block; padding: 14px 14px 12px; color: var(--ink2); text-decoration: none;
             white-space: nowrap; border-bottom: 3px solid transparent; font-size: 0.95rem; }}
  .tabs a:hover {{ color: var(--ink); }}
  .tabs a[aria-current="page"] {{ color: var(--ink); border-bottom-color: var(--accent); font-weight: 600; }}
  .cards {{ display: grid; gap: 20px; margin-top: 32px; }}
  .card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
           padding: 24px 28px; }}
  .card h2 {{ font-size: 1.3rem; }}
  .card .answer {{ font-size: 1.05rem; margin: 10px 0 4px; }}
  .card .more {{ display: inline-block; margin-top: 8px; color: var(--accent); font-weight: 600;
                 text-decoration: none; }}
  .card .more:hover {{ text-decoration: underline; }}
  .pager {{ display: flex; justify-content: space-between; gap: 16px; margin-top: 24px; }}
  .pager a {{ color: var(--accent); text-decoration: none; font-weight: 600; }}
  .pager a:hover {{ text-decoration: underline; }}
  @media (max-width: 600px) {{ .card {{ padding: 20px 16px; }} }}
</style>"""
FOOTER = f"""<footer>
  All figures are produced by <code>analysis.py</code> and <code>build_site.py</code> from the Northwind
  dataset; see the GitHub repository README to reproduce them. Revenue = unit price × quantity × (1 − discount).
</footer>"""


def render_page(filename, title, body):
    """Write one page of the site with the shared head, tabs and footer.

    Args:
        filename (str): Output file name inside ``DOCS``; also marks
            which tab is shown as current.
        title (str): Page title shown in the browser tab.
        body (str): HTML placed between the tab bar and the footer.

    Returns:
        None. Writes ``DOCS / filename``.
    """
    current = ' aria-current="page"'
    tabs = "".join(
        f'<li><a href="{f}"{current if f == filename else ""}>{label}</a></li>'
        for f, label in TABS)
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<script src="{PLOTLY_JS}"></script>
{CSS}
</head>
<body>
<nav class="tabs" aria-label="Sections"><ul>{tabs}</ul></nav>
<main>
{body}
{FOOTER}
</main>
</body>
</html>
"""
    (DOCS / filename).write_text(page, encoding="utf-8")
    print(f"Wrote {DOCS / filename}")


def pager(prev, nxt):
    """Build previous/next links shown at the bottom of a question page.

    Args:
        prev (tuple[str, str] | None): ``(file, label)`` of the page
            before, or None for no link.
        nxt (tuple[str, str] | None): ``(file, label)`` of the page
            after, or None for no link.

    Returns:
        str: A ``pager`` div with up to two links.
    """
    left = f'<a href="{prev[0]}">← {prev[1]}</a>' if prev else "<span></span>"
    right = f'<a href="{nxt[0]}">{nxt[1]} →</a>' if nxt else "<span></span>"
    return f'<div class="pager">{left}{right}</div>'


overview = f"""
<header>
  <p class="meta">15.561 · HW 3 · Northwind Traders order data, July 1996 – May 1998</p>
  <h1>Discounts, sales reps, and product bundles at Northwind</h1>
  <p class="lede">Three questions a sales manager should be able to answer from Northwind's
  {len(A.orders)} orders and {len(A.details):,} order lines: whether discounts earn their cost,
  where sales performance really differs, and which products customers buy together. Each card
  below gives the short answer; open a tab for the full analysis, charts and data.</p>
</header>

<div class="cards">
  <article class="card">
    <div class="qnum">Question 1</div>
    <h2>Do discounted orders actually sell more product?</h2>
    <p class="answer"><b>Yes, but it doesn't pay off in revenue.</b> Compared with itself at full price,
    the typical product sells {pp.qty_ratio.median() - 1:.0%} more units per order line when discounted,
    yet net revenue per line shows no significant gain. Lift levels off above 15%, and the 10% tier
    shows none.</p>
    <div class="stats">
      <div class="stat"><b>{pp.qty_ratio.median() - 1:+.0%}</b><span>median quantity lift when discounted</span></div>
      <div class="stat"><b>{n_more} / {len(pp)}</b><span>products sell more units when discounted</span></div>
      <div class="stat"><b>{money(r1['discount_cost'])}</b><span>given up to discounts ({pct(r1['discount_cost'] / r1['total_gross'])} of gross)</span></div>
    </div>
    <p><b>Implication:</b> use discounts to move units, not to grow revenue; cap routine discounts at 15%.</p>
    <a class="more" href="discounts.html">See the discount analysis →</a>
  </article>

  <article class="card">
    <div class="qnum">Question 2</div>
    <h2>How does performance vary among the sales representatives?</h2>
    <p class="answer"><b>Top reps win on volume, not deal size.</b> {top3.Rep.iloc[0]} leads with
    {money(top3.net_revenue.iloc[0])}. Revenue gaps come from how many orders and customers each rep
    handles. Most reps' average order values match the rest of the team; only {aov_sig_names}
    write significantly smaller orders. Most reps grew sharply by 1998, but two stayed flat.</p>
    <div class="stats">
      <div class="stat"><b>{top3.revenue_share.sum():.0%}</b><span>of revenue from the top three reps</span></div>
      <div class="stat"><b>{uk.revenue_share.sum():.0%}</b><span>of revenue from the four-person UK office</span></div>
      <div class="stat"><b>{len(aov_sig)} / {len(reps)}</b><span>reps whose order value differs significantly from the rest (both lower)</span></div>
    </div>
    <p><b>Implication:</b> coach for customer coverage and order frequency rather than upselling.</p>
    <a class="more" href="sales-reps.html">See the sales rep analysis →</a>
  </article>

  <article class="card">
    <div class="qnum">Question 3</div>
    <h2>Which products tend to be bundled or bought together?</h2>
    <p class="answer"><b>One standout pair: scones and maple syrup.</b> Sir Rodney's Scones and Sirop
    d'érable appear together {top.lift:.1f}× more often than chance, well ahead of any other pair.
    Orders are small and focused, and categories mix slightly less than chance.</p>
    <div class="stats">
      <div class="stat"><b>{top.lift:.1f}×</b><span>scones + maple syrup vs. chance</span></div>
      <div class="stat"><b>{top.conf_b_to_a:.0%}</b><span>of maple-syrup orders also include the scones</span></div>
      <div class="stat"><b>{r3['basket_size']['50%']:.0f}</b><span>products in the median order</span></div>
    </div>
    <p><b>Implication:</b> launch a scones-and-syrup bundle; test the weaker cheese/dessert pairs first.</p>
    <a class="more" href="bundles.html">See the bundling analysis →</a>
  </article>
</div>
"""

render_page("index.html", "Northwind Sales Insights", overview)
render_page("discounts.html", "Discounts · Northwind Sales Insights",
            f"""<section class="q" id="q1">
  <div class="qnum">Question 1</div>
  <h2>Do discounted orders actually sell more product?</h2>
  <h3>Why it matters</h3>
  <p>Discounts cost Northwind {money(r1['discount_cost'])} — {pct(r1['discount_cost'] / r1['total_gross'])}
  of gross sales. If discounts don't move more product, that is margin given away for nothing.</p>
  <h3>Approach</h3>
  <p>Each product is compared with itself: its average units per order line when
  discounted versus when sold at full price. All {r1['n_products']} products were sold both ways,
  giving {r1['n_products']} paired comparisons ({r1['n_disc_lines']} discounted lines out of
  {r1['n_lines']:,}). Differences are tested with a paired t-test and a Wilcoxon signed-rank test,
  then repeated at each discount level.</p>

  <div class="stats">
    <div class="stat"><b>{pp.qty_ratio.median() - 1:+.0%}</b><span>median quantity lift when the same product is discounted</span></div>
    <div class="stat"><b>{n_more} / {len(pp)}</b><span>products sell more units when discounted</span></div>
    <div class="stat"><b>{n_rev_more} / {len(pp)}</b><span>products earn more net revenue per line when discounted</span></div>
  </div>

  <p class="chart-title">Most products sell more units per order when discounted</p>
  <p class="chart-sub">Each dot is one product. Dashed line = no difference. Hover for details.</p>
  {html(q1_scatter)}

  <p class="chart-title">Deeper discounts don't buy proportionally more volume</p>
  <p class="chart-sub">Median change in units per line vs. the same product at full price, by discount level.</p>
  {html(q1_levels)}
  <details><summary>Show table</summary>{q1_level_table}</details>

  <h3>Main finding</h3>
  <p class="finding">Yes — discounted lines sell more product. The typical product moves
  {pp.qty_ratio.median() - 1:.0%} more units per order line when discounted (paired t-test
  {ptxt(r1['qty_t_p'])}, Wilcoxon {ptxt(r1['qty_w_p'])}). But the extra volume only roughly
  offsets the lower price: net revenue per line is {money(pp.mean_net_rev_disc.mean())} discounted vs.
  {money(pp.mean_net_rev_full.mean())} at full price, a difference that is not statistically significant
  ({ptxt(r1['rev_t_p'])}). The lift also plateaus: 15%, 20% and 25% discounts all produce a similar
  13–18% increase, while the 10% tier shows no lift at all.</p>
  <h3>Business implication</h3>
  <p class="implication">Treat discounts as a tool for moving units (e.g. clearing stock), not for growing
  revenue. Since 20-25% discounts move no more volume than 15%, given the plateaued quantity uplift,
  cap routine discounts at 15%. Review how the 10% tier is used — it gives up price with no measurable volume gain.</p>
  <p class="caveat">Caveat: quantity uplift could be association, not causation — reps may grant discounts <em>because</em>
  a customer is already placing a large order. Some products have only one or two lines on one side,
  so individual dots are noisy; the conclusion rests on the paired test across all products.</p>
</section>""" + pager(None, TABS[2]))
render_page("sales-reps.html", "Sales reps · Northwind Sales Insights",
            f"""<section class="q" id="q2">
  <div class="qnum">Question 2</div>
  <h2>How does performance vary among the sales representatives?</h2>
  <h3>Why it matters</h3>
  <p>Knowing whether top performers win through more deals or bigger deals tells a manager what to coach,
  where to add headcount, and which reps need attention.</p>
  <h3>Approach</h3>
  <p>For each of the 9 employees who took orders: net revenue (after discounts), orders, distinct customers,
  average order value, discount rate given, and the share of orders shipped after the required date.
  A t-test (Welch's, which allows unequal spreads) compares each rep's average order value with the
  average of all other reps' orders. Growth is compared as monthly
  revenue because the data covers only {r2['months'][1996]} months of 1996 and {r2['months'][1998]} of 1998.</p>

  <div class="stats">
    <div class="stat"><b>{top3.revenue_share.sum():.0%}</b><span>of revenue from the top three reps ({', '.join(top3.Rep.str.split().str[0])})</span></div>
    <div class="stat"><b>{uk.revenue_share.sum():.0%}</b><span>of revenue from the four-person UK office</span></div>
    <div class="stat"><b>{len(aov_sig)} / {len(reps)}</b><span>reps whose average order value differs significantly from the rest — {aov_sig_names}, both lower</span></div>
  </div>

  <p class="chart-title">Top reps win on number of orders, not order size</p>
  <p class="chart-sub">Bubble size = net revenue. Average order values cluster around $1,100–1,800 for everyone.</p>
  {html(q2_scatter)}

  <p class="chart-title">Most reps grew sharply by 1998 — two did not</p>
  <p class="chart-sub">Net revenue per month, by year. Reps sorted by total revenue.</p>
  {html(q2_growth)}
  <details><summary>Show full rep scorecard</summary>{q2_table}</details>

  <h3>Main finding</h3>
  <p class="finding">Revenue differences between reps come from <em>how many orders and customers</em> they
  handle, not deal size. {top3.Rep.iloc[0]} leads with {money(top3.net_revenue.iloc[0])}
  ({pct(top3.revenue_share.iloc[0])}) from {top3.orders.iloc[0]} orders, and for 7 of the 9 reps the t-test
  finds no significant difference between their average order value and the rest of the team's. The two
  exceptions write significantly <em>smaller</em> orders ({aov_sig_detail}). Most reps roughly doubled their monthly revenue from 1997 to
  1998, but Michael Suyama and Steven Buchanan stayed flat. Robert King gives the deepest discounts
  ({pct(reps.set_index('Rep').discount_given_pct['Robert King'])}) and Anne Dodsworth has the highest late-shipment
  rate ({pct(reps.set_index('Rep').late_rate['Anne Dodsworth'])}).</p>
  <h3>Business implication</h3>
  <p class="implication">Focus coaching and territory planning on customer coverage and order frequency rather
  than upselling. Follow up specifically on Suyama's and Buchanan's flat
  growth, why Suyama's and Callahan's orders run smaller, King's discounting, and Dodsworth's late
  shipments.</p>
  <p class="caveat">Caveat: Andrew Fuller (VP) and Steven Buchanan (manager) also carry management duties, and
  customer assignments are not random, so raw totals are not a pure measure of individual skill.</p>
</section>""" + pager(TABS[1], TABS[3]))
render_page("bundles.html", "Bundles · Northwind Sales Insights",
            f"""<section class="q" id="q3">
  <div class="qnum">Question 3</div>
  <h2>Which products tend to be bundled or bought together?</h2>
  <h3>Why it matters</h3>
  <p>Products that reliably appear together are candidates for bundles, cross-sell prompts, and
  coordinated stocking. They also point to future directions for product marketing: which pairings
  to feature in promotions, catalogs and recommendations, and which product combinations are worth
  testing next.</p>
  <h3>Approach</h3>
  <p>Market-basket analysis over {r3['n_orders']} orders: for every product pair seen together in at least
  5 orders, compute <em>lift</em> (how much more often they co-occur than if bought independently) and
  confidence. "Chance" is the number of orders expected to contain both products if customers chose
  them independently: the share of orders with product A × the share with product B × the total number
  of orders. Lift is the actual number of shared orders divided by that expected number, so 1.0× means
  exactly as often as chance. A chi-square test checks whether each pair appears together more often
  than chance.
  The same lift is computed between product categories.</p>

  <div class="stats">
    <div class="stat"><b>{int(top.orders_together)}</b><span>orders contain both the scones and the maple syrup</span></div>
    <div class="stat"><b>{top.lift:.1f}×</b><span>Sir Rodney's Scones + Sirop d'érable vs. chance</span></div>
  </div>

  <p class="chart-title">One pair stands out: scones and maple syrup</p>
  <p class="chart-sub">Top 12 pairs by lift (min. 5 shared orders). The strongest pair is highlighted in blue.</p>
  {html(q3_pairs)}
  <details><summary>Show table</summary>{pairs_table}</details>

  <p class="chart-title">Categories are bought together slightly <em>less</em> than chance</p>
  <p class="chart-sub">Lift between product categories. Red = less often than chance, blue = more often.</p>
  {html(q3_heat)}

  <h3>Main finding</h3>
  <p class="finding">One pairing stands well above the rest: Sir Rodney's Scones and Sirop d'érable appear together
  in {int(top.orders_together)} orders — {top.lift:.1f}× more than chance, and {top.conf_b_to_a:.0%} of
  maple-syrup orders also include the scones (chi-square {ptxt(top.chisq_p)}). Several cheese and dessert pairs
  (e.g. Gorgonzola Telino with Pavlova or Mozzarella) are 2–3× chance but rest on only 5–7 orders. At the category
  level every pair sits below 1.0: customers place focused orders rather than mixed baskets.</p>
  <h3>Business implication</h3>
  <p class="implication">Launch a scones-and-syrup bundle or cross-sell prompt — the evidence supports it. Treat the
  cheese/dessert pairs as hypotheses to test with a small promotion rather than as established patterns. Because
  orders are small and focused, broad cross-category bundling is unlikely to pay off.</p>
  <p class="caveat">Caveat: with 77 products and a median of 2 items per order, most pairs are rare, so lift
  estimates for low-count pairs are unstable. The chi-square test is also only approximate when counts are
  this small, so treat pairs with p-values near 0.05 as borderline.</p>
</section>""" + pager(TABS[2], None))
