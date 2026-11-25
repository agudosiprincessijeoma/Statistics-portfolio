"""Builds the Superstore Excel dashboard workbook.
Python is only used to split and clean the raw file and to lay out the sheets.
Every figure in the Analysis and Dashboard sheets is a live Excel formula."""
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.chart import LineChart, BarChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils import get_column_letter
from openpyxl.formatting.rule import DataBarRule, CellIsRule

RAW = "data/superstore_raw.csv"
# ---- 1. Split the stacked file into its three tables ----------
orders = pd.read_csv(RAW, encoding="latin-1", nrows=9994)
people = pd.read_csv(RAW, encoding="latin-1", skiprows=9995, nrows=4)
returns = pd.read_csv(RAW, encoding="latin-1", skiprows=10000)
print("orders", orders.shape, "| people", people.shape, "| returns", returns.shape,
      "| duplicate return rows", returns.duplicated().sum())
returns = returns.drop_duplicates().reset_index(drop=True)
for c in ["Order Date", "Ship Date"]:
    orders[c] = pd.to_datetime(orders[c], format="%m/%d/%Y")
orders["Postal Code"] = orders["Postal Code"].astype("Int64")

# ---- styles ----------------------------------------------------
F = "Arial"
NAVY, TEAL, RED, LIGHT = "1D3557", "2A6F97", "C1121F", "EAF2F8"
hdr_font = Font(name=F, bold=True, color="FFFFFF"); hdr_fill = PatternFill("solid", fgColor=NAVY)
title_font = Font(name=F, bold=True, size=16, color=NAVY)
sub_font = Font(name=F, italic=True, size=10, color="555555")
body = Font(name=F, size=10); bold = Font(name=F, size=10, bold=True)
thin = Side(style="thin", color="BFBFBF"); box = Border(top=thin, bottom=thin, left=thin, right=thin)
USD = '$#,##0;($#,##0);"-"'; PCT = '0.0%;(0.0%);"-"'

wb = Workbook()

# ---- 2. Orders sheet (data + calculated columns) ---------------
ws = wb.active; ws.title = "Orders"
cols = list(orders.columns)
calc = ["Year", "Month", "Profit Margin", "Discount Band", "Returned", "Regional Manager", "New Order"]
ws.append(cols + calc)
n = len(orders); last = n + 1
L = {c: get_column_letter(i + 1) for i, c in enumerate(cols + calc)}
for i, row in enumerate(orders.itertuples(index=False), start=2):
    vals = [v.to_pydatetime() if isinstance(v, pd.Timestamp) else (None if pd.isna(v) else v) for v in row]
    ws.append(vals + [
        f"=YEAR({L['Order Date']}{i})",
        f"=DATE(YEAR({L['Order Date']}{i}),MONTH({L['Order Date']}{i}),1)",
        f"=IF({L['Sales']}{i}=0,0,{L['Profit']}{i}/{L['Sales']}{i})",
        f'=IF({L["Discount"]}{i}=0,"0%",IF({L["Discount"]}{i}<=0.2,"1-20%",IF({L["Discount"]}{i}<=0.4,"21-40%","Over 40%")))',
        f'=IF(COUNTIF(Returns!$B:$B,{L["Order ID"]}{i})>0,"Yes","No")',
        f'=INDEX(People!$A:$A,MATCH({L["Region"]}{i},People!$B:$B,0))',
        f"=IF({L['Order ID']}{i}<>{L['Order ID']}{i-1},1,0)" if i > 2 else "=1",
    ])
for c in ["Order Date", "Ship Date"]:
    for cell in ws[L[c]][1:]: cell.number_format = "dd-mmm-yyyy"
for c in ["Sales", "Profit"]:
    for cell in ws[L[c]][1:]: cell.number_format = "#,##0.00"
