import numpy as np
import yfinance as yf
import plotly
import plotly.graph_objects as go
from flask import Flask, render_template
from flask import request
import json

def get_yf_tickers(tickers):
    return [yf.Ticker(t) for t in tickers]

def get_closing_prices(yf_tickers, period, interval='1d'):
    cps = []
    for t in yf_tickers:
        yf_history = t.history(period=period, interval=interval)
        cps.append(yf_history['Close'].values)
    dates = list(yf_history.index)
    return dates, cps

def calc_ratios(closing_prices):
    xlnx_cp, amd_cp = closing_prices
    return np.divide(xlnx_cp, amd_cp)

def calc_gains(mr_cps, cps, r):
    xlnx_mr, _ = mr_cps
    xlnx_cp, amd_cp = cps
    diff = xlnx_mr-xlnx_cp
    xnlx_rise_gains = diff+r*amd_cp-xlnx_cp
    amd_drop_gains = diff+amd_cp-(xlnx_cp/r)
    mm_gains = diff+(2/(r+1))*(r*amd_cp-xlnx_cp)
    return xnlx_rise_gains, amd_drop_gains, mm_gains

def fig_update_layout(fig, legend, xaxis, yaxis):
    fig.update_layout(
        template="simple_white",
        showlegend=legend, 
        hovermode="x unified", 
        xaxis_title=xaxis,
        yaxis_title=yaxis,
        margin=dict(l=20, r=20, t=20, b=20),
        legend=dict(yanchor="top",y=0.99,xanchor="right",x=0.99))
    return fig

def graph_ratios(dates, ratios):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=ratios, mode='lines', name='Ratio', hovertemplate='<b>Ratio</b>: %{y:.3f}<extra></extra>', line_color="blue"))                    
    return fig_update_layout(fig, False, "Date", "XNLX/AMD Ratio")

def graph_prices(dates, cps):
    xlnx_cp, amd_cp = cps
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=xlnx_cp, mode='lines', name='XNLX', line_color="purple", hovertemplate='<b>XNLX</b>: %{y:.2f}<extra></extra>'))
    fig.add_trace(go.Scatter(x=dates, y=amd_cp, mode='lines', name='AMD', line_color="rgb(237, 28, 36)", hovertemplate='<b>AMD</b>: %{y:.2f}<extra></extra>'))
    return fig_update_layout(fig, True, "Date", "Stock Price ($)")

def graph_gains(dates, gains):
    xnlx_rise_gains, amd_drop_gains, mm_gains = gains
    fig = go.Figure(go.Scatter(x=dates, y=mm_gains, hovertemplate='<b>Meet in Middle</b>: %{y:.2f}<extra></extra>'))
    fig.add_hline(y=1, line_color='rgb(191, 52, 52)', line_width=1, line_dash='dash')
    fig.add_trace(go.Scatter(
        x=np.concatenate([dates, dates[::-1]]),
        y=np.concatenate([xnlx_rise_gains, amd_drop_gains[::-1]]),
        customdata=np.concatenate([amd_drop_gains, xnlx_rise_gains[::-1]]),
        line_color='rgb(205, 209, 228)',
        fill='toself',
        hovertemplate='<b>Range</b>: %{y:.2f} to %{customdata:.2f}<extra></extra>'
    ))
    fig.update_traces(hoverinfo='skip')
    fig.for_each_trace(lambda t: t.update(hoveron='points'))
    return fig_update_layout(fig, False, "Purchase Date", "Gain/Loss ($)")

def get_data(duration):
    mr = 1.7234
    tickers = ['XLNX','AMD']
    yft = get_yf_tickers(tickers)
    dates, cps = get_closing_prices(yft, '1d', '5m')       # today's data
    mr_cps = [cp[-1] for cp in cps]                        # most recent prices

    if duration == "Month":
        dates, cps = get_closing_prices(yft, '1mo') 
    if duration == "Year":
        dates, cps = get_closing_prices(yft, '1y')
    if duration == "Three_Months":
        dates, cps = get_closing_prices(yft, '3mo')

    fig1 = graph_prices(dates, cps)
    fig2 = graph_ratios(dates, calc_ratios(cps))
    fig3 = graph_gains(dates, calc_gains(mr_cps, cps, mr))
    graph1JSON = json.dumps(fig1, cls=plotly.utils.PlotlyJSONEncoder)
    graph2JSON = json.dumps(fig2, cls=plotly.utils.PlotlyJSONEncoder)
    graph3JSON = json.dumps(fig3, cls=plotly.utils.PlotlyJSONEncoder)
    return graph1JSON, graph2JSON, graph3JSON

app = Flask(__name__)

@app.route("/", methods=['GET', 'POST'])
def view():
    if request.method == 'POST':
        duration = request.form.get('duration')
        duration = duration.replace(" ", "_")
    else: 
        duration = 'Three_Months'
    graph1JSON, graph2JSON, graph3JSON = get_data(duration)
    return render_template("index.html", graph1JSON=graph1JSON, graph2JSON=graph2JSON, graph3JSON=graph3JSON, duration=duration)
