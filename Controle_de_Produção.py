import os
import re
import glob
import pandas as pd
import numpy as np
from dash import Dash, html, dcc, Output, Input
import plotly.express as px

#### LOAD FROM GITHUB REPOSITORIES ####

def load_production_files():
    directory = os.path.dirname(os.path.abspath(__file__))
    files = glob.glob(os.path.join(directory, "Produção_Diária_Obra_*.xlsx"))
    data = {}
    for file in files:
        obra_id = os.path.basename(file).split('_')[-1].split('.')[0]
        df = pd.read_excel(file)
        df['Dias'] = pd.to_datetime(df['Dias'])
        df['Mes'] = df['Dias'].dt.to_period('M')
        df['Semana'] = df['Dias'].dt.to_period('W')
        df['Obra'] = f'Obra {obra_id}'
        print(f"{file} - {len(df)} linhas")
        data[obra_id] = df
    return data

production_data = load_production_files()

app = Dash(__name__)
server = app.server

activity_labels = {
    'prod diaria 1': 'Corte (m³)',
    'prod diaria 2': 'Aterro (m³)',
    'prod diaria 3': 'Rachão (m³)',
    'prod diaria 4': 'Caixas e PVs (un)',
    'prod diaria 5': 'Escavação de Drenagem'
}

app.layout = html.Div([
    html.H1("Acompanhamento da Produção Diária"),
    html.Div([
        dcc.Dropdown(
            id='atividade-dropdown',
            options=[{'label': label, 'value': key} for key, label in activity_labels.items()] + [{'label': 'Todos os Serviços', 'value': 'todas'}],
            value='todas',
            clearable=False,
            style={'width': '100%'}
        ),
    ], style={'width': '48%', 'display': 'inline-block'}),
    html.Div([
        dcc.Dropdown(
            id='mes-dropdown',
            clearable=False,
            style={'width': '100%'}
        ),
    ], style={'width': '48%', 'display': 'inline-block'}),
    html.Div([
        dcc.Dropdown(
            id='obra-dropdown',
            options=[{'label': f'Obra {obra_id}', 'value': obra_id} for obra_id in production_data.keys()] + [{'label': 'Todas as Obras', 'value': 'todas'}],
            value='todas',
            clearable=False,
            style={'width': '100%'}
        ),
    ], style={'width': '48%', 'display': 'inline-block'}),
    html.Div([
        dcc.Dropdown(
            id='semana-dropdown',
            clearable=False,
            style={'width': '100%'}
        ),
    ], style={'width': '48%', 'display': 'inline-block'}),
    html.Div([
        dcc.Graph(id='grafico-prod-diaria', style={'display': 'inline-block', 'width': '99%'}),
    ]),
    dcc.Graph(id='grafico-comparativo-mensal'),
    html.Div(id='tabela-valores')
])

@app.callback(
    [Output('mes-dropdown', 'options'),
     Output('semana-dropdown', 'options')],
    [Input('obra-dropdown', 'value'),
     Input('mes-dropdown', 'value')]
)
def update_dropdowns(selected_obra, selected_mes):
    if selected_obra == 'todas':
        combined_df = pd.concat(production_data.values()) if production_data else pd.DataFrame()
    else:
        combined_df = production_data.get(selected_obra, pd.DataFrame())

    if not combined_df.empty and 'Mes' in combined_df.columns:
        meses = [{'label': str(mes), 'value': str(mes)} for mes in combined_df['Mes'].unique()]
    else:
        meses = []

    if not combined_df.empty and 'Mes' in combined_df.columns:
        filtered_df = combined_df[combined_df['Mes'].astype(str) == selected_mes]
        semanas = [{'label': 'Todas as Semanas', 'value': 'todas'}] + [{'label': str(semana), 'value': str(semana)} for semana in filtered_df['Semana'].unique()]
    else:
        semanas = []

    return meses, semanas