for cell in ws[L["Discount"]][1:]: cell.number_format = "0%"
for cell in ws[L["Month"]][1:]: cell.number_format = "mmm-yyyy"
for cell in ws[L["Profit Margin"]][1:]: cell.number_format = "0.0%"
tab = Table(displayName="tblOrders", ref=f"A1:{L['New Order']}{last}")
tab.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
ws.add_table(tab)
ws.freeze_panes = "C2"
widths = {"Order ID": 16, "Order Date": 12, "Ship Date": 12, "Ship Mode": 14, "Customer Name": 20,
          "Product Name": 40, "Sub-Category": 13, "Category": 15, "Regional Manager": 18, "Discount Band": 13}
for c, col in L.items(): ws.column_dimensions[col].width = widths.get(c, 11)

# ---- 3. Returns and People sheets ------------------------------
wr = wb.create_sheet("Returns"); wr.append(["Returned", "Order ID"])
for r in returns.itertuples(index=False): wr.append(list(r))
wr.add_table(Table(displayName="tblReturns", ref=f"A1:B{len(returns)+1}",
                   tableStyleInfo=TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)))
wr.column_dimensions["A"].width = 11; wr.column_dimensions["B"].width = 18
wp = wb.create_sheet("People"); wp.append(["Person", "Region"])
for r in people.itertuples(index=False): wp.append(list(r))
wp.add_table(Table(displayName="tblPeople", ref="A1:B5",
                   tableStyleInfo=TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)))
wp.column_dimensions["A"].width = 20

# ---- 4. Analysis sheet -----------------------------------------
wa = wb.create_sheet("Analysis")
O = lambda c: f"Orders!${L[c]}$2:${L[c]}${last}"
S, P, Q, NEW, RET = O("Sales"), O("Profit"), O("Quantity"), O("New Order"), O("Returned")
wa["A1"] = "Analysis tables"; wa["A1"].font = title_font
wa["A2"] = "Every value below is a formula on the Orders sheet (SUMIFS, COUNTIFS, SUMPRODUCT)."; wa["A2"].font = sub_font

def header(ws_, r, c0, names):
    for j, nm in enumerate(names):
        cell = ws_.cell(r, c0 + j, nm); cell.font = hdr_font; cell.fill = hdr_fill
        cell.alignment = Alignment(horizontal="center", wrap_text=True); cell.border = box

def section(ws_, r, text):
    ws_.cell(r, 1, text).font = Font(name=F, bold=True, size=12, color=TEAL)

anchors = {}
# 4a KPIs
r = 4; section(wa, r, "1. Headline KPIs"); r += 1
header(wa, r, 1, ["Measure", "Value"])
kpis = [("Total sales", f"=SUM({S})", USD), ("Total profit", f"=SUM({P})", USD),
        ("Profit margin", "=B7/B6", PCT), ("Orders", f"=SUM({NEW})", "#,##0"),
        ("Order lines", f"=COUNTA({O('Order ID')})", "#,##0"),
        ("Average order value", "=B6/B9", USD), ("Units sold", f"=SUM({Q})", "#,##0"),
        ("Returned orders", f'=SUMIFS({NEW},{RET},"Yes")', "#,##0"),
        ("Order return rate", "=B13/B9", PCT)]
for k, (nm, f, fmt) in enumerate(kpis):
    rr = r + 1 + k; wa.cell(rr, 1, nm).font = body
    c = wa.cell(rr, 2, f); c.number_format = fmt; c.font = bold
anchors["kpi"] = r + 1
r = r + 1 + len(kpis) + 1

# 4b By year
section(wa, r, "2. Performance by year"); r += 1
header(wa, r, 1, ["Year", "Sales", "Profit", "Margin", "Orders", "Sales growth"]); y0 = r + 1
for k, yr in enumerate(sorted(orders["Order Date"].dt.year.unique())):
    rr = y0 + k
    wa.cell(rr, 1, str(yr))
    wa.cell(rr, 2, f"=SUMIFS({S},{O('Year')},VALUE(A{rr}))").number_format = USD
    wa.cell(rr, 3, f"=SUMIFS({P},{O('Year')},VALUE(A{rr}))").number_format = USD
    wa.cell(rr, 4, f"=IF(B{rr}=0,0,C{rr}/B{rr})").number_format = PCT
    wa.cell(rr, 5, f"=SUMIFS({NEW},{O('Year')},VALUE(A{rr}))").number_format = "#,##0"
    wa.cell(rr, 6, "" if k == 0 else f"=B{rr}/B{rr-1}-1").number_format = PCT
