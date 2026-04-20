import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import pandas as pd
from src.matching import match_across_files

# ============================================================================
# CONFIGURACIÓN Y CONSTANTES
# ============================================================================

NOISE_TERMS = {
    "monitor", "tablet", "impresora", "all in one",
    "ipad", "tab", "multifunción", "smart monitor"
}

# Colores corporativos por plataforma
PLATFORM_COLORS = {
    "Amazon": "#007185",
    "PcComponentes": "#FF6000",
    "ElCorteIngles": "#212121",
}

def _is_laptop(nombre: str) -> bool:
    """Valida que sea un portátil filtrando términos de ruido."""
    if not isinstance(nombre, str):
        return True
    nombre_lower = nombre.lower()
    return not any(term in nombre_lower for term in NOISE_TERMS)

# ============================================================================
# CARGA Y PREPARACIÓN DE DATOS
# ============================================================================

def load_data():
    processed_path = Path("data/processed")
    files = sorted(processed_path.glob("*.csv"))
    if not files:
        return pd.DataFrame()

    dfs = [pd.read_csv(f) for f in files]
    df = match_across_files(dfs)
    df['fecha_extraccion'] = pd.to_datetime(df['fecha_extraccion'])

    # FILTRO DE SEGURIDAD: Elimina productos que no sean portátiles
    df = df[df['nombre'].apply(_is_laptop)].copy()

    # Extraemos la marca
    from src.matching import _BRAND
    def get_brand(name):
        m = _BRAND.search(str(name))
        return m.group(1).upper() if m else "OTRA"

    df['marca'] = df['nombre'].apply(get_brand)
    return df

df_master = load_data()

# ============================================================================
# INICIALIZACIÓN DE APP CON TEMA PROFESIONAL
# ============================================================================

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.LUX],
    title="TFG: Sistema de Monitorización de Precios"
)

# ============================================================================
# ESTILOS PERSONALIZADOS
# ============================================================================

custom_css = """
:root {
    --primary: #007185;
    --secondary: #FF6000;
    --tertiary: #212121;
    --light-bg: #F8F9FA;
    --card-bg: #FFFFFF;
}

body {
    background-color: var(--light-bg);
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.sidebar {
    background: linear-gradient(135deg, #1a1a2e 0%, #2d3561 100%);
    color: white;
    padding: 30px 20px;
    min-height: 100vh;
    position: fixed;
    top: 0;
    left: 0;
    width: 280px;
    overflow-y: auto;
    box-shadow: 2px 0 15px rgba(0, 0, 0, 0.1);
}

.main-content {
    margin-left: 280px;
    padding: 40px 30px;
    min-height: 100vh;
}

.header {
    background: white;
    padding: 25px 30px;
    margin-bottom: 40px;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    border-left: 5px solid var(--primary);
}

.header h1 {
    margin: 0;
    font-size: 32px;
    font-weight: 700;
    color: #1a1a2e;
    letter-spacing: -0.5px;
}

.header p {
    margin: 8px 0 0 0;
    color: #7f8c8d;
    font-size: 14px;
}

.kpi-card {
    background: white;
    border-radius: 12px;
    padding: 25px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    border: 1px solid #E8EAED;
    transition: all 0.3s ease;
    text-align: center;
}

.kpi-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.12);
}

.kpi-icon {
    font-size: 32px;
    margin-bottom: 12px;
}

.kpi-label {
    font-size: 13px;
    color: #7f8c8d;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-weight: 600;
    margin-bottom: 8px;
}

.kpi-value {
    font-size: 28px;
    font-weight: 700;
    color: #1a1a2e;
}

.filter-section {
    margin-bottom: 25px;
}

.filter-title {
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: rgba(255, 255, 255, 0.7);
    font-weight: 700;
    margin-bottom: 12px;
    display: block;
}

.section-title {
    font-size: 20px;
    font-weight: 700;
    color: #1a1a2e;
    margin-bottom: 20px;
    padding-bottom: 12px;
    border-bottom: 2px solid #E8EAED;
}

.graph-container {
    background: white;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 30px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.table-container {
    background: white;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

/* Personalización de Dropdowns y Checklists */
.Select-menu-outer {
    background-color: white;
}

.Select-control {
    border: 1px solid #D0D3D8;
    border-radius: 6px;
    background-color: white;
}
"""

