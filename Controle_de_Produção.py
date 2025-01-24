import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import plotly.graph_objs as go
import pandas as pd
import requests
from io import BytesIO
import os

app = dash.Dash(__name__)
app.title = 'Análise de Produção Diária'

# URL direta para a imagem no GitHub
image_url = 'https://github.com/JacoLucas/producaodiaria/raw/main/LOGO MLC Infra.jpg'

# URLs dos arquivos no GitHub
file_urls = {
    'Obra 500 - Arauco': 'https://github.com/JacoLucas/producaodiaria/raw/main/Produção_Diária_Obra_Arauco.xlsx',
    'Obra 004 - Duplicação PR-151': 'https://github.com/JacoLucas/producaodiaria/raw/main/Produção_Diária_Obra_PG_004.xlsx'
}

# Função para baixar e ler o arquivo Excel do GitHub com controle de exceção
def get_data_from_github(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        df = pd.read_excel(BytesIO(response.content))
        df = df.replace(regex=r'[^0-9.]', value=0)  # Substituir caracteres especiais por 0
        return df
    except requests.exceptions.RequestException as e:
        print(f"Erro ao carregar o arquivo: {e}")
        return pd.DataFrame()  # Retorna um DataFrame vazio em caso de erro

# Layout da página
app.layout = html.Div([
    html.Div([
        html.Img(src=image_url, style={'position': 'absolute', 'top': '10px', 'right': '10px', 'width': '220px', 'height': '180px'})
    ]),
    html.H1('Análise da Produção Diária'),
    
    ######### ATUALIZAR SEMPRE #########
    html.H3('Atualizado dia 22/01/25 - 14:18'), 
    ######### ATUALIZAR SEMPRE #########

    dcc.Dropdown(
        id='obra-dropdown',
        options=[{'label': name, 'value': name} for name in file_urls.keys()],
        value='Obra 500 - Arauco',
        style={'width': '75%'}
    ),
    dcc.Dropdown(
        id='month-dropdown',
        options=[],  # Será preenchido dinamicamente
        value=None,
        style={'width': '75%'}
    ),
    dcc.Dropdown(
        id='service-dropdown',
        options=[],  # Será preenchido dinamicamente
        multi=True,
        value=[],
        style={'width': '75%'}
    ),
    html.H2('Produção Diária'),
    dcc.Graph(id='line-chart'),
    html.H2('Produção Acumulada'),
    dcc.Graph(id='bar-chart'),
    html.Div(id='table-container', style={'width': '60%', 'margin': '0 auto'})
])

# Callback para carregar os dados da obra selecionada
@app.callback(
    [Output('month-dropdown', 'options'),
     Output('service-dropdown', 'options'),
     Output('month-dropdown', 'value'),
     Output('service-dropdown', 'value')],
    [Input('obra-dropdown', 'value')]
)
def update_dropdowns(obra_name):
    url = file_urls[obra_name]
    df = get_data_from_github(url)
    
    # Verificar se o DataFrame está vazio
    if df.empty:
        return [], [], None, []

    # Dicionário de rótulos para atividades
    if obra_name == 'Obra 500 - Arauco':
        activity_labels = {
            'prod diaria 1': 'Escavação (m³)',
            'prod diaria 2': 'Aterro (m³)',
            'prod diaria 3': 'Tubo em Concreto (m)',
            'prod diaria 4': 'Blocos de Concreto (m²)',
            'prod diaria 5': 'Sarjeta de Concreto (m)',
            'prod diaria 6': 'SMC (m³)',
            'prod diaria 7': 'Drenos Longitudinais (m)',
            'prod diaria 8': 'CBUQ / Binder (m³)',
            'prod diaria 9': 'Supressão Vegetal (m²)'
        }
    else:
        activity_labels = {
            'prod diaria 1': 'Escavação (m³)',
            'prod diaria 2': 'Aterro (m³)',
            'prod diaria 3': 'Macadame (m³)',
            'prod diaria 4': 'Brita graduada (m³)',
            'prod diaria 5': 'C.B.U.Q. (ton.)',
            'prod diaria 6': 'Muro de Escama (m²)',
            'prod diaria 7': 'Aterro com Fita Metálica (m³)',
            'prod diaria 8': 'Barreira New Jersey (m)',
            'prod diaria 9': ''
        }

    # Converter a coluna 'Dias' para datetime e extrair os meses
    df['Dias'] = pd.to_datetime(df['Dias'])
    df['Mês'] = df['Dias'].dt.to_period('M')

    # Obter os meses únicos presentes na coluna 'Dias'
    unique_months = sorted(df['Mês'].unique())

    month_options = [{'label': str(month), 'value': str(month)} for month in unique_months]
    service_options = [{'label': label, 'value': label} for label in activity_labels.values()]
    
    return month_options, service_options, str(unique_months[0]), list(activity_labels.values())

# Callback para atualizar os gráficos e a tabela com base nos filtros
@app.callback(
    [Output('line-chart', 'figure'),
     Output('bar-chart', 'figure'),
     Output('table-container', 'children')],
    [Input('month-dropdown', 'value'),
     Input('service-dropdown', 'value'),
     Input('obra-dropdown', 'value')]
)
def update_charts(selected_month, selected_services, obra_name):
    url = file_urls[obra_name]
    df = get_data_from_github(url)
    
    # Verificar se o DataFrame está vazio
    if df.empty:
        return {}, {}, None

    # Dicionário de rótulos para atividades
    if obra_name == 'Obra 500 - Arauco':
        activity_labels = {
            'prod diaria 1': 'Escavação (m³)',
            'prod diaria 2': 'Aterro (m³)',
            'prod diaria 3': 'Tubo em Concreto (m)',
            'prod diaria 4': 'Blocos de Concreto (m²)',
            'prod diaria 5': 'Sarjeta de Concreto (m)',
            'prod diaria 6': 'SMC (m³)',
            'prod diaria 7': 'Drenos Longitudinais (m)',
            'prod diaria 8': 'CBUQ / Binder (m³)',
            'prod diaria 9': 'Supressão Vegetal (m²)'
        }
    else:
        activity_labels = {
            'prod diaria 1': 'Escavação (m³)',
            'prod diaria 2': 'Aterro (m³)',
            'prod diaria 3': 'Macadame (m³)',
            'prod diaria 4': 'Brita graduada (m³)',
            'prod diaria 5': 'C.B.U.Q. (ton.)',
            'prod diaria 6': 'Muro de Escama (m²)',
            'prod diaria 7': 'Aterro com Fita Metálica (m³)',
            'prod diaria 8': 'Barreira New Jersey (m)',
            'prod diaria 9': ''
        }

    required_columns = list(activity_labels.keys())
    for col in required_columns:
        if col not in df.columns:
            df[col] = 0

    # Converter a coluna 'Dias' para datetime e extrair os meses
    df['Dias'] = pd.to_datetime(df['Dias'])
    df['Mês'] = df['Dias'].dt.to_period('M')

    # Verificar se as colunas de produção acumulada existem e têm dados
    for i in range(1, 9):
        if f'prev acum {i}' not in df.columns or df[f'prev acum {i}'].isna().all():
            df[f'prev acum {i}'] = 0  # Adicionar coluna com valor 0 se não existir ou estiver vazia
        if f'prod acum {i}' not in df.columns or df[f'prod acum {i}'].isna().all():
            df[f'prod acum {i}'] = 0  # Adicionar coluna com valor 0 se não existir ou estiver vazia

    # Transformar dados em formato longo para facilitar a manipulação
    df_long = df.melt(id_vars=['Dias', 'Mês'], value_vars=required_columns, var_name='Serviço', value_name='Produção')
    df_long['Serviço'] = df_long['Serviço'].map(activity_labels)
    
    # Adicionar colunas de produção acumulada ao DataFrame longo
    for i in range(1, 9):
        df_long[f'Prev Acum {i}'] = df[f'prev acum {i}']
        df_long[f'Prod Acum {i}'] = df[f'prod acum {i}']

    df_long = df_long.fillna(0)

    # Obter o total previsto para cada serviço (última célula não nula da coluna 'Prev Acum')
    totals = {}
    for i in range(1, 9):
        coluna = f'prev acum {i}'
        total_prev = df[coluna].dropna().replace(regex=r'[^0-9.]', value=0)  # Substituir caracteres especiais por 0
        if not total_prev.empty:
            totals[activity_labels[f'prod diaria {i}']] = float(total_prev.iloc[-1])  # Garantir que o total é float

    # Função para calcular a porcentagem relativa prevista para o mês
    def calculate_monthly_percentage(df, total_column, total):
        last_day_of_month = df['Dias'].max()
        monthly_total = df.loc[df['Dias'] == last_day_of_month, total_column].values[0]
    
        # Verificar se total pode ser convertido para float
        try:
            total = float(total)
        except (ValueError, TypeError):
            total = 0.0  # Transformar células nulas e caracteres especiais em zero (float)
    
        if total == 0:
            return 0
        return (monthly_total / total) * 100

    # Função para obter o valor acumulado mensal
    def get_monthly_value(df, total_column):
        last_day_of_month = df['Dias'].max()
        monthly_total = df.loc[df['Dias'] == last_day_of_month, total_column].values[0]
        return monthly_total

    selected_period = pd.Period(selected_month, 'M')
    df_filtered = df_long[df_long['Mês'] == selected_period]

    df_filtered['Obs'] = df['Obs']
    df_filtered['Obs'] = df_filtered['Obs'].fillna(0)
    
    # Atualizar o gráfico de linhas
    line_fig = px.line(df_filtered[df_filtered['Serviço'].isin(selected_services)], 
                       x='Dias', y='Produção', color='Serviço', 
                       title=f'{obra_name} {selected_month}',
                       labels={'Produção': 'Produção', 'Dias': 'Período', 'Serviço': 'Serviço'}
                      )
    # Adicionando scatter plot para os pontos onde Obs != 0
    scatter_points = go.Scatter(
        x=df_filtered[df_filtered['Obs'] != 0]['Dias'],
        y=[0] * len(df_filtered[df_filtered['Obs'] != 0]),
        mode='markers',
        name='Observação',
        marker=dict(color='red', size=10),
        text=df_filtered[df_filtered['Obs'] != 0]['Obs'],
        textposition='top center',
        hovertext=df_filtered[df_filtered['Obs'] != 0]['Obs']
    )

    # Atualizando o layout do gráfico
    line_fig.add_trace(scatter_points)
    line_fig.update_layout(
        xaxis_title=f'{selected_month}',
        xaxis=dict(
            tickmode='linear',
            dtick='D1',
            tickformat='%d'
        ),
        yaxis=dict(
            range=[0, max(df_filtered[['Produção']].max()) + 5]
        )
    )

    # Atualizar o gráfico de barras
    data = []
    table_data = []

    # Verificar e inicializar colunas ausentes
    for i in range(1, 9):
        prev_acum_column = f'Prev Acum {i}'
        prod_acum_column = f'Prod Acum {i}'
        if prev_acum_column not in df.columns:
            df[prev_acum_column] = 0
        if prod_acum_column not in df.columns:
            df[prod_acum_column] = 0

    for service_label in selected_services:
        service_index = [key for key, value in activity_labels.items() if value == service_label]
        
        # Verificar se o serviço está na lista
        if not service_index:
            print(f"Service '{service_label}' not found in activity_labels.")
            continue

        service_index = service_index[0]
        prev_acum_column = f'Prev Acum {service_index.split()[-1]}'
        prod_acum_column = f'Prod Acum {service_index.split()[-1]}'
        
        # Garantir que as colunas estão no DataFrame
        if prev_acum_column not in df.columns or prod_acum_column not in df.columns:
            print(f"Columns '{prev_acum_column}' or '{prod_acum_column}' not found in DataFrame.")
            continue

        total = totals[service_label]
        prev_acum_value = get_monthly_value(df_filtered, prev_acum_column)
        prod_acum_value = get_monthly_value(df_filtered, prod_acum_column)
        
        data.append({'Serviço': service_label, 'Tipo': 'Total Previsto', 'Valor': 100})
        data.append({'Serviço': service_label, 'Tipo': 'Previsto Acumulado', 'Valor': calculate_monthly_percentage(df_filtered, prev_acum_column, total)})
        data.append({'Serviço': service_label, 'Tipo': 'Realizado Acumulado', 'Valor': calculate_monthly_percentage(df_filtered, prod_acum_column, total)})

        table_data.append({'Serviço': service_label, 'Total Previsto': total, 
                        'Previsto Acumulado': prev_acum_value, 'Realizado Acumulado': prod_acum_value})

    df_chart = pd.DataFrame(data)



    bar_fig = px.bar(df_chart, x='Serviço', y='Valor', color='Tipo', barmode='group', 
                     title=f'{obra_name} {selected_month}', 
                     labels={'Valor': 'Porcentagem (%)', 'Serviço': 'Serviço'},
                     color_discrete_map={
                         'Total Previsto': '#FFCC00',
                         'Previsto Acumulado': '#CC0033',
                         'Realizado Acumulado': '#0066CC'
                     })

    # Configuração para ocultar 'Total Previsto' inicialmente 
    for trace in bar_fig.data: 
        if trace.name == 'Total Previsto': 
            trace.visible = 'legendonly'
    
    bar_fig.update_layout(
        xaxis= dict(
            tickfont= dict(size= 14))
    )

    # Função para converter valores para float, tratando células nulas e caracteres especiais
    def safe_float_conversion(value):
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    
    # Criar a tabela com os valores reais e bordas nas células
    table_header = [html.Thead(html.Tr([html.Th('Serviço'), html.Th('Total Previsto'), 
                                        html.Th('Previsto Acumulado'), html.Th('Realizado Acumulado')]))]
    table_body = [html.Tbody([
        html.Tr([html.Td(row['Serviço'], style={'border': '1px solid black'}), 
                 html.Td(f"{safe_float_conversion(row['Total Previsto']):.4f}", style={'border': '1px solid black'}), 
                 html.Td(f"{safe_float_conversion(row['Previsto Acumulado']):.4f}", style={'border': '1px solid black'}), 
                 html.Td(f"{safe_float_conversion(row['Realizado Acumulado']):.4f}", style={'border': '1px solid black'})])
        for row in table_data
    ])]
    
    table = html.Table(table_header + table_body, style={'width': '100%', 'textAlign': 'center', 'borderCollapse': 'collapse'})
    return line_fig, bar_fig, table

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