anchors["year"] = (y0, y0 + 3); r = y0 + 5

# 4c By region
section(wa, r, "3. Performance by region"); r += 1
header(wa, r, 1, ["Region", "Manager", "Sales", "Profit", "Margin", "Avg discount", "Order return rate"]); g0 = r + 1
for k, reg in enumerate(["West", "East", "Central", "South"]):
    rr = g0 + k; wa.cell(rr, 1, reg)
    wa.cell(rr, 2, f"=INDEX(People!$A$2:$A$5,MATCH(A{rr},People!$B$2:$B$5,0))")
    wa.cell(rr, 3, f"=SUMIFS({S},{O('Region')},A{rr})").number_format = USD
    wa.cell(rr, 4, f"=SUMIFS({P},{O('Region')},A{rr})").number_format = USD
    wa.cell(rr, 5, f"=IF(C{rr}=0,0,D{rr}/C{rr})").number_format = PCT
    wa.cell(rr, 6, f"=AVERAGEIFS({O('Discount')},{O('Region')},A{rr})").number_format = PCT
    wa.cell(rr, 7, f'=SUMIFS({NEW},{O("Region")},A{rr},{RET},"Yes")/SUMIFS({NEW},{O("Region")},A{rr})').number_format = PCT
anchors["region"] = (g0, g0 + 3); r = g0 + 6

# 4d By category
section(wa, r, "4. Performance by category"); r += 1
header(wa, r, 1, ["Category", "Sales", "Profit", "Margin", "Share of sales", "Share of profit"]); c0 = r + 1
for k, cat in enumerate(["Technology", "Office Supplies", "Furniture"]):
    rr = c0 + k; wa.cell(rr, 1, cat)
    wa.cell(rr, 2, f"=SUMIFS({S},{O('Category')},A{rr})").number_format = USD
    wa.cell(rr, 3, f"=SUMIFS({P},{O('Category')},A{rr})").number_format = USD
    wa.cell(rr, 4, f"=IF(B{rr}=0,0,C{rr}/B{rr})").number_format = PCT
    wa.cell(rr, 5, f"=B{rr}/$B${anchors['kpi']}").number_format = PCT
    wa.cell(rr, 6, f"=C{rr}/$B${anchors['kpi']+1}").number_format = PCT
anchors["cat"] = (c0, c0 + 2); r = c0 + 5

# 4e By sub-category (ordered by profit, lowest first, so the bar chart reads top-down)
section(wa, r, "5. Profit by sub-category (sorted lowest to highest profit)"); r += 1
header(wa, r, 1, ["Sub-category", "Category", "Sales", "Profit", "Margin", "Avg discount"]); s0 = r + 1
sub = orders.groupby(["Sub-Category", "Category"]).Profit.sum().sort_values().reset_index()
for k, row in sub.iterrows():
    rr = s0 + k; wa.cell(rr, 1, row["Sub-Category"]); wa.cell(rr, 2, row["Category"])
    wa.cell(rr, 3, f"=SUMIFS({S},{O('Sub-Category')},A{rr})").number_format = USD
    wa.cell(rr, 4, f"=SUMIFS({P},{O('Sub-Category')},A{rr})").number_format = USD
    wa.cell(rr, 5, f"=IF(C{rr}=0,0,D{rr}/C{rr})").number_format = PCT
    wa.cell(rr, 6, f"=AVERAGEIFS({O('Discount')},{O('Sub-Category')},A{rr})").number_format = PCT