# Inyectar CSS personalizado
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            ''' + custom_css + '''
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# ============================================================================
# LAYOUT - ESTRUCTURA CON SIDEBAR
# ============================================================================

app.layout = html.Div([
    # SIDEBAR
    html.Div(className="sidebar", children=[
        # Logo/Branding
        html.Div([
            html.H2("📊 TFG Precios", style={
                'fontSize': '22px',
                'fontWeight': '700',
                'marginBottom': '10px',
                'letterSpacing': '-0.5px'
            }),
            html.P("Portátiles", style={
                'fontSize': '12px',
                'color': 'rgba(255,255,255,0.7)',
                'margin': '0',
                'textTransform': 'uppercase',
                'letterSpacing': '1px'
            }),
        ], style={'marginBottom': '35px', 'paddingBottom': '20px', 'borderBottom': '1px solid rgba(255,255,255,0.2)'}),

        # FILTRO: PLATAFORMAS
        html.Div(className="filter-section", children=[
            html.Span("Plataformas", className="filter-title"),
            dcc.Checklist(
                id='platform-filter',
                options=[{'label': p, 'value': p} for p in sorted(df_master['plataforma'].unique())],
                value=sorted(df_master['plataforma'].unique().tolist()),
                inline=False,
                style={
                    'display': 'flex',
                    'flexDirection': 'column',
                    'gap': '10px'
                },
                labelStyle={
                    'color': 'white',
                    'fontSize': '13px',
                    'cursor': 'pointer',
                    'marginBottom': '0'
                }
            )
        ]),

        # FILTRO: MARCAS
        html.Div(className="filter-section", children=[
            html.Span("Marcas", className="filter-title"),
            dcc.Dropdown(
                id='brand-filter',
                options=[{'label': b, 'value': b} for b in sorted(df_master['marca'].unique())],
                value=None,
                placeholder="Todas las marcas...",
                multi=True,
                style={'color': '#1a1a2e'}
            )
        ]),

        # Footer del Sidebar
        html.Hr(style={'borderColor': 'rgba(255,255,255,0.2)', 'margin': '30px 0'}),
        html.P(
            "Dashboard de Inteligencia Competitiva",
            style={
                'fontSize': '11px',
                'color': 'rgba(255,255,255,0.6)',
                'margin': '0',
                'textAlign': 'center'
            }
        ),
    ]),

    # CONTENIDO PRINCIPAL
    html.Div(className="main-content", children=[
        # HEADER
        html.Div(className="header", children=[
            html.H1("TFG: Sistema de Monitorización de Precios de Portátiles"),
            html.P("Análisis de inteligencia competitiva | Amazon • PcComponentes • El Corte Inglés")
        ]),

        # FILA 1: KPIs
        dbc.Row([
            dbc.Col([
                html.Div(className="kpi-card", children=[
                    html.Div("📊", className="kpi-icon"),
                    html.Div("Productos", className="kpi-label"),
                    html.Div(id="kpi-productos", className="kpi-value", children="0")
                ])
            ], lg=3, md=6, sm=12, style={'marginBottom': '20px'}),

            dbc.Col([
                html.Div(className="kpi-card", children=[
                    html.Div("💰", className="kpi-icon"),
                    html.Div("Precio Medio", className="kpi-label"),
                    html.Div(id="kpi-precio", className="kpi-value", children="0 €")
                ])
            ], lg=3, md=6, sm=12, style={'marginBottom': '20px'}),

            dbc.Col([
                html.Div(className="kpi-card", children=[
                    html.Div("🎯", className="kpi-icon"),
                    html.Div("Máx. Descuento", className="kpi-label"),
                    html.Div(id="kpi-descuento", className="kpi-value", children="0 %")
                ])
            ], lg=3, md=6, sm=12, style={'marginBottom': '20px'}),

            dbc.Col([
                html.Div(className="kpi-card", children=[
                    html.Div("⚡", className="kpi-icon"),
                    html.Div("Velocidad Actualización", className="kpi-label"),
                    html.Div(id="kpi-actualizado", className="kpi-value", children="Hoy")
                ])
            ], lg=3, md=6, sm=12, style={'marginBottom': '20px'}),
        ], style={'marginBottom': '40px'}),

        # FILA 2: EVOLUCIÓN TEMPORAL
        dbc.Row([
            dbc.Col([
                html.Div(className="graph-container", children=[
                    html.H3("Serie Temporal de Precios", className="section-title"),
                    dcc.Graph(id='line-evolution', style={'height': '400px'})
                ])
            ], lg=12)
        ], style={'marginBottom': '30px'}),

        # FILA 3: DOS COLUMNAS
        dbc.Row([
            dbc.Col([
                html.Div(className="graph-container", children=[
                    html.H3("Análisis de Dispersión", className="section-title"),
                    dcc.Graph(id='scatter-dispersion', style={'height': '400px'})
                ])
            ], lg=6, md=12),

            dbc.Col([
                html.Div(className="table-container", children=[
                    html.H3("Top Oportunidades (Hoy)", className="section-title"),
                    html.Div(id='top-discounts-table')
                ])
            ], lg=6, md=12),
        ], style={'marginBottom': '30px'}),
    ])
])

