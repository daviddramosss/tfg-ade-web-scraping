import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from src.matching import match_across_files

# ============================================================================
# CONFIGURACIÓN Y CONSTANTES
# ============================================================================

NOISE_TERMS = {
    "monitor", "tablet", "impresora", "all in one",
    "ipad", "tab", "multifunción", "smart monitor"
}

PLATFORM_COLORS = {
    "Amazon": "#007185",
    "PcComponentes": "#FF6000",
    "ElCorteIngles": "#212121",
}

# Paleta para gráficos de specs
SPEC_COLORS = [
    "#007185", "#FF6000", "#2E7D32", "#C62828",
    "#6A1B9A", "#EF6C00", "#0277BD", "#AD1457",
    "#00695C", "#4E342E",
]

INR_TO_EUR = 0.012  # Tasa de conversión aprox. rupia india → euro


def _is_laptop(nombre: str) -> bool:
    if not isinstance(nombre, str):
        return True
    nombre_lower = nombre.lower()
    return not any(term in nombre_lower for term in NOISE_TERMS)


def _pick_latest_unique_csv(files):
    """Elige el CSV más reciente, deduplicando por nombre y priorizando /specs/."""
    if not files:
        return None

    unique_by_name = {}
    for f in sorted(files):
        current = unique_by_name.get(f.name)
        if current is None:
            unique_by_name[f.name] = f
            continue

        current_in_specs = "specs" in current.parts
        candidate_in_specs = "specs" in f.parts
        if candidate_in_specs and not current_in_specs:
            unique_by_name[f.name] = f
        elif candidate_in_specs == current_in_specs and str(f) > str(current):
            unique_by_name[f.name] = f

    return max(unique_by_name.values(), key=lambda p: p.name)


# ============================================================================
# CARGA DE DATOS
# ============================================================================

def load_data():
    """
    Carga datos en dos pasos:
      1. Lee CSVs procesados y aplica match_across_files (conserva producto_id)
      2. Enriquece con specs extraídas del dataset_maestro_*.csv
    """
    processed_path = Path("data/processed")

    # --- Paso 1: Matching (tu flujo original) ---
    # Búsqueda recursiva para incluir CSVs en subcarpetas (p. ej., simulado/)
    proc_files = sorted(
        f for f in processed_path.rglob("*.csv")
        if f.name.startswith("precios_portatiles_procesado_")
    )
    if not proc_files:
        return pd.DataFrame()

    dfs = []
    for f in proc_files:
        part = pd.read_csv(f)
        if 'es_simulado' not in part.columns:
            part['es_simulado'] = False
        dfs.append(part)

    df = match_across_files(dfs)
    df['fecha_extraccion'] = pd.to_datetime(df['fecha_extraccion'])
    df = df[df['nombre'].apply(_is_laptop)].copy()

    # --- Paso 2: Enriquecer con specs del dataset_maestro ---
    maestro_files = list(processed_path.rglob("dataset_maestro_*.csv"))
    maestro_latest = _pick_latest_unique_csv(maestro_files)
    if maestro_latest:
        maestro = pd.read_csv(maestro_latest)
        spec_cols = ['nombre', 'marca', 'ram_gb', 'almacenamiento_gb',
                     'cpu', 'gpu', 'tamanio_pantalla', 'sistema_operativo']
        spec_cols = [c for c in spec_cols if c in maestro.columns]
        specs = maestro[spec_cols].drop_duplicates(subset=['nombre'], keep='first')
        df = df.merge(specs, on='nombre', how='left')
    else:
        # Fallback: extraer marca con regex de matching.py
        from src.matching import _BRAND
        def get_brand(name):
            m = _BRAND.search(str(name))
            return m.group(1).upper() if m else "OTRA"
        df['marca'] = df['nombre'].apply(get_brand)

    return df


def load_kaggle_benchmark():
    """Carga el benchmark de Kaggle para análisis comparativo."""
    processed_path = Path("data/processed")
    kaggle_files = list(processed_path.rglob("kaggle_benchmark_*.csv"))
    kaggle_latest = _pick_latest_unique_csv(kaggle_files)
    if not kaggle_latest:
        return None

    kg = pd.read_csv(kaggle_latest)
    # Normalizar columnas
    kg['precio_eur'] = kg['price'] * INR_TO_EUR
    if 'ram_gb' not in kg.columns and 'Ram' in kg.columns:
        import re
        kg['ram_gb'] = kg['Ram'].apply(
            lambda x: int(re.search(r'(\d+)', str(x)).group(1))
            if re.search(r'(\d+)', str(x)) else None
        )
    return kg