s1 = s0 + len(sub) - 1; anchors["sub"] = (s0, s1)
wa.conditional_formatting.add(f"D{s0}:D{s1}", CellIsRule(operator="lessThan", formula=["0"], font=Font(name=F, color=RED, bold=True)))
r = s1 + 3

# 4f By discount band
section(wa, r, "6. The effect of discounting"); r += 1
header(wa, r, 1, ["Discount band", "Order lines", "Sales", "Profit", "Margin", "Share of lines"]); d0 = r + 1
for k, band in enumerate(["0%", "1-20%", "21-40%", "Over 40%"]):
    rr = d0 + k; wa.cell(rr, 1, band)
    wa.cell(rr, 2, f"=COUNTIFS({O('Discount Band')},A{rr})").number_format = "#,##0"
    wa.cell(rr, 3, f"=SUMIFS({S},{O('Discount Band')},A{rr})").number_format = USD
    wa.cell(rr, 4, f"=SUMIFS({P},{O('Discount Band')},A{rr})").number_format = USD
    wa.cell(rr, 5, f"=IF(C{rr}=0,0,D{rr}/C{rr})").number_format = PCT
    wa.cell(rr, 6, f"=B{rr}/$B${anchors['kpi']+4}").number_format = PCT
anchors["disc"] = (d0, d0 + 3)
rr = d0 + 5; wa.cell(rr, 1, "Correlation between discount and profit margin (order lines):").font = bold
wa.cell(rr, 6, f"=CORREL({O('Discount')},{O('Profit Margin')})").number_format = "0.00"
anchors["corr"] = rr; r = rr + 3

# 4g By segment
section(wa, r, "7. Performance by customer segment"); r += 1
header(wa, r, 1, ["Segment", "Sales", "Profit", "Margin", "Orders", "Avg order value"]); g20 = r + 1
for k, seg in enumerate(["Consumer", "Corporate", "Home Office"]):
    rr = g20 + k; wa.cell(rr, 1, seg)
    wa.cell(rr, 2, f"=SUMIFS({S},{O('Segment')},A{rr})").number_format = USD
    wa.cell(rr, 3, f"=SUMIFS({P},{O('Segment')},A{rr})").number_format = USD
    wa.cell(rr, 4, f"=IF(B{rr}=0,0,C{rr}/B{rr})").number_format = PCT
    wa.cell(rr, 5, f"=SUMIFS({NEW},{O('Segment')},A{rr})").number_format = "#,##0"
    wa.cell(rr, 6, f"=B{rr}/E{rr}").number_format = USD
anchors["seg"] = (g20, g20 + 2); r = g20 + 5

# 4h Monthly trend (helper table for line chart)
section(wa, r, "8. Monthly sales and profit"); r += 1
header(wa, r, 1, ["Month", "Sales", "Profit", "Sales, 3-month average"]); m0 = r + 1
months = pd.date_range("2015-01-01", "2018-12-01", freq="MS")
for k, mth in enumerate(months):
    rr = m0 + k; c = wa.cell(rr, 1, mth.to_pydatetime()); c.number_format = "mmm-yy"
    wa.cell(rr, 2, f"=SUMIFS({S},{O('Month')},A{rr})").number_format = USD
    wa.cell(rr, 3, f"=SUMIFS({P},{O('Month')},A{rr})").number_format = USD
    wa.cell(rr, 4, f"=AVERAGE(B{max(m0, rr-2)}:B{rr})" if k >= 2 else "").number_format = USD
m1 = m0 + len(months) - 1; anchors["month"] = (m0, m1)
# Seasonality: average share of annual sales by calendar month
rr = m1 + 2; section(wa, rr, "9. Seasonality: average sales by calendar month (2015 to 2018)"); rr += 1
header(wa, rr, 1, ["Month", "Average monthly sales"]); q0 = rr + 1
for k in range(12):
    rq = q0 + k; wa.cell(rq, 1, pd.Timestamp(2018, k + 1, 1).strftime("%b"))
    wa.cell(rq, 2, f"=AVERAGE(B{m0+k},B{m0+k+12},B{m0+k+24},B{m0+k+36})").number_format = USD