# ============================================================================
# CALLBACKS - LÓGICA INTERACTIVA
# ============================================================================

@app.callback(
    [Output('kpi-productos', 'children'),
     Output('kpi-precio', 'children'),
     Output('kpi-descuento', 'children'),
     Output('kpi-actualizado', 'children'),
     Output('line-evolution', 'figure'),
     Output('top-discounts-table', 'children'),
     Output('scatter-dispersion', 'figure')],
    [Input('brand-filter', 'value'),
     Input('platform-filter', 'value')]
)
def update_dashboard(selected_brands, selected_platforms):
    # Filtrado dinámico
    if not selected_platforms:
        selected_platforms = []

    dff = df_master[df_master['plataforma'].isin(selected_platforms)] if selected_platforms else df_master.copy()
    if selected_brands:
        dff = dff[dff['marca'].isin(selected_brands)]

    # ===== KPIs =====
    num_productos = dff['producto_id'].nunique() if len(dff) > 0 else 0
    precio_medio = dff['precio_actual_num'].mean() if len(dff) > 0 and dff['precio_actual_num'].notna().any() else 0
    max_descuento = dff['descuento_pct'].max() if len(dff) > 0 and dff['descuento_pct'].notna().any() else 0

    # Obtener fecha de actualización
    fecha_actualizado = dff['fecha_extraccion'].max() if len(dff) > 0 else None
    if fecha_actualizado:
        from datetime import datetime, timedelta
        hoy = pd.Timestamp.now()
        diff = (hoy - fecha_actualizado).days
        if diff == 0:
            texto_fecha = "Hoy"
        elif diff == 1:
            texto_fecha = "Ayer"
        else:
            texto_fecha = f"Hace {diff}d"
    else:
        texto_fecha = "N/A"

    kpi_productos = f"{num_productos:.0f}"
    kpi_precio = f"{precio_medio:.0f} €"
    kpi_descuento = f"{max_descuento:.1f} %"

    # ===== GRÁFICO LÍNEA =====
    if len(dff) > 0:
        evolution_data = dff.groupby(['fecha_extraccion', 'plataforma'])['precio_actual_num'].mean().reset_index()

        fig_line = go.Figure()
        for platform in evolution_data['plataforma'].unique():
            platform_data = evolution_data[evolution_data['plataforma'] == platform]
            fig_line.add_trace(go.Scatter(
                x=platform_data['fecha_extraccion'],
                y=platform_data['precio_actual_num'],
                mode='lines',
                name=platform,
                line=dict(
                    color=PLATFORM_COLORS.get(platform, '#999999'),
                    width=3
                ),
                hovertemplate='<b>%{fullData.name}</b><br>Fecha: %{x|%d/%m}<br>Precio: €%{y:.2f}<extra></extra>'
            ))

        fig_line.update_layout(
            template='plotly_white',
            hovermode='x unified',
            margin=dict(l=0, r=0, t=0, b=0),
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(family='Segoe UI, sans-serif', size=12, color='#1a1a2e'),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
            xaxis=dict(gridcolor='#E8EAED', zeroline=False),
            yaxis=dict(gridcolor='#E8EAED', zeroline=False),
        )
    else:
        fig_line = go.Figure().add_annotation(text="Sin datos disponibles", showarrow=False)
        fig_line.update_layout(template='plotly_white')

    # ===== TABLA DESCUENTOS =====
    if len(dff) > 0:
        latest_date = dff['fecha_extraccion'].max()
        table_data = dff[dff['fecha_extraccion'] == latest_date].sort_values('descuento_pct', ascending=False).head(10)
    else:
        table_data = pd.DataFrame()

    if len(table_data) > 0:
        table = dbc.Table(
            [
                html.Thead(
                    html.Tr([
                        html.Th("Producto", style={'backgroundColor': '#1a1a2e', 'color': 'white', 'fontWeight': '700'}),
                        html.Th("Plataforma", style={'backgroundColor': '#1a1a2e', 'color': 'white', 'fontWeight': '700'}),
                        html.Th("Precio", style={'backgroundColor': '#1a1a2e', 'color': 'white', 'fontWeight': '700', 'textAlign': 'center'}),
                        html.Th("Descuento", style={'backgroundColor': '#1a1a2e', 'color': 'white', 'fontWeight': '700', 'textAlign': 'center'}),
                    ])
                ),
                html.Tbody([
                    html.Tr([
                        html.Td(row['nombre'][:40] + '...' if len(row['nombre']) > 40 else row['nombre'],
                               style={'fontSize': '12px', 'borderColor': '#E8EAED'}),
                        html.Td(row['plataforma'], style={'fontSize': '12px', 'borderColor': '#E8EAED', 'fontWeight': '600'}),
                        html.Td(f"€{row['precio_actual_num']:.0f}", style={'fontSize': '12px', 'textAlign': 'center', 'borderColor': '#E8EAED', 'fontWeight': '600'}),
                        html.Td(
                            f"{row['descuento_pct']:.1f}%",
                            style={
                                'fontSize': '12px',
                                'textAlign': 'center',
                                'borderColor': '#E8EAED',
                                'backgroundColor': '#E8F5E9',
                                'fontWeight': '700',
                                'color': '#2E7D32'
                            }
                        ),
                    ]) for _, row in table_data.iterrows()
                ])
            ],
            bordered=True,
            hover=True,
            responsive=True,
            striped=False,
        )
    else:
        table = html.P("Sin datos disponibles", style={'color': '#7f8c8d', 'textAlign': 'center', 'padding': '20px'})

    # ===== GRÁFICO BOXPLOT =====
    if len(dff) > 0:
        fig_box = go.Figure()
        for platform in sorted(dff['plataforma'].unique()):
            platform_data = dff[dff['plataforma'] == platform]
            fig_box.add_trace(go.Box(
                y=platform_data['precio_actual_num'],
                name=platform,
                marker=dict(color=PLATFORM_COLORS.get(platform, '#999999')),
                boxmean=True,
                hovertemplate='<b>%{fullData.name}</b><br>Precio: €%{y:.2f}<extra></extra>'
            ))

        fig_box.update_layout(
            template='plotly_white',
            margin=dict(l=0, r=0, t=0, b=0),
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(family='Segoe UI, sans-serif', size=12, color='#1a1a2e'),
            yaxis=dict(gridcolor='#E8EAED', zeroline=False),
            xaxis=dict(gridcolor='#E8EAED', zeroline=False),
            showlegend=False,
            hovermode='closest'
        )
    else:
        fig_box = go.Figure().add_annotation(text="Sin datos disponibles", showarrow=False)
        fig_box.update_layout(template='plotly_white')

    return kpi_productos, kpi_precio, kpi_descuento, texto_fecha, fig_line, table, fig_box

if __name__ == '__main__':
    app.run(debug=True, port=8050)
