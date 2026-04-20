import sys
from pathlib import Path

# Solución definitiva al Path: añade la raíz del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent))

import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
import re
from src.matching import match_across_files

# 1. CARGA Y PREPARACIÓN DE DATOS
def load_data():
    processed_path = Path("data/processed")
    files = sorted(processed_path.glob("*.csv"))
    if not files:
        return pd.DataFrame()
    
    # Leemos todos los días y aplicamos el matching global
    dfs = [pd.read_csv(f) for f in files]
    df = match_across_files(dfs)
    df['fecha_extraccion'] = pd.to_datetime(df['fecha_extraccion'])
    
    # Extraemos la marca para el filtro (usando tu lógica de matching)
    from src.matching import _BRAND
    def get_brand(name):
        m = _BRAND.search(str(name))
        return m.group(1).upper() if m else "OTRA"
    
    df['marca'] = df['nombre'].apply(get_brand)
    return df

df_master = load_data()

# 2. INICIALIZACIÓN DE APP
app = dash.Dash(__name__, title="TFG Dynamic Pricing Dashboard")

app.layout = html.Div(style={'fontFamily': 'Arial, sans-serif', 'padding': '20px'}, children=[
    html.H1("Análisis de Inteligencia Competitiva - TFG ADE", style={'textAlign': 'center', 'color': '#2c3e50'}),
    html.Hr(),

    # SECCIÓN DE FILTROS
    html.Div([
        html.Div([
            html.Label("🔍 Filtrar por Marca:", style={'fontWeight': 'bold'}),
            dcc.Dropdown(
                id='brand-filter',
                options=[{'label': b, 'value': b} for b in sorted(df_master['marca'].unique())],
                value=None,
                placeholder="Todas las marcas...",
                multi=True
            )
        ], style={'width': '48%', 'display': 'inline-block'}),
        
        html.Div([
            html.Label("🛒 Filtrar por Plataforma:", style={'fontWeight': 'bold'}),
            dcc.Checklist(
                id='platform-filter',
                options=[{'label': p, 'value': p} for p in df_master['plataforma'].unique()],
                value=df_master['plataforma'].unique().tolist(),
                inline=True,
                style={'padding': '10px'}
            )
        ], style={'width': '48%', 'display': 'inline-block', 'float': 'right'}),
    ], style={'marginBottom': '30px', 'backgroundColor': '#f8f9fa', 'padding': '15px', 'borderRadius': '10px'}),

    # FILA 1: KPIs dinámicos
    html.Div(id='kpi-container', style={'display': 'flex', 'justifyContent': 'space-around', 'marginBottom': '30px'}),

    # FILA 2: Gráfico de Evolución
    html.Div([
        html.H2("Serie Temporal de Precios", style={'fontSize': '18px'}),
        dcc.Graph(id='line-evolution')
    ], style={'marginBottom': '50px'}),

    # FILA 3: Descuentos y Dispersión
    html.Div(style={'display': 'flex', 'gap': '20px'}, children=[
        html.Div([
            html.H2("Top Oportunidades (Hoy)", style={'fontSize': '18px'}),
            html.Div(id='top-discounts-table')
        ], style={'width': '50%'}),

        html.Div([
            html.H2("Análisis de Dispersión (Boxplot)", style={'fontSize': '18px'}),
            dcc.Graph(id='scatter-dispersion')
        ], style={'width': '50%'})
    ])
])

# 3. CALLBACKS (LÓGICA INTERACTIVA)
@app.callback(
    [Output('kpi-container', 'children'),
     Output('line-evolution', 'figure'),
     Output('top-discounts-table', 'children'),
     Output('scatter-dispersion', 'figure')],
    [Input('brand-filter', 'value'),
     Input('platform-filter', 'value')]
)
def update_dashboard(selected_brands, selected_platforms):
    # Filtrado dinámico
    dff = df_master[df_master['plataforma'].isin(selected_platforms)]
    if selected_brands:
        dff = dff[dff['marca'].isin(selected_brands)]

    # 1. KPIs
    kpis = [
        html.Div([html.H3("Productos"), html.P(dff['producto_id'].nunique())], className="kpi-card"),
        html.Div([html.H3("Precio Medio"), html.P(f"{dff['precio_actual_num'].mean():.2f} €")], className="kpi-card"),
        html.Div([html.H3("Máx. Descuento"), html.P(f"{dff['descuento_pct'].max():.1f} %")], className="kpi-card"),
    ]

    # 2. Evolución (Agrupada por fecha y plataforma)
    fig_line = px.line(
        dff.groupby(['fecha_extraccion', 'plataforma'])['precio_actual_num'].mean().reset_index(),
        x='fecha_extraccion', y='precio_actual_num', color='plataforma',
        labels={'precio_actual_num': 'Precio Medio (€)'},
        template="plotly_white",
        line_shape="linear"
    )

    # 3. Tabla de descuentos (Última fecha disponible)
    latest_date = dff['fecha_extraccion'].max()
    table_data = dff[dff['fecha_extraccion'] == latest_date].sort_values('descuento_pct', ascending=False).head(10)
    
    table = dash_table.DataTable(
        data=table_data.to_dict('records'),
        columns=[{"name": i, "id": i} for i in ['nombre', 'plataforma', 'precio_actual_num', 'descuento_pct']],
        style_cell={'textAlign': 'left', 'padding': '5px', 'fontSize': '11px', 'whiteSpace': 'normal', 'height': 'auto'},
        style_header={'backgroundColor': '#2c3e50', 'color': 'white'}
    )

    # 4. Boxplot
    fig_box = px.box(
        dff, x='plataforma', y='precio_actual_num', color='plataforma',
        points="all", template="plotly_white", title="Rango de Precios"
    )

    return kpis, fig_line, table, fig_box

if __name__ == '__main__':
    app.run(debug=True, port=8050)