anchors["season"] = (q0, q0 + 11)

for row in wa.iter_rows(min_row=4, max_row=q0 + 11, max_col=7):
    for c in row:
        if c.value is not None and c.font != hdr_font and c.row not in ():
            if c.font.name != F or (not c.font.bold and c.font.color is None): c.font = Font(name=F, size=10, bold=c.font.bold, color=c.font.color)
wa.column_dimensions["A"].width = 26
for col in "BCDEFG": wa.column_dimensions[col].width = 16
wa.column_dimensions["B"].width = 18
wa.freeze_panes = "A4"

# ---- 5. Dashboard sheet ----------------------------------------
wd = wb.create_sheet("Dashboard", 0)
wd.sheet_view.showGridLines = False
wd.page_setup.orientation = "landscape"; wd.page_setup.fitToWidth = 1; wd.page_setup.fitToHeight = 1; wd.sheet_properties.pageSetUpPr.fitToPage = True
wd["B1"] = "Superstore Sales Performance Dashboard, 2015 to 2018"; wd["B1"].font = Font(name=F, bold=True, size=20, color=NAVY)
wd["B2"] = "Where does the profit come from, and what is eroding it?   |   Source: Sample Superstore (Tableau), 9,994 order lines   |   Built in Excel by Princess Ijeoma Agudosi"
wd["B2"].font = sub_font
for col in range(2, 26): wd.column_dimensions[get_column_letter(col)].width = 9.5
wd.column_dimensions["A"].width = 2
k0 = anchors["kpi"]
cards = [("Total sales", f"=Analysis!B{k0}", USD), ("Total profit", f"=Analysis!B{k0+1}", USD),
         ("Profit margin", f"=Analysis!B{k0+2}", PCT), ("Orders", f"=Analysis!B{k0+3}", "#,##0"),
         ("Avg order value", f"=Analysis!B{k0+5}", USD), ("Return rate", f"=Analysis!B{k0+8}", PCT)]
for j, (lab, f, fmt) in enumerate(cards):
    c1 = 2 + j * 4; cl, cr = get_column_letter(c1), get_column_letter(c1 + 2)
    wd.merge_cells(f"{cl}4:{cr}4"); wd.merge_cells(f"{cl}5:{cr}6")
    a = wd[f"{cl}4"]; a.value = lab; a.font = Font(name=F, size=10, bold=True, color="FFFFFF")
    a.alignment = Alignment(horizontal="center", vertical="center")
    v = wd[f"{cl}5"]; v.value = f; v.number_format = fmt
    v.font = Font(name=F, size=20, bold=True, color=NAVY); v.alignment = Alignment(horizontal="center", vertical="center")
    for rr in (4, 5, 6):
        for cc in range(c1, c1 + 3):
            wd.cell(rr, cc).fill = PatternFill("solid", fgColor=TEAL if rr == 4 else LIGHT)
wd.row_dimensions[5].height = 22; wd.row_dimensions[6].height = 18

def style(ch, title, ytitle=None, xtitle=None, w=17, h=8.2):
    ch.title = title; ch.width = w; ch.height = h; ch.roundedCorners = False
    ch.style = 2
    if hasattr(ch, "y_axis"):
        ch.y_axis.delete = False; ch.x_axis.delete = False
        ch.y_axis.majorGridlines = None if isinstance(ch, BarChart) and ch.type == "bar" else ch.y_axis.majorGridlines
        if ytitle: ch.y_axis.title = ytitle
        if xtitle: ch.x_axis.title = xtitle
    if ch.legend is not None: ch.legend.position = "b"; ch.legend.overlay = False