df_master = load_data()
df_kaggle = load_kaggle_benchmark()

# ============================================================================
# APP
# ============================================================================

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.LUX],
    title="TFG: Sistema de Monitorización de Precios"
)

# ============================================================================
# CSS
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

.Select-menu-outer {
    background-color: white;
}

.Select-control {
    border: 1px solid #D0D3D8;
    border-radius: 6px;
    background-color: white;
}
"""

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
# LAYOUT
# ============================================================================

# Opciones de filtros
platform_options = sorted(df_master['plataforma'].unique()) if len(df_master) > 0 else []
brand_options = sorted(df_master['marca'].dropna().unique()) if len(df_master) > 0 else []

# Opciones de RAM para filtro
ram_options = sorted(df_master['ram_gb'].dropna().unique()) if 'ram_gb' in df_master.columns else []

app.layout = html.Div([
    # SIDEBAR
    html.Div(className="sidebar", children=[
        html.Div([
            html.H2("📊 TFG Precios", style={
                'fontSize': '22px', 'fontWeight': '700',
                'marginBottom': '10px', 'letterSpacing': '-0.5px'
            }),
            html.P("Portátiles", style={
                'fontSize': '12px', 'color': 'rgba(255,255,255,0.7)',
                'margin': '0', 'textTransform': 'uppercase', 'letterSpacing': '1px'
            }),
        ], style={'marginBottom': '35px', 'paddingBottom': '20px',
                  'borderBottom': '1px solid rgba(255,255,255,0.2)'}),

        # Plataformas
        html.Div(className="filter-section", children=[
            html.Span("Plataformas", className="filter-title"),
            dcc.Checklist(
                id='platform-filter',
                options=[{'label': p, 'value': p} for p in platform_options],
                value=platform_options,
                inline=False,
                style={'display': 'flex', 'flexDirection': 'column', 'gap': '10px'},
                labelStyle={'color': 'white', 'fontSize': '13px', 'cursor': 'pointer'}
            )
        ]),

        # Marcas
        html.Div(className="filter-section", children=[
            html.Span("Marcas", className="filter-title"),
            dcc.Dropdown(
                id='brand-filter',
                options=[{'label': b, 'value': b} for b in brand_options],
                value=None,
                placeholder="Todas las marcas...",
                multi=True,
                style={'color': '#1a1a2e'}
            )
        ]),

        # RAM
        html.Div(className="filter-section", children=[
            html.Span("RAM (GB)", className="filter-title"),
            dcc.Dropdown(
                id='ram-filter',
                options=[{'label': f"{int(r)} GB", 'value': r} for r in ram_options],
                value=None,
                placeholder="Toda la RAM...",
                multi=True,
                style={'color': '#1a1a2e'}
            )
        ]),

        html.Hr(style={'borderColor': 'rgba(255,255,255,0.2)', 'margin': '30px 0'}),
        html.P("Dashboard de Inteligencia Competitiva", style={
            'fontSize': '11px', 'color': 'rgba(255,255,255,0.6)',
            'margin': '0', 'textAlign': 'center'
        }),
    ]),

    # CONTENIDO PRINCIPAL
    html.Div(className="main-content", children=[
        # Header
        html.Div(className="header", children=[
            html.H1("TFG: Sistema de Monitorización de Precios de Portátiles"),
            html.P("Análisis de inteligencia competitiva | Amazon • PcComponentes • El Corte Inglés")
        ]),

        # KPIs
        dbc.Row([
            dbc.Col([html.Div(className="kpi-card", children=[
                html.Div("📊", className="kpi-icon"),
                html.Div("Productos", className="kpi-label"),
                html.Div(id="kpi-productos", className="kpi-value", children="0")
            ])], lg=3, md=6, sm=12, style={'marginBottom': '20px'}),

            dbc.Col([html.Div(className="kpi-card", children=[
                html.Div("💰", className="kpi-icon"),
                html.Div("Precio Medio", className="kpi-label"),
                html.Div(id="kpi-precio", className="kpi-value", children="0 €")
            ])], lg=3, md=6, sm=12, style={'marginBottom': '20px'}),

            dbc.Col([html.Div(className="kpi-card", children=[
                html.Div("🎯", className="kpi-icon"),
                html.Div("Máx. Descuento", className="kpi-label"),
                html.Div(id="kpi-descuento", className="kpi-value", children="0 %")
            ])], lg=3, md=6, sm=12, style={'marginBottom': '20px'}),

            dbc.Col([html.Div(className="kpi-card", children=[
                html.Div("🧠", className="kpi-icon"),
                html.Div("Specs Extraídas", className="kpi-label"),
                html.Div(id="kpi-specs", className="kpi-value", children="0 %")
            ])], lg=3, md=6, sm=12, style={'marginBottom': '20px'}),
        ], style={'marginBottom': '40px'}),

        # FILA: Evolución temporal
        dbc.Row([
            dbc.Col([html.Div(className="graph-container", children=[
                html.H3("Serie Temporal de Precios", className="section-title"),
                dcc.Graph(id='line-evolution', style={'height': '400px'},
                          config={'displayModeBar': False})
            ])], lg=12)
        ], style={'marginBottom': '30px'}),

        # FILA: Dispersión + Top descuentos
        dbc.Row([
            dbc.Col([html.Div(className="graph-container", children=[
                html.H3("Análisis de Dispersión", className="section-title"),
                dcc.Graph(id='scatter-dispersion', style={'height': '400px'},
                          config={'displayModeBar': False})
            ])], lg=6, md=12),

            dbc.Col([html.Div(className="table-container", children=[
                html.H3("Top Oportunidades (Hoy)", className="section-title"),
                html.Div(id='top-discounts-table')
            ])], lg=6, md=12),
        ], style={'marginBottom': '30px'}),

        # ====== NUEVOS GRÁFICOS CON SPECS ======

        # Separador visual
        html.Hr(style={'border': '2px solid #E8EAED', 'margin': '40px 0 30px'}),
        html.H2("Análisis de Especificaciones Técnicas", style={
            'fontSize': '24px', 'fontWeight': '700', 'color': '#1a1a2e',
            'marginBottom': '30px',
        }),

        # FILA: Precio vs RAM + Distribución CPU
        dbc.Row([
            dbc.Col([html.Div(className="graph-container", children=[
                html.H3("Precio vs RAM", className="section-title"),
                dcc.Graph(id='scatter-ram-price', style={'height': '420px'},
                          config={'displayModeBar': False})
            ])], lg=6, md=12),

            dbc.Col([html.Div(className="graph-container", children=[
                html.H3("Distribución por Procesador", className="section-title"),
                dcc.Graph(id='bar-cpu', style={'height': '420px'},
                          config={'displayModeBar': False})
            ])], lg=6, md=12),
        ], style={'marginBottom': '30px'}),

        # FILA: Benchmark España vs Kaggle
        dbc.Row([
            dbc.Col([html.Div(className="graph-container", children=[
                html.H3("Benchmark: España vs Mercado Internacional", className="section-title"),
                html.P("Precio medio por GB de RAM — Datos españoles (scraper) vs dataset internacional (Kaggle)",
                       style={'color': '#7f8c8d', 'fontSize': '13px', 'marginBottom': '15px'}),
                dcc.Graph(id='benchmark-chart', style={'height': '420px'},
                          config={'displayModeBar': False})
            ])], lg=12),
        ], style={'marginBottom': '30px'}),
    ])
])

# ============================================================================
# HELPERS PARA GRÁFICOS
# ============================================================================

_PLOTLY_BASE = dict(
    template='plotly_white',
    plot_bgcolor='white',
    paper_bgcolor='white',
    font=dict(family='Segoe UI, sans-serif', size=12, color='#1a1a2e'),
)

_PLOTLY_AXES = dict(
    xaxis=dict(gridcolor='#E8EAED', zeroline=False),
    yaxis=dict(gridcolor='#E8EAED', zeroline=False),
)

_PLOTLY_LEGEND_H = dict(
    orientation='h', yanchor='top', y=-0.15, xanchor='center', x=0.5
)


def _empty_fig(msg="Sin datos disponibles"):
    fig = go.Figure()
    fig.add_annotation(text=msg, showarrow=False, font=dict(size=14, color='#7f8c8d'))
    fig.update_layout(**_PLOTLY_BASE)
    return fig


# ============================================================================
# CALLBACKS
# ============================================================================

@app.callback(
    [Output('kpi-productos', 'children'),
     Output('kpi-precio', 'children'),
     Output('kpi-descuento', 'children'),
     Output('kpi-specs', 'children'),
     Output('line-evolution', 'figure'),
     Output('top-discounts-table', 'children'),
     Output('scatter-dispersion', 'figure'),
     Output('scatter-ram-price', 'figure'),
     Output('bar-cpu', 'figure'),
     Output('benchmark-chart', 'figure')],
    [Input('brand-filter', 'value'),
     Input('platform-filter', 'value'),
     Input('ram-filter', 'value')]
)
def update_dashboard(selected_brands, selected_platforms, selected_ram):

    # --- Filtrado ---
    dff = df_master.copy()
    if selected_platforms:
        dff = dff[dff['plataforma'].isin(selected_platforms)]
    if selected_brands:
        dff = dff[dff['marca'].isin(selected_brands)]
    if selected_ram and 'ram_gb' in dff.columns:
        dff = dff[dff['ram_gb'].isin(selected_ram)]

    # === KPIs ===
    n = len(dff)
    num_productos = dff['producto_id'].nunique() if n > 0 else 0
    precio_medio = dff['precio_actual_num'].mean() if n > 0 and dff['precio_actual_num'].notna().any() else 0
    max_descuento = dff['descuento_pct'].max() if n > 0 and dff['descuento_pct'].notna().any() else 0

    # Cobertura de specs
    if n > 0 and 'cpu' in dff.columns:
        specs_pct = dff['cpu'].notna().sum() / n * 100
    else:
        specs_pct = 0

    kpi_productos = f"{num_productos:.0f}"
    kpi_precio = f"{precio_medio:.0f} €"
    kpi_descuento = f"{max_descuento:.1f} %"
    kpi_specs = f"{specs_pct:.0f} %"

    # === 1. SERIE TEMPORAL ===
    if n > 0:
        evo = dff.groupby(['fecha_extraccion', 'plataforma'])['precio_actual_num'].mean().reset_index()
        fig_line = go.Figure()
        for plat in evo['plataforma'].unique():
            d = evo[evo['plataforma'] == plat]
            fig_line.add_trace(go.Scatter(
                x=d['fecha_extraccion'], y=d['precio_actual_num'],
                mode='lines', name=plat,
                line=dict(color=PLATFORM_COLORS.get(plat, '#999'), width=3),
                hovertemplate='<b>%{fullData.name}</b><br>%{x|%d/%m}<br>€%{y:.0f}<extra></extra>'
            ))
        fig_line.update_layout(**_PLOTLY_BASE, **_PLOTLY_AXES,
                               margin=dict(l=0, r=0, t=20, b=60),
                               hovermode='x unified',
                               legend=_PLOTLY_LEGEND_H)
    else:
        fig_line = _empty_fig()

    # === 2. TOP DESCUENTOS ===
    if n > 0:
        latest = dff['fecha_extraccion'].max()
        top = dff[dff['fecha_extraccion'] == latest].sort_values('descuento_pct', ascending=False).head(3)
    else:
        top = pd.DataFrame()

    if len(top) > 0:
        def _link_cell(row):
            enlace = row.get('enlace')
            nombre = row['nombre']
            if pd.notna(enlace) and str(enlace).strip().startswith('http'):
                return html.A(nombre, href=str(enlace), target="_blank",
                              rel="noopener noreferrer",
                              style={'color': '#007185', 'textDecoration': 'none', 'fontWeight': '500'})
            return nombre

        # Columna de specs resumida
        def _specs_badge(row):
            parts = []
            if 'ram_gb' in row and pd.notna(row.get('ram_gb')):
                parts.append(f"{int(row['ram_gb'])}GB")
            if 'cpu' in row and pd.notna(row.get('cpu')):
                cpu_short = str(row['cpu'])
                # Acortar: "Intel Core i5-13420H" → "i5-13420H"
                cpu_short = cpu_short.replace('Intel ', '').replace('AMD ', '')
                parts.append(cpu_short[:15])
            return " • ".join(parts) if parts else "—"

        th_style = {'backgroundColor': '#1a1a2e', 'color': 'white', 'fontWeight': '700'}
        table = dbc.Table([
            html.Thead(html.Tr([
                html.Th("Producto", style=th_style),
                html.Th("Specs", style=th_style),
                html.Th("Precio", style={**th_style, 'textAlign': 'center'}),
                html.Th("Dto.", style={**th_style, 'textAlign': 'center'}),
            ])),
            html.Tbody([
                html.Tr([
                    html.Td(_link_cell(row), style={'fontSize': '12px'}),
                    html.Td(_specs_badge(row), style={'fontSize': '11px', 'color': '#6A1B9A', 'fontWeight': '600'}),
                    html.Td(f"€{row['precio_actual_num']:.0f}",
                             style={'fontSize': '12px', 'textAlign': 'center', 'fontWeight': '600'}),
                    html.Td(f"{row['descuento_pct']:.1f}%",
                             style={'fontSize': '12px', 'textAlign': 'center',
                                    'backgroundColor': '#E8F5E9', 'fontWeight': '700', 'color': '#2E7D32'}),
                ]) for _, row in top.iterrows()
            ])
        ], bordered=True, hover=True, responsive=True)
    else:
        table = html.P("Sin datos", style={'color': '#7f8c8d', 'textAlign': 'center', 'padding': '20px'})

    # === 3. BOXPLOT DISPERSIÓN ===
    if n > 0:
        fig_box = go.Figure()
        for plat in sorted(dff['plataforma'].unique()):
            d = dff[dff['plataforma'] == plat]
            fig_box.add_trace(go.Box(
                y=d['precio_actual_num'], name=plat,
                marker=dict(color=PLATFORM_COLORS.get(plat, '#999')),
                boxmean=True,
                hovertemplate='<b>%{fullData.name}</b><br>€%{y:.0f}<extra></extra>'
            ))
        fig_box.update_layout(**_PLOTLY_BASE, **_PLOTLY_AXES,
                              margin=dict(l=0, r=0, t=20, b=60),
                              legend=_PLOTLY_LEGEND_H, hovermode='closest')
    else:
        fig_box = _empty_fig()

    # === 4. SCATTER: PRECIO vs RAM (NUEVO) ===
    if n > 0 and 'ram_gb' in dff.columns and dff['ram_gb'].notna().any():
        ram_data = dff[dff['ram_gb'].notna()].copy()
        ram_data['ram_gb'] = ram_data['ram_gb'].astype(int)

        fig_ram = go.Figure()

        for plat in sorted(ram_data['plataforma'].unique()):
            d = ram_data[ram_data['plataforma'] == plat]
            fig_ram.add_trace(go.Scatter(
                x=d['ram_gb'], y=d['precio_actual_num'],
                mode='markers', name=plat,
                marker=dict(
                    color=PLATFORM_COLORS.get(plat, '#999'),
                    size=10, opacity=0.7,
                    line=dict(width=1, color='white')
                ),
                hovertemplate=(
                    '<b>%{text}</b><br>'
                    'RAM: %{x} GB<br>'
                    'Precio: €%{y:.0f}<br>'
                    '<extra>%{fullData.name}</extra>'
                ),
                text=d['nombre'].str[:40],
            ))

        fig_ram.update_layout(
            **_PLOTLY_BASE,
            margin=dict(l=0, r=0, t=20, b=60),
            xaxis=dict(title='RAM (GB)', gridcolor='#E8EAED', zeroline=False,
                       dtick=4),
            yaxis=dict(title='Precio (€)', gridcolor='#E8EAED', zeroline=False),
            legend=_PLOTLY_LEGEND_H,
            hovermode='closest',
        )
    else:
        fig_ram = _empty_fig("Sin datos de RAM")

    # === 5. BARRAS: DISTRIBUCIÓN POR CPU (NUEVO) ===
    if n > 0 and 'cpu' in dff.columns and dff['cpu'].notna().any():
        cpu_data = dff[dff['cpu'].notna()].copy()

        # Simplificar nombres de CPU para agrupar mejor
        def simplify_cpu(cpu_name):
            name = str(cpu_name)
            # Agrupar por familia: "Intel Core i5-XXXX" → "Core i5"
            import re as _re
            m = _re.search(r'(Core\s+(?:Ultra\s+)?\d|Core\s+i[3579]|Ryzen\s+(?:AI\s+)?\d|Celeron|Pentium|Apple\s+M\d|M[1234])', name, _re.IGNORECASE)
            if m:
                return m.group(1).strip()
            return "Otro"

        cpu_data['cpu_familia'] = cpu_data['cpu'].apply(simplify_cpu)
        cpu_counts = cpu_data.groupby('cpu_familia').agg(
            cantidad=('cpu_familia', 'size'),
            precio_medio=('precio_actual_num', 'mean')
        ).sort_values('cantidad', ascending=True).tail(8)

        fig_cpu = go.Figure()
        fig_cpu.add_trace(go.Bar(
            y=cpu_counts.index,
            x=cpu_counts['cantidad'],
            orientation='h',
            marker=dict(color='#007185', opacity=0.85),
            text=[f"{int(c)} uds • €{p:.0f} medio"
                  for c, p in zip(cpu_counts['cantidad'], cpu_counts['precio_medio'])],
            textposition='auto',
            textfont=dict(size=11),
            hovertemplate='<b>%{y}</b><br>Cantidad: %{x}<extra></extra>',
        ))

        fig_cpu.update_layout(
            **_PLOTLY_BASE,
            margin=dict(l=100, r=20, t=20, b=40),
            xaxis=dict(title='Nº de productos', gridcolor='#E8EAED', zeroline=False),
            yaxis=dict(gridcolor='#E8EAED', zeroline=False),
            showlegend=False,
        )
    else:
        fig_cpu = _empty_fig("Sin datos de CPU")

    # === 6. BENCHMARK: ESPAÑA vs KAGGLE INTERNACIONAL (NUEVO) ===
    if n > 0 and df_kaggle is not None and 'ram_gb' in dff.columns:
        # España: precio medio por rango de RAM
        esp = dff[dff['ram_gb'].notna()].copy()
        esp['ram_gb'] = esp['ram_gb'].astype(int)
        esp_by_ram = esp.groupby('ram_gb')['precio_actual_num'].mean().reset_index()
        esp_by_ram.columns = ['ram_gb', 'precio_medio']

        # Kaggle: precio medio por rango de RAM (convertido a EUR)
        kg = df_kaggle[df_kaggle['ram_gb'].notna()].copy()
        kg['ram_gb'] = kg['ram_gb'].astype(int)
        kg_by_ram = kg.groupby('ram_gb')['precio_eur'].mean().reset_index()
        kg_by_ram.columns = ['ram_gb', 'precio_medio']

        # Solo RAM values que existan en ambos
        common_ram = sorted(set(esp_by_ram['ram_gb']) & set(kg_by_ram['ram_gb']))
        esp_filtered = esp_by_ram[esp_by_ram['ram_gb'].isin(common_ram)]
        kg_filtered = kg_by_ram[kg_by_ram['ram_gb'].isin(common_ram)]

        fig_bench = go.Figure()

        if len(common_ram) > 0:
            fig_bench.add_trace(go.Bar(
                x=[f"{r} GB" for r in esp_filtered['ram_gb']],
                y=esp_filtered['precio_medio'],
                name='España (Scraper)',
                marker=dict(color='#007185'),
                hovertemplate='<b>España</b><br>RAM: %{x}<br>Precio medio: €%{y:.0f}<extra></extra>',
            ))
            fig_bench.add_trace(go.Bar(
                x=[f"{r} GB" for r in kg_filtered['ram_gb']],
                y=kg_filtered['precio_medio'],
                name='Internacional (Kaggle)',
                marker=dict(color='#FF6000'),
                hovertemplate='<b>Internacional</b><br>RAM: %{x}<br>Precio medio: €%{y:.0f}<extra></extra>',
            ))

            fig_bench.update_layout(
                **_PLOTLY_BASE,
                margin=dict(l=0, r=0, t=20, b=60),
                barmode='group',
                xaxis=dict(title='RAM', gridcolor='#E8EAED', zeroline=False),
                yaxis=dict(title='Precio medio (€)', gridcolor='#E8EAED', zeroline=False),
                legend=_PLOTLY_LEGEND_H,
            )
        else:
            fig_bench = _empty_fig("Sin datos de RAM comunes entre fuentes")
    else:
        fig_bench = _empty_fig("Benchmark no disponible (falta kaggle_benchmark_*.csv)")

    return (kpi_productos, kpi_precio, kpi_descuento, kpi_specs,
            fig_line, table, fig_box,
            fig_ram, fig_cpu, fig_bench)


if __name__ == '__main__':
    app.run(debug=True, port=8050)