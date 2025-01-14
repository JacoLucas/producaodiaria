import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
import requests
from io import BytesIO
import os

app = dash.Dash(__name__)
app.title = 'Análise de Produção Diária'

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

# Dropdown para selecionar a obra
app.layout = html.Div([
    html.H1('Análise da Produção Diária'),
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
    dcc.Graph(id='line-chart'),
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
    
    # Converter a coluna 'Dias' para datetime e extrair os meses
    df['Dias'] = pd.to_datetime(df['Dias'])
    df['Mês'] = df['Dias'].dt.to_period('M')

    # Obter os meses únicos presentes na coluna 'Dias'
    unique_months = sorted(df['Mês'].unique())

    # Dicionário de rótulos para atividades
    if obra_name == 'Obra 500 - Arauco':
        activity_labels = {
            'prod diaria 1': 'Corte (m³)',
            'prod diaria 2': 'Aterro (m³)',
            'prod diaria 3': '',
            'prod diaria 4': ' ',
            'prod diaria 5': '  '
        }
    else:
        activity_labels = {
            'prod diaria 1': 'Corte (m³)',
            'prod diaria 2': 'Aterro (m³)',
            'prod diaria 3': 'Rachão (m³)',
            'prod diaria 4': 'Rocha Detonada (ton.)',
            'prod diaria 5': 'Aplicação Brita 3/4'
        } 

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
    
    # Converter a coluna 'Dias' para datetime e extrair os meses
    df['Dias'] = pd.to_datetime(df['Dias'])
    df['Mês'] = df['Dias'].dt.to_period('M')

    # Dicionário de rótulos para atividades
    if obra_name == 'Obra 500 - Arauco':
        activity_labels = {
            'prod diaria 1': 'Corte (m³)',
            'prod diaria 2': 'Aterro (m³)',
            'prod diaria 3': '',
            'prod diaria 4': ' ',
            'prod diaria 5': '  '
        }
    else:
        activity_labels = {
            'prod diaria 1': 'Corte (m³)',
            'prod diaria 2': 'Aterro (m³)',
            'prod diaria 3': 'Rachão (m³)',
            'prod diaria 4': 'Rocha Detonada (ton.)',
            'prod diaria 5': 'Aplicação Brita 3/4'
        } 

    # Verificar se as colunas de produção acumulada existem e têm dados
    for i in range(1, 6):
        if f'prev acum {i}' not in df.columns or df[f'prev acum {i}'].isna().all():
            df[f'prev acum {i}'] = 0  # Adicionar coluna com valor 0 se não existir ou estiver vazia

        if f'prod acum {i}' not in df.columns or df[f'prod acum {i}'].isna().all():
            df[f'prod acum {i}'] = 0  # Adicionar coluna com valor 0 se não existir ou estiver vazia

    # Transformar dados em formato longo para facilitar a manipulação
    df_long = df.melt(id_vars=['Dias', 'Mês'], value_vars=list(activity_labels.keys()), 
                      var_name='Serviço', value_name='Produção')
    df_long['Serviço'] = df_long['Serviço'].map(activity_labels)
    
    # Adicionar colunas de produção acumulada ao DataFrame longo
    for i in range(1, 6):
        df_long[f'Prev Acum {i}'] = df[f'prev acum {i}']
        df_long[f'Prod Acum {i}'] = df[f'prod acum {i}']

    df_long = df_long.fillna(0)
    
    # Obter o total previsto para cada serviço (última célula não nula da coluna 'Prev Acum')
    totals = {}
    for i in range(1, 6):
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
    
    # Atualizar o gráfico de linhas
    line_fig = px.line(df_filtered[df_filtered['Serviço'].isin(selected_services)], 
                       x='Dias', y='Produção', color='Serviço', 
                       title=f'Produção Diária {obra_name} {selected_month}',
                       labels={'Produção': 'Produção', 'Dias': 'Período', 'Serviço': 'Serviço'})

    # Atualizar o gráfico de barras
    data = []
    table_data = []
    for service_label in selected_services:
        service_index = [key for key, value in activity_labels.items() if value == service_label][0]
        prev_acum_column = f'Prev Acum {service_index.split()[-1]}'
        total = totals[service_label]
        prev_acum_value = get_monthly_value(df_filtered, prev_acum_column)
        
        prod_acum_column = f'Prod Acum {service_index.split()[-1]}'
        prod_acum_value = get_monthly_value(df_filtered, prod_acum_column)
        
        # Dados para o gráfico de barras em porcentagem relativa
        data.append({'Serviço': service_label, 'Tipo': 'Total Previsto', 'Valor': 100})
        data.append({'Serviço': service_label, 'Tipo': 'Previsto Acumulado', 'Valor': calculate_monthly_percentage(df_filtered, prev_acum_column, total)})
        data.append({'Serviço': service_label, 'Tipo': 'Realizado Acumulado', 'Valor': calculate_monthly_percentage(df_filtered, prod_acum_column, total)})

        # Dados para a tabela com valores reais
        table_data.append({'Serviço': service_label, 'Total Previsto': total, 
                           'Previsto Acumulado': prev_acum_value, 'Realizado Acumulado': prod_acum_value})
    
    df_chart = pd.DataFrame(data)
    bar_fig = px.bar(df_chart, x='Serviço', y='Valor', color='Tipo', barmode='group', 
                     title=f'Produção Acumulada {obra_name} {selected_month}', 
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