# Chart 1: monthly trend
m0, m1 = anchors["month"]
lc = LineChart()
lc.add_data(Reference(wa, min_col=2, min_row=m0 - 1, max_row=m1), titles_from_data=True)
lc.add_data(Reference(wa, min_col=4, min_row=m0 - 1, max_row=m1), titles_from_data=True)
lc.add_data(Reference(wa, min_col=3, min_row=m0 - 1, max_row=m1), titles_from_data=True)
lc.set_categories(Reference(wa, min_col=1, min_row=m0, max_row=m1))
style(lc, "Monthly sales and profit: strong growth with a year-end peak", "US$", w=24, h=8.2)
lc.y_axis.number_format = '$#,##0'; lc.x_axis.number_format = "mmm-yy"; lc.x_axis.tickLblSkip = 3; lc.x_axis.tickLblPos = "low"
for s, colr, wdt in zip(lc.series, ["9DB4C0", NAVY, "E76F51"], [12000, 28000, 22000]):
    s.graphicalProperties.line.solidFill = colr; s.graphicalProperties.line.width = wdt; s.smooth = False
wd.add_chart(lc, "B8")

# Chart 2: profit by sub-category (horizontal bar)
s0, s1 = anchors["sub"]
bc = BarChart(); bc.type = "bar"
bc.add_data(Reference(wa, min_col=4, min_row=s0 - 1, max_row=s1), titles_from_data=True)
bc.set_categories(Reference(wa, min_col=1, min_row=s0, max_row=s1))
style(bc, "Profit by sub-category: Tables, Bookcases and Supplies lose money", w=17, h=16.6)
bc.legend = None; bc.y_axis.number_format = '$#,##0'; bc.gapWidth = 40
bc.series[0].graphicalProperties.solidFill = TEAL; bc.series[0].invertIfNegative = False
from openpyxl.chart.series import DataPoint
for idx in range(3):
    pt = DataPoint(idx=idx); pt.graphicalProperties.solidFill = RED; bc.series[0].dPt.append(pt)
from openpyxl.chart.text import RichText
from openpyxl.drawing.text import Paragraph, ParagraphProperties, CharacterProperties, RichTextProperties
bc.x_axis.txPr = RichText(bodyPr=RichTextProperties(), p=[Paragraph(pPr=ParagraphProperties(defRPr=CharacterProperties(sz=800)), endParaRPr=CharacterProperties(sz=800))])
bc.x_axis.tickLblPos = "low"; bc.y_axis.number_format = '$#,##0,"k"'
wd.add_chart(bc, "O8")

# Chart 3: profit and margin by discount band
d0, d1 = anchors["disc"]
dc = BarChart(); dc.type = "col"
dc.add_data(Reference(wa, min_col=4, min_row=d0 - 1, max_row=d1), titles_from_data=True)
dc.set_categories(Reference(wa, min_col=1, min_row=d0, max_row=d1))
style(dc, "Profit by discount band: discounts above 20% destroy profit", "US$", "Discount band", w=12.8)
dc.legend = None; dc.y_axis.number_format = '$#,##0'
dc.series[0].graphicalProperties.solidFill = TEAL; dc.series[0].invertIfNegative = False
for idx in (2, 3):
    pt = DataPoint(idx=idx); pt.graphicalProperties.solidFill = RED; dc.series[0].dPt.append(pt)
dc.dataLabels = DataLabelList(); dc.dataLabels.showVal = True; dc.dataLabels.showSerName = False; dc.dataLabels.showCatName = False; dc.dataLabels.showLegendKey = False; dc.dataLabels.numFmt = '$#,##0'; dc.x_axis.tickLblPos = 'low'
wd.add_chart(dc, "B25")

# Chart 4: sales and profit by region
g0, g1 = anchors["region"]
rc = BarChart(); rc.type = "col"
rc.add_data(Reference(wa, min_col=3, min_row=g0 - 1, max_col=4, max_row=g1), titles_from_data=True)
rc.set_categories(Reference(wa, min_col=1, min_row=g0, max_row=g1))
style(rc, "Sales and profit by region", "US$", w=11)
rc.y_axis.number_format = '$#,##0'
rc.series[0].graphicalProperties.solidFill = "9DB4C0"; rc.series[1].graphicalProperties.solidFill = NAVY
wd.add_chart(rc, "I25")