@app.callback(
    [Output('grafico-prod-diaria', 'figure'),
     Output('grafico-comparativo-mensal', 'figure'),
     Output('tabela-valores', 'children')],
    [Input('atividade-dropdown', 'value'),
     Input('obra-dropdown', 'value'),
     Input('mes-dropdown', 'value'),
     Input('semana-dropdown', 'value')]
)
def update_graphs_and_table(selected_atividade, selected_obra, selected_mes, selected_semana):
    if selected_obra == 'todas':
        filtered_data = pd.concat(production_data.values()) if production_data else pd.DataFrame()
    else:
        filtered_data = production_data.get(selected_obra, pd.DataFrame())

    if filtered_data.empty or 'Mes' not in filtered_data.columns:
        return {}, {}, "Nenhum dado disponível"

    filtered_df = filtered_data[filtered_data['Mes'].astype(str) == selected_mes]
    if filtered_df.empty:
        return {}, {}, "Nenhum dado disponível"
    
    if selected_semana != 'todas':
        filtered_df = filtered_df[filtered_df['Semana'].astype(str) == selected_semana]
        if filtered_df.empty:
            return {}, {}, "Nenhum dado disponível"

    if selected_atividade == 'todas':
        prod_diaria_data = filtered_df.melt(id_vars=['Dias', 'Mes', 'Obra'], value_vars=[key for key in activity_labels.keys()],
                                            var_name='Atividade', value_name='Produção')
    else:
        prod_diaria_data = filtered_df.melt(id_vars=['Dias', 'Mes', 'Obra'], value_vars=[selected_atividade],
                                            var_name='Atividade', value_name='Produção')
    
    prod_diaria_data['Atividade'] = prod_diaria_data['Atividade'].map(activity_labels)

    if selected_obra == 'todas':
        prod_diaria_data['Obra_Serviço'] = prod_diaria_data['Obra'] + ' - ' + prod_diaria_data['Atividade']
    else:
        prod_diaria_data['Obra_Serviço'] = prod_diaria_data['Atividade']

    fig_prod_diaria = px.line(
        prod_diaria_data, x='Dias', y='Produção', color='Obra_Serviço', line_group='Obra',
        title='Produção Diária por Serviço', markers=True,
        hover_data={"Obra": False, "Dias": False, "Obra_Serviço": False}
    )
    fig_prod_diaria.update_traces(connectgaps=False)

    comparacao_cols = {
        'prod acum 1': 'Corte (m³)',
        'prod acum 2': 'Aterro (m³)',
        'prod acum 3': 'Rachão (ton.)',
        'prod acum 4': 'Caixas e PVs (un)',
        'prod acum 5': 'Escavação de Drenagem (m³)',
        'prev acum 1': 'Previsto Corte (m³)',
        'prev acum 2': 'Previsto Aterro (m³)',
        'prev acum 3': 'Previsto Rachão (ton.)',
        'prev acum 4': 'Previsto Caixas e PVs (un)',
        'prev acum 5': 'Previsto Escavação de Drenagem (m³)'
    }

    if selected_obra == 'todas':
        combined_summary = pd.concat([df.groupby('Mes').last().reset_index() for df in production_data.values()])
    else:
        combined_summary = production_data[selected_obra]

    final_prev_values = {key: combined_summary[key].dropna().iloc[-1] if key in combined_summary.columns and not combined_summary[key].dropna().empty else 0 for key in comparacao_cols if key.startswith('prev acum')}
    final_real_values = {key: combined_summary[key].dropna().iloc[-1] if key in combined_summary.columns and not combined_summary[key].dropna().empty else 0 for key in comparacao_cols if key.startswith('prod acum')}

    # Adicionar verificação de zero
    normalized_real_values = {key: (value / final_prev_values[key.replace('prod', 'prev')]) * 100 if key.replace('prod', 'prev') in final_prev_values and final_prev_values[key.replace('prod', 'prev')] != 0 else 0 for key, value in final_real_values.items()}
    normalized_prev_values = {key: 100 for key in final_prev_values.keys()}
    final_prev_df = pd.DataFrame([ {'Mes': selected_mes, 'Tipo': 'Previsto', 'Produção': value, 'Serviço': key.split()[2]}
                                    for key, value in normalized_prev_values.items()
                                ])
    final_real_df = pd.DataFrame([ {'Mes': selected_mes, 'Tipo': 'Realizado', 'Produção': value, 'Serviço': key.split()[2]}
                                  for key, value in normalized_real_values.items()
                                ])
    final_df = pd.concat([final_prev_df, final_real_df], ignore_index=True)
    final_df['Produção (%)'] = final_df['Produção']
    final_df = pd.concat([final_prev_df, final_real_df], ignore_index=True)

    # Adicionar coluna de porcentagem relativa
    final_df['Acumulado Previsto'] = final_df.apply(
        lambda row: (row['Produção'] / final_prev_values[f'prev acum {row["Serviço"]}']) * 100 if row['Tipo'] == 'Previsto' and f'prev acum {row["Serviço"]}' in final_prev_values and final_prev_values[f'prev acum {row["Serviço"]}'] != 0 else row['Produção'],
        axis=1
    )

    serviço_labels = {
        '1': 'Corte (m³)',
        '2': 'Aterro (m³)',
        '3': 'Rachão (ton.)',
        '4': 'Tubos e Aduelas (un)',
        '5': 'Caixas e PVs (un)'
    }
    final_df['Serviço'] = final_df['Serviço'].map(serviço_labels)

    # Definir a ordem das barras para trazer 'Realizado' para frente de 'Previsto'
    final_df['Tipo'] = pd.Categorical(final_df['Tipo'], categories=['Realizado', 'Previsto'], ordered=True)

    final_df['Total Previsto'] = final_df['Produção']

    # Filtrar para remover serviços com "Realizado", "prod acum" ou "prev acum" igual a zero
    final_df = final_df[~((final_df['Tipo'] == 'Realizado') & (final_df['Produção'] == 0) & 
                         (final_df['Serviço'].map(lambda x: final_real_values[f'prod acum {x.split()[1]}'] == 0) &
                          final_df['Serviço'].map(lambda x: final_prev_values[f'prev acum {x.split()[1]}'] == 0)))]

    # Alterar as cores das barras
    color_discrete_map = {'Total Previsto': '#FF0000', 'Realizado': '#0099FF', 'Acumulado Previsto': '#00CC00'} 
    
    # Ajustar o DataFrame para o gráfico de barras
    final_df_realizado = final_df[final_df['Tipo'] == 'Realizado'].copy()
    final_df_previsto = final_df[final_df['Tipo'] == 'Previsto'].copy()
    final_df_previsto['Status:'] = 'Total Previsto'
    final_df_previsto_relative = final_df[final_df['Tipo'] == 'Previsto'].copy()
    final_df_previsto_relative['Status:'] = 'Acumulado Previsto'

    final_df_final = pd.concat([final_df_realizado, final_df_previsto, final_df_previsto_relative], ignore_index=True)
    final_df_final['Status:'].fillna('Realizado', inplace=True)  # Adicionar 'Realizado' para dados NaN em 'Status:'
    final_df_final['Produção (%)'] = final_df_final.apply(
        lambda row: row['Acumulado Previsto'] if row['Status:'] == 'Acumulado Previsto' else row['Total Previsto'],
        axis=1
    )

    # Organizar final_df_final para valores de Value crescentes
    final_df_final = final_df_final.sort_values(by='Produção (%)', ascending=True)


    print(final_df_final)

    if selected_obra != 'todas':
        # Criar gráfico de barras
        fig_comparativo = px.bar(
            final_df_final,
            x='Serviço',
            y='Produção (%)',
            color='Status:',
            barmode='group',
            title='Comparação de Produção Acumulada e Porcentagem Relativa'
        )

        fig_comparativo.update_layout(bargroupgap=0.1)
    else:
        fig_comparativo = {}

    # Criar a tabela com os valores numéricos finais de Realizado e Previsto, apenas se uma obra específica for selecionada
    if selected_obra != 'todas':
        tabela_valores = pd.DataFrame({
            'Serviço': [serviço_labels[key.split()[2]] for key in final_prev_values.keys()],
            'Previsto': [value for value in final_prev_values.values()],
            'Realizado': [final_real_values[key] for key in final_real_values.keys()]
        })

        tabela_html = html.Table([
            html.Thead(html.Tr([html.Th(col, style={'text-align': 'center', 'border': '1px solid black'}) for col in tabela_valores.columns])),
            html.Tbody([
                html.Tr([
                    html.Td(tabela_valores.iloc[i][col], style={'text-align': 'center', 'border': '1px solid black'}) for col in tabela_valores.columns
                ]) for i in range(len(tabela_valores))
            ])
        ], style={'border-collapse': 'collapse', 'width': '70%', 'margin': 'auto'})
    else:
        tabela_html = "Nenhum dado disponível para 'Todas as Obras'"

    return fig_prod_diaria, fig_comparativo, tabela_html


if __name__ == '__main__':
    app.run_server(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 8050)))