# Notes / insights box
ins = ["Key insights",
       "1. Sales grew 51% from 2015 to 2018, and margin improved from 10.2% to 12.7%.",
       "2. Technology and Office Supplies earn 93% of profit. Furniture makes 32% of sales but only 6% of profit.",
       "3. Order lines discounted above 20% lose US$135k in total. Discount and margin are strongly negatively correlated (r = -0.86).",
       "4. Tables, Bookcases and Supplies are loss-making; Tables alone lose US$17.7k on heavy discounts.",
       "5. Central has the highest average discount and the lowest margin of the four regions.",
       "6. The West has the best margin but returns 11.7% of its orders, about four times the rate of every other region.",
       "7. Sales peak every year in September, November and December, so stock and staffing should follow."]
for k, t in enumerate(ins):
    c = wd.cell(42 + k, 2, t); c.font = Font(name=F, size=11 if k else 13, bold=(k == 0), color=NAVY if k == 0 else "222222")
wd["B50"] = "All figures update automatically from the Orders sheet. See the About sheet for method and definitions."; wd["B50"].font = sub_font

# ---- 6. About sheet --------------------------------------------
ab = wb.create_sheet("About", 1)
ab.column_dimensions["A"].width = 24; ab.column_dimensions["B"].width = 110
rows = [
    ("Project", "Project 5: Data visualisation using Excel: Superstore sales and profitability dashboard"),
    ("Author", "Princess Ijeoma Agudosi, MSc Statistics"),
    ("Research question", "Which regions, products, customer segments and pricing decisions drive profit for a US office-supplies retailer, and what is eroding its margin?"),
    ("Data source", "Sample Superstore dataset (Tableau sample data), via github.com/leonism/sample-superstore. Fictional retail data, 9,994 order lines, January 2015 to December 2018."),
    ("Data cleaning", "The downloaded CSV contained three tables stacked on top of each other: Orders (9,994 rows), People (4 regional managers) and Returns (800 rows). They were split into separate sheets, and 504 duplicate rows were removed from Returns, leaving 296 unique returned orders."),
    ("Calculated columns", "Orders sheet: Year, Month, Profit Margin, Discount Band (0%, 1-20%, 21-40%, over 40%), Returned (COUNTIF on Returns), Regional Manager (INDEX/MATCH on People) and New Order (flags the first line of each order, so orders can be counted without double counting)."),
    ("Analysis", "Analysis sheet: SUMIFS, COUNTIFS, AVERAGEIFS and CORREL summaries by year, month, region, category, sub-category, discount band and segment. No values are typed in; everything recalculates if the data change."),
    ("Dashboard", "KPI cards plus four native Excel charts. Colour is used for meaning: red marks loss-making items, so the eye goes straight to the problems."),
    ("Definitions", "Profit margin = profit / sales. Order return rate = returned orders / all orders. Average order value = sales / number of orders."),
    ("Limitations", "Fictional data. Profit is as recorded in the dataset, with no detail on cost structure. Discount and product mix are linked, so the discount effect is an association, not a controlled estimate."),
]
ab["A1"] = "About this workbook"; ab["A1"].font = title_font
for k, (a, b) in enumerate(rows, start=3):
    ab.cell(k, 1, a).font = bold; c = ab.cell(k, 2, b); c.font = body; c.alignment = Alignment(wrap_text=True, vertical="top")
    ab.cell(k, 1).alignment = Alignment(vertical="top")
ab["A15"] = "Sheets"; ab["A15"].font = bold
ab["B15"] = "Dashboard | About | Orders (data) | Returns | People | Analysis"; ab["B15"].font = body

wb.save("superstore_dashboard.xlsx")
print("saved")
