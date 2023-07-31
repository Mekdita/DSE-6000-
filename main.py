import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import plotly.express as px
from dash.dependencies import Input, Output
from census import Census
import plotly.graph_objects as go

from preprocessing import data
# from dash import Dash, dcc, html


#####################################  Cleaning steps ############################################################################


# data = pd.read_csv(r'https://storage.googleapis.com/assignment-data/Point_in_Time_Estimates_of_Homelessness_in_the_US_by_State.csv')

# data.rename(columns={'count_type': 'homeless_type'}, inplace=True)
# data = data[data['state'] != 'MP']
# data = data[data['state'] != 'Total']
# data['count'] = data['count'].astype(int)
# data = data.dropna()
#########


# population from census

population_table = pd.DataFrame()
for i in range(2009, 2019):
    c = Census("52b7c26667eed84927ca68b61e8cd4b3ff00f5f0", year=i)

    df = pd.DataFrame(c.acs5.state('B01001_001E', Census.ALL))
    df['year'] = i
    population_table = population_table.append(df)

population_table.rename(columns={'B01001_001E': 'population'}, inplace=True)

state_codes = {
    'WA': '53', 'DE': '10', 'DC': '11', 'WI': '55', 'WV': '54', 'HI': '15', 'FL': '12', 'WY': '56', 'PR': '72', 'NJ': '34', 'NM': '35', 'TX': '48',
    'LA': '22', 'NC': '37', 'ND': '38', 'NE': '31', 'TN': '47', 'NY': '36', 'PA': '42', 'AK': '02', 'NV': '32', 'NH': '33', 'VA': '51', 'CO': '08',
    'CA': '06', 'AL': '01', 'AR': '05', 'VT': '50', 'IL': '17', 'GA': '13', 'IN': '18', 'IA': '19', 'MA': '25', 'AZ': '04', 'ID': '16', 'CT': '09',
    'ME': '23', 'MD': '24', 'OK': '40', 'OH': '39', 'UT': '49', 'MO': '29', 'MN': '27', 'MI': '26', 'RI': '44', 'KS': '20', 'MT': '30', 'MS': '28',
    'SC': '45', 'KY': '21', 'OR': '41', 'SD': '46'}
state_codes = {v: k for k, v in state_codes.items()}
population_table['state'] = population_table['state'].map(state_codes)


##############################################


pivoted_data = data.pivot_table(values='count', index=['year', 'state'],   columns='homeless_type',    aggfunc=['sum'],   margins=False)
pivoted_data.columns = pivoted_data.columns.to_series().str.join('')
pivoted_data.columns = pivoted_data.columns.str.replace("sum", "")

pivoted_data.reset_index(inplace=True)

states_dictionary = pd.read_csv(
    r'https://raw.githubusercontent.com/cphalpert/census-regions/master/us%20census%20bureau%20regions%20and%20divisions.csv')


pivoted_data = pd.merge(pivoted_data, states_dictionary, left_on='state', right_on='State Code', how='left')
pivoted_data = pd.merge(pivoted_data, population_table, left_on=['year', 'state'], right_on=['year', 'state'], how='left')


pivoted_data['Homelessness Rate'] = pivoted_data['Overall Homeless'] / pivoted_data['population']
pivoted_data['Homelessness Rate '] = pivoted_data['Homelessness Rate'].apply(lambda x: '{:.2%}'.format(x))


def state_level_summary(selected_year=2018):
    pivoted_data_sliced = pivoted_data[pivoted_data['year'].isin([selected_year])].reset_index()
    yoy_homeless = pd.merge(pivoted_data_sliced.groupby('Region').sum('Overall Homeless')['Overall Homeless'],
                            pivoted_data[pivoted_data['year'].isin([selected_year-1])][['Region', 'Overall Homeless']
                                                                                       ].groupby('Region').sum('Overall Homeless')['Overall Homeless'],
                            how='left',
                            on='Region').rename(columns={'Overall Homeless_y': 'Prior Year Overall Homeless',
                                                         'Overall Homeless_x': 'Overall Homeless during {x}'.format(x=selected_year)})

    yoy_homeless['Overall Homeless L4Y'] = pivoted_data[pivoted_data['year'].isin([selected_year-1, selected_year-2, selected_year-3, selected_year-4])][[
        'Region', 'Overall Homeless']].groupby('Region').sum('Overall Homeless')['Overall Homeless']/4
    yoy_homeless['Percent change vs Baseline'] = (
        yoy_homeless['Overall Homeless during {x}'.format(x=selected_year)] / yoy_homeless['Overall Homeless L4Y'])-1
    yoy_homeless['Overall Homeless Distribution'] = yoy_homeless['Overall Homeless during {x}'.format(
        x=selected_year)]/yoy_homeless['Overall Homeless during {x}'.format(x=selected_year)].sum()
    yoy_homeless[['Overall Homeless during {x}'.format(x=selected_year), 'Prior Year Overall Homeless']] = yoy_homeless[[
        'Overall Homeless during {x}'.format(x=selected_year), 'Prior Year Overall Homeless']].astype(int)

    yoy_homeless['Percent change vs prior Year'] = (yoy_homeless['Overall Homeless during {x}'.format(
        x=selected_year)]/yoy_homeless['Prior Year Overall Homeless']) - 1

    yoy_homeless['Percent change vs prior Year'] = yoy_homeless['Percent change vs prior Year'].apply(lambda x: '{:.2%}'.format(x))
    yoy_homeless['Overall Homeless Distribution'] = yoy_homeless['Overall Homeless Distribution'].apply(lambda x: '{:.2%}'.format(x))
    yoy_homeless['Percent change vs Baseline'] = yoy_homeless['Percent change vs Baseline'].apply(lambda x: '{:.2%}'.format(x))

    yoy_homeless = yoy_homeless[['Overall Homeless Distribution', 'Overall Homeless during {x}'.format(
        x=selected_year), 'Percent change vs prior Year', 'Percent change vs Baseline']].sort_values(by='Overall Homeless during {x}'.format(x=selected_year),  ascending=False)
    yoy_homeless['Overall Homeless during {x}'.format(
        x=selected_year)] = yoy_homeless['Overall Homeless during {x}'.format(x=selected_year)].apply(lambda x:  f'{x:,}')
    return yoy_homeless


def homeless_count_map(selected_year=2018, count_type='Overall Homeless'):
    fig_2_state = go.Figure(data=go.Choropleth(
        locations=pivoted_data[pivoted_data['year'] == selected_year]['state'],
        z=pivoted_data[pivoted_data['year'] == selected_year][count_type],
        locationmode='USA-states',
        #    colorscale = 'Reds'


        #text=pivoted_data[pivoted_data['year'] == selected_year][count_type],
        marker_line_color='white'  # , customdata=['Overall Homelessness', 'Homelessness Rate ']
    ))

    fig_2_state.update_layout(
        title_text='State-wise distribution of the Homelessness',
        geo_scope='usa', width=800, height=450
    )
    return fig_2_state


avail_beds = pd.DataFrame()
for i in range(2008, 2019, 1):
    df.columns
    df = pd.read_excel(r'https://www.huduser.gov/portal/sites/default/files/xls/2007-2021-HIC-Counts-by-State.xlsx', sheet_name=str(i), skiprows=[0])
    if i == 2013:
        df['Total Year-Round Beds (ES, TH, SH)'] = df['Total Year-Round ES Beds'] + df['Total Year-Round TH Beds'] + df['Total Year-Round SH Beds']

    df.rename(columns={'Total Year-Round Beds (ES,TH,SH)': 'Total Year-Round Beds (ES, TH, SH)', 'Total Year-Round ES Beds': 'Total Year-Round Beds (ES)',
              'Total Year-Round TH Beds': 'Total Year-Round Beds (TH)', 'Total Year-Round SH Beds': 'Total Year-Round Beds (SH)'}, inplace=True)
    df = df[['State', 'Total Year-Round Beds (ES, TH, SH)']]
    df['Year'] = i
    avail_beds = avail_beds.append(df)

data = pd.merge(data, avail_beds, right_on=['Year', 'State'], left_on=['year', 'state'], how='left')  # .rename(columns= )


def beds_availability(selected_state='AR'):
    data_plot = data[(data['year'] >= 2009) & data['homeless_type'].isin(
        ['Sheltered Total Homeless', 'Unsheltered Homeless'])].rename(columns={'homeless_type': 'Homeless Type'})
    fig = px.bar(data_plot[data_plot['state'].isin([selected_state])], x='year', y='count', color='Homeless Type', barmode='stack')
    fig.update_layout(title="Shelter Status and Beds Availability in AR",
                      yaxis_title='Number of Homeless',
                      width=1200, height=600)

    fig.add_scatter(x=data_plot[data_plot['state'].isin([selected_state])]['year'], y=data_plot[data_plot['state'].isin(
        [selected_state])]['Total Year-Round Beds (ES, TH, SH)'], mode='lines', name="Available Beds")
    fig.update_layout({
        'plot_bgcolor': 'rgba(0, 0, 0, 0)',
        'paper_bgcolor': 'rgba(0, 0, 0, 0)',
    },  width=1200, height=600, showlegend=True)
    return fig


def top_10_highest_homeless_count(selected_year=2018,  count_type='Overall Homeless'):
    fig_3_state = px.bar(pivoted_data[pivoted_data['year'] == selected_year].sort_values(by=count_type, ascending=False)[
                         0:10], x=count_type, y="state", orientation='h', title='Top 10 States with Highest Overall Homelessness')  # ,  custom_data =[count_type],)

    fig_3_state.update_layout({
        'plot_bgcolor': 'rgba(0, 0, 0, 0)',
        'paper_bgcolor': 'rgba(0, 0, 0, 0)',
    }, width=450, height=450, colorway=['green'], yaxis={'categoryorder': 'total ascending'})

    fig_3_state.update_traces(marker_color='orange',
                              #   hovertemplate="<br>".join([
                              #       "State: %{x}",
                              #       "{t}: %{customdata[0]}".format(t=count_type)
                              #   ])
                              )
    return fig_3_state


########################### TAB 1 ##################################

def Chronically_Homeless_Prop_Pie(selected_year=2018):
    data_pie_1 = data[data['homeless_type'].isin(['Chronically Homeless', 'Overall Homeless'])].groupby([
        'year', 'homeless_type']).sum('count').reset_index()
    for year in range(2011, 2019):
        Other_type_count = data_pie_1[(data_pie_1['year'] == year) & (data_pie_1['homeless_type'] == 'Overall Homeless')].reset_index(drop=True)[
            'count'][0] - data_pie_1[(data_pie_1['year'] == year) & (data_pie_1['homeless_type'] == 'Chronically Homeless')].reset_index(drop=True)['count'][0]

        df = pd.DataFrame({'year': [year], 'homeless_type': ['Other Homeless Types'],   'count': [Other_type_count]})
        data_pie_1 = data_pie_1.append(df)
    Chronically_Homeless_Prop_fig = px.pie(data_pie_1[(data_pie_1['homeless_type'] != 'Overall Homeless') & (
        data_pie_1['year'] == selected_year)], values='count', names='homeless_type', title='Proportion of Chronically Homeless')

    Chronically_Homeless_Prop_fig.update_layout({'plot_bgcolor': 'rgba(0, 0, 0, 0)', 'paper_bgcolor': 'rgba(0, 0, 0, 0)', }, width=600, height=600)

    return Chronically_Homeless_Prop_fig


def Overall_Homeless_subpop_bar(selected_year=2018):
    data_bar_1 = data[data['homeless_type'].isin(['Homeless Individuals', 'Homeless People in Families'])
                      ].groupby(['year', 'homeless_type']).sum('count').reset_index()
    Chronically_Homeless_Prop_fig = px.bar(data_bar_1[data_bar_1['year'] == selected_year],
                                           x='homeless_type', y='count',  color='homeless_type',  title='Homeless Household Composition')

    Chronically_Homeless_Prop_fig.update_layout({
        'plot_bgcolor': 'rgba(0, 0, 0, 0)',
        'paper_bgcolor': 'rgba(0, 0, 0, 0)',
    }, width=450, height=650, xaxis_title='Homeless Type',
        xaxis={'visible': True, 'showticklabels': False}, showlegend=False)

    return Chronically_Homeless_Prop_fig


def Homeless_by_shelter(selected_year=2018):
    data_pie_2 = data[data['homeless_type'].isin(['Sheltered Total Homeless', 'Unsheltered Homeless'])
                      ].groupby(['year', 'homeless_type']).sum('count').reset_index()
    fig_homeless_by_shelter = px.pie(data_pie_2[data_pie_2['year'] == selected_year], values='count',
                                     names='homeless_type', title='Shelter Status', hole=0.4)
    fig_homeless_by_shelter.update_layout({'plot_bgcolor': 'rgba(0, 0, 0, 0)', 'paper_bgcolor': 'rgba(0, 0, 0, 0)', }, width=450, height=450)
    return fig_homeless_by_shelter


def sheltered_by_shelter_type(selected_year=2018):

    data_pie_2 = data[data['homeless_type'].isin(['Sheltered ES Homeless', 'Sheltered TH Homeless', 'Sheltered SH Homeless'])].groupby([
        'year', 'homeless_type']).sum('count').reset_index()

    fig_sheltered_by_shelter_type = px.pie(data_pie_2[data_pie_2['year'] == selected_year],
                                           values='count', names='homeless_type', title='Shelter Types', hole=0.4)
    fig_sheltered_by_shelter_type.update_layout({'plot_bgcolor': 'rgba(0, 0, 0, 0)', 'paper_bgcolor': 'rgba(0, 0, 0, 0)', }, width=450, height=450)
    return fig_sheltered_by_shelter_type


def Homeless_Type_by_Shelter(selected_year=2018):

    data_bar_3 = data[(data['homeless_type'].isin(['Sheltered SH Homeless Individuals', 'Sheltered SH Homeless People in Families', 'Sheltered ES Homeless Individuals', 'Sheltered ES Homeless People in Families', 'Sheltered TH Homeless Individuals', 'Sheltered TH Homeless People in Families'
                                                   ])) & (data['year'] == selected_year)].reset_index(drop=True)

    data_bar_3['Shelter Type'] = data_bar_3['homeless_type'].apply(lambda x: x.split()[1])
    data_bar_3['Homeless Category'] = data_bar_3['homeless_type'].apply(lambda x: x.split()[len(x.split())-2] + ' ' + x.split()[len(x.split())-1])

    data_bar_3['Homeless Category'] = data_bar_3['Homeless Category'].apply(
        lambda x: 'Homeless Individuals' if x == 'Homeless Individuals' else 'Homeless people in familes')

    data_bar_3 = data_bar_3.groupby(['year', 'homeless_type', 'Shelter Type', 'Homeless Category']).sum('count').reset_index()

    fig_Homeless_Type_by_Shelter = px.bar(data_bar_3.sort_values(by='count', ascending=False), x="Shelter Type", color="Homeless Category",
                                          y='count',
                                          title="Homeless Household Composition by Shelter Type",
                                          barmode='group',
                                          height=700,

                                          )

    fig_Homeless_Type_by_Shelter.update_layout({
        'plot_bgcolor': 'rgba(0, 0, 0, 0)',
        'paper_bgcolor': 'rgba(0, 0, 0, 0)',
    }, width=800, height=650)

    return fig_Homeless_Type_by_Shelter


def Youth_Homeless_Prop_Pie(selected_year=2018):
    data_pie_1 = data[data['homeless_type'].isin(['Homeless Unaccompanied Youth (Under 25)',  'Homeless Parenting Youth (Under 25)', 'Overall Homeless'])].groupby([
        'year', 'homeless_type']).sum('count').reset_index()
    for year in range(2015, 2019):
        Other_type_count = data_pie_1[(data_pie_1['year'] == year) & (data_pie_1['homeless_type'] == 'Overall Homeless')].reset_index(drop=True)['count'][0] - (data_pie_1[(data_pie_1['year'] == year) & (data_pie_1['homeless_type'] ==
                                                                                                                                                                                                           'Homeless Unaccompanied Youth (Under 25)')].reset_index(drop=True)['count'][0] + data_pie_1[(data_pie_1['year'] == year) & (data_pie_1['homeless_type'] == 'Homeless Parenting Youth (Under 25)')].reset_index(drop=True)['count'][0])

        df = pd.DataFrame({'year': [year], 'homeless_type': ['Others'],   'count': [Other_type_count]})
        data_pie_1 = data_pie_1.append(df)

    Youth_Homeless_Prop_fig = px.pie(data_pie_1[(data_pie_1['homeless_type'] != 'Overall Homeless') & (
        data_pie_1['year'] == selected_year)], values='count', names='homeless_type', title='Proportion of Chronically Homeless')

    Youth_Homeless_Prop_fig.update_layout({'plot_bgcolor': 'rgba(0, 0, 0, 0)', 'paper_bgcolor': 'rgba(0, 0, 0, 0)', }, width=600, height=600)

    return Youth_Homeless_Prop_fig


def homeless_youth(selected_year=2018):
    data_pie_5 = data[data['homeless_type'].isin(['Sheltered Total Homeless Parenting Youth (Under 25)', 'Sheltered Total Homeless Unaccompanied Youth (Under 25)',
                                                 'Unsheltered Homeless Parenting Youth (Under 25)', 'Unsheltered Homeless Unaccompanied Youth (Under 25)'])].groupby(['year', 'homeless_type']).sum('count').reset_index()

    Unsheltered_youth = data_pie_5[(data_pie_5['year'] == selected_year) & (data_pie_5['homeless_type'] == 'Unsheltered Homeless Parenting Youth (Under 25)')].reset_index(drop=True)[
        'count'][0] + (data_pie_5[(data_pie_5['year'] == selected_year) & (data_pie_5['homeless_type'] == 'Unsheltered Homeless Unaccompanied Youth (Under 25)')].reset_index(drop=True)['count'][0])
    Sheltered_youth = data_pie_5[(data_pie_5['year'] == selected_year) & (data_pie_5['homeless_type'] == 'Sheltered Total Homeless Parenting Youth (Under 25)')].reset_index(drop=True)[
        'count'][0] + (data_pie_5[(data_pie_5['year'] == selected_year) & (data_pie_5['homeless_type'] == 'Sheltered Total Homeless Unaccompanied Youth (Under 25)')].reset_index(drop=True)['count'][0])

    df_1 = pd.DataFrame({'year': [selected_year], 'homeless_type': ['Sheltered Youth'],   'count': [Sheltered_youth]})
    df_2 = pd.DataFrame({'year': [selected_year], 'homeless_type': ['Unsheltered Youth'],   'count': [Unsheltered_youth]})

    data_pie_5 = data_pie_5.append(df_1).append(df_2)

    data_pie_5 = data_pie_5[data_pie_5['homeless_type'].isin(['Sheltered Youth', 'Unsheltered Youth'])]
    fig_homeless_youth = px.pie(data_pie_5[data_pie_5['year'] == selected_year], values='count',
                                names='homeless_type', title='Youths Shelter Status', hole=0.4)
    fig_homeless_youth.update_layout({'plot_bgcolor': 'rgba(0, 0, 0, 0)', 'paper_bgcolor': 'rgba(0, 0, 0, 0)', }, width=450, height=450)

    return fig_homeless_youth


def homeless_youth_by_age(selected_year=2018):
    data_pie_6 = data[data['homeless_type'].isin(['Homeless Parenting Youth Under 18', 'Homeless Parenting Youth Age 18-24',
                                                  'Homeless Unaccompanied Youth Age 18-24', 'Homeless Unaccompanied Youth Under 18'])].groupby(['year', 'homeless_type']).sum('count').reset_index()

    youth_18_24 = data_pie_6[(data_pie_6['year'] == selected_year) & (data_pie_6['homeless_type'] == 'Homeless Unaccompanied Youth Age 18-24')].reset_index(drop=True)[
        'count'][0] + (data_pie_6[(data_pie_6['year'] == selected_year) & (data_pie_6['homeless_type'] == 'Homeless Parenting Youth Age 18-24')].reset_index(drop=True)['count'][0])
    youth_under_18 = data_pie_6[(data_pie_6['year'] == selected_year) & (data_pie_6['homeless_type'] == 'Homeless Unaccompanied Youth Under 18')].reset_index(drop=True)[
        'count'][0] + (data_pie_6[(data_pie_6['year'] == selected_year) & (data_pie_6['homeless_type'] == 'Homeless Parenting Youth Under 18')].reset_index(drop=True)['count'][0])

    df_1 = pd.DataFrame({'year': [selected_year], 'homeless_type': ['Between 18-24'],   'count': [youth_18_24]})
    df_2 = pd.DataFrame({'year': [selected_year], 'homeless_type': ['Under 18'],   'count': [youth_under_18]})

    data_pie_6 = data_pie_6.append(df_1).append(df_2)
    data_pie_6 = data_pie_6[data_pie_6['homeless_type'].isin(['Between 18-24',  'Under 18'])]

    fig_homeless_youth_by_age = px.pie(data_pie_6, values='count', names='homeless_type', title='Homeless Youth by Age', hole=0.4)
    fig_homeless_youth_by_age.update_layout({'plot_bgcolor': 'rgba(0, 0, 0, 0)', 'paper_bgcolor': 'rgba(0, 0, 0, 0)', }, width=450, height=450)

    return fig_homeless_youth_by_age


def yoy_fig1():
    plot1 = data.query('homeless_type == "Overall Homeless"').groupby('year').sum()
    # print(plot1)
    fig = px.bar(plot1, title="Comparison of total number of overall homeless through the years")
    fig.update_layout(xaxis_title="Years", yaxis_title="Total no of overall homeless")
    fig.update_layout(xaxis=dict(tickmode='linear'))
    return fig


def yoy_fig2():
    ca = data.loc[data.state.isin(["CA"])].groupby('year').sum()
    ca.rename(columns={'count': 'CA'}, inplace=True)
    mi = data.loc[data.state.isin(["MI"])].groupby('year').sum()
    mi.rename(columns={'count': 'MI'}, inplace=True)
    # print(mi)
    ca_mi = pd.merge(ca, mi, on='year')
    # print(ca_mi)
    # plot2= data.loc[data.state.isin(["CA", "MI"])].groupby('year').sum()
    # print(plot2)
    f = px.bar(ca_mi, y=["CA", "MI"], title="Total no of overall homeless for states MI and CA")
    f.update_layout(xaxis_title="Years", yaxis_title="Total no of overall homeless")
    f.update_layout(xaxis=dict(tickmode='linear'))
    return f


def yoy_fig3():
    df2 = data.loc[data['state'] == 'CA']
    df3 = df2.loc[data['homeless_type'].isin(['Sheltered Total Homeless Individuals', 'Unsheltered Homeless'])]
    df4 = df3.query('homeless_type == "Sheltered Total Homeless Individuals"')
    df5 = df3.query('homeless_type == "Unsheltered Homeless"')
    df4_overall_ca = df4[['year', 'count']].copy()
    df5_unsheltered_ca = df5[['year', 'count']].copy()
    df4_overall_ca.rename(columns={'count': 'Sheltered Total Homeless Individuals'}, inplace=True)
    df5_unsheltered_ca.rename(columns={'count': 'unsheltered_homeless'}, inplace=True)
    # df5_unsheltered_ca
    merged = pd.merge(df4_overall_ca, df5_unsheltered_ca, on='year')
    # print(merged)
    fig = px.line(merged, x='year', y=['Sheltered Total Homeless Individuals', 'unsheltered_homeless'],
                  title="Comparison of total number of Sheltered Total Homeless Individuals and Unsheltered Homeless through the years in CA state")
    # fig = px.line(df4_overall_ca, title="Comparison of total number of overall homeless through the years")
    fig.update_layout(xaxis=dict(tickmode='linear'))
    return fig


def yoy_fig4():
    d = data[data.homeless_type == "Overall Homeless"]
    d = d[d.state.isin(["CA", "MI", "NC", "NY", "PA"])].groupby('state')['count'].sum()
    d = d.to_frame()
    d.rename(columns={'count': 'Overall Homeless'}, inplace=True)

    e = data[data.homeless_type == "Sheltered Total Homeless"]
    e = e[e.state.isin(["CA", "MI", "NC", "NY", "PA"])].groupby('state')['count'].sum()
    e = e.to_frame()
    e.rename(columns={'count': 'Sheltered Total Homeless'}, inplace=True)

    de = pd.merge(d, e, on='state')

    f = px.bar(de, y=["Overall Homeless", "Sheltered Total Homeless"],
               title="Comparison of Overall Homeless vs Sheltered Total Homeless in 5 states")
    f.update_layout(xaxis_title="States", yaxis_title="Total no of overall homeless")
    f.update_layout(xaxis=dict(tickmode='linear'))
    return f


def yoy_fig5():
    d = data.query('year == 2018 & homeless_type == "Overall Homeless"')
    d = d.sort_values(by=['count'], ascending=False)
    fig = px.pie(d[:10], values='count', names='state', title='Top 10 States with Overall Homeless in 2018')
    fig.update_layout(xaxis=dict(tickmode='linear'))
    return fig


def yoy_fig6():
    d = data[data.homeless_type.isin([
        #'Homeless Individuals',
        'Homeless Family Households',
        'Homeless Veterans',
        'Chronically Homeless',
        'Homeless Children of Parenting Youth',
        'Homeless Unaccompanied Youth Under 18',
    ])]

    d = d.drop(columns=['state'])
    d = d.groupby(['year', 'homeless_type']).sum()
    d = d.reset_index()
    # print(d)

    fig = px.bar(d, x="year", y="count", color='homeless_type', title="Total Homeless count by year of all states")
    fig.update_layout(xaxis=dict(tickmode='linear'))
    return fig


def yoy_fig7():
    d = data[data.homeless_type == "Overall Homeless"].groupby(['year', 'state']).apply(lambda x: x)

    # Create empty DataFrame with specific column names & types
    _df = pd.DataFrame({'year': pd.Series(dtype='int'),
                        'state': pd.Series(dtype='str'),
                        'count': pd.Series(dtype='int')})

    for i in range(2007, 2019):
        h = d[d.year == i].sort_values(by=['count'], ascending=False).head(1)
        state = h.iloc[0]['state']
        count = h.iloc[0]['count']
        # print(state, count)

        _df = _df.append({
            'year': i,
            'state': state,
            'count': count
        }, ignore_index=True)

    # print(_df)
    _df.rename(columns={'count': 'total no of overall Homeless'}, inplace=True)

    fig = px.bar(_df, x="year", y="total no of overall Homeless", text="state", title="Max number of homeless state by year")
    fig.update_layout(xaxis=dict(tickmode='linear'))
    return fig


def yoy_fig8():
    d = data[data.year == 2018]
    d = d.groupby('homeless_type')['count'].sum().to_frame()
    d = d.sort_values(by=['count'], ascending=False).reset_index()

    fig = px.pie(d[2:18], values='count', names='homeless_type', title='Percentage of difference types of homeless categories in 2018')
    return fig


def yoy_fig9():
    pivoted_data_state_year_level = data.pivot_table(
        values='count', index=['year', 'state'], columns='homeless_type',  aggfunc=['sum'], margins=False)
    pivoted_data_state_year_level.columns = pivoted_data_state_year_level.columns.to_series().str.join('')
    pivoted_data_state_year_level.columns = pivoted_data_state_year_level.columns.str.replace("sum", "")
    pivoted_data_state_year_level.reset_index(inplace=True)
    fig = px.box(pivoted_data_state_year_level, x="year", y="Overall Homeless", title="Boxplot - Yearly Distribution of Homeless")
    return fig


drop_down_state_container = dcc.Dropdown(id="selected_year_state_tab", options=[
    {'label': '2015', 'value': 2015},
    {'label': '2016', 'value': 2016},
    {'label': '2017', 'value': 2017},
    {'label': '2018', 'value': 2018},
], multi=False, value=2018, style={'width': '100%'}
),


drop_down_state_container_variable = dcc.Dropdown(id="variable", options=[
    {'label': 'Overall Homeless', 'value': 'Overall Homeless'},
    {'label': 'Homelessness Rate', 'value': 'Homelessness Rate'},

], multi=False, value='Overall Homeless', style={'width': '100%'}
),


################ Subpopulations Tab ##########################
Homeless_Subpopulation = dbc.Container([
    dbc.Row([html.H2('Overall Homelessness during 2018', style={'text-align': 'center', 'margin-top': '20px'})]),
    # fig 1
    dbc.Row([dbc.Col(), dbc.Col([html.P('In this figure, we would like to analyze the data collected on homeless types in 2018 in the United States. From the data it can be assumed that Chronically homeless people constitute less proportion of overall homeless population.')]), dbc.Col()]),
    dbc.Row([dbc.Col(), dbc.Col([dcc.Graph(figure=Chronically_Homeless_Prop_Pie(2018),  style={'display': 'inline-block'}),]), dbc.Col()]),
    dbc.Row([dbc.Col(), dbc.Col([html.P('It can be seen that 17.6% of the homeless population is chronically homeless in 2018 where the other 82.4% of the homelessness belongs to all other homeless population categories. So, this proportion of chronically homeless population out of entire homeless population is not insignificant.')]), dbc.Col()]),

    dbc.Row(style={'margin': '50px', 'border': '1px solid gray'}),
    # fig 2
    dbc.Row([
        dbc.Col([html.P('In the first figure we would like to analyze total homeless population to find out whether USA has more sheltered homeless population than unsheltered')]),
        dbc.Col([html.P('In the second figure we would like to analyze the population of sheltered homeless population to see which type of shelter is provided more in the USA. It is assumed that  out of ES, SH and TH shelter type sheltered homeless population were allocated more in the ES shelter.')]),
    ]),
    dbc.Row([
        dbc.Col([dcc.Graph(figure=Homeless_by_shelter(2018),  style={'display': 'inline-block'}),]),
        dbc.Col([dcc.Graph(figure=sheltered_by_shelter_type(2018),  style={'display': 'inline-block'}),])
    ]),
    dbc.Row([
        dbc.Col([html.P('From the first chart it is clearly visible that USA has significantly more sheltered homeless than unsheltered and the size is almost double. So, it can be told that USA is actively trying to allocate their homeless population in shelter homes.')]),
        dbc.Col([html.P('From the second figure we can see out of sheltered homeless population, the major share of homeless population were given shelter to ES shelters and the proportion is 76.9% and the least chosen shelter type to allocate homeless population was SH shelters, whose proportion is only .543% that is  almost 142 times less than the former percentage. It is also visible that TH shelter types also got a significant amount of homeless population and the percentage is 22.5%')]),
    ]),

    dbc.Row(style={'margin': '50px', 'border': '1px solid gray'}),
    # fig 3
    dbc.Row([
        dbc.Col([html.P('In the first figure we would try to analyze the population of homeless households to see which population of homeless is more. It can be assumed that there less households with homeless people in families than  households with individually homeless population.')]),
        dbc.Col([html.P('In the second figure we will try to analyze shelter types provided to  households with homeless people in families and to households with individual homeless people. It is assumed ES shelter were given more than TH and SH shelters.')]),
    ]),
    dbc.Row([dbc.Col([dcc.Graph(figure=Overall_Homeless_subpop_bar(selected_year=2018),  style={'display': 'inline-block'}),]),
             dbc.Col([dcc.Graph(figure=Homeless_Type_by_Shelter(2018),  style={'display': 'inline-block'}),])]),
    dbc.Row([
        dbc.Col([html.P('From the first figure it is visible that almost 355,000 of  households has homeless individuals and almost 155,000 of households has homeless people in families which is half of the size of households with homeless individuals.')]),
        dbc.Col([html.P('From the second figure we can see out of total homeless individuals around 145,000 were sheltered in ES shelters and around 45,000 were sheltered in TH shelters and approximately 5,000 were sheltered in SH shelters.Out of total population of homeless in families almost 125,000 were sheltered in ES shelters and almost 35,000 were sheltered in TH shelters and none of them were sheltered in SH shelters. So, SH shelters are not much popular shelter types for allocating homeless households.')]),
    ]),

    dbc.Row(style={'margin': '50px', 'border': '1px solid gray'}),
    # fig 4

    dbc.Row([html.H2('Youth Homelessness during 2018', style={'text-align': 'center', 'margin-top': '20px'})]),
    dbc.Row([dbc.Col(), dbc.Col([html.P('In this figure, we would like to analyze the data collected on homeless types in 2018 in the United States. From the data it can be assumed that Chronically homeless people constitute less proportion of overall homeless population.')]), dbc.Col()]),
    dbc.Row([dbc.Col(), dbc.Col([dcc.Graph(figure=Youth_Homeless_Prop_Pie(2018),  style={'display': 'inline-block'}),]), dbc.Col()]),
    dbc.Row([dbc.Col(), dbc.Col([html.P('From this figure it can be seen only 7.17% of chronically homeless population is aged under 25 and remaining 91.8% are most likely aged more than 25. So, it can be said young population are less likely to be chronically homeless.')]), dbc.Col()]),
    dbc.Row([dbc.Col(), dbc.Col([html.P('From the chronically homeless youths population it also can be seen that the larger percentage of them are unaccompanied and the percentage is 6.59% and 1.58% is young homeless who are parenting.')]), dbc.Col()]),

    dbc.Row(style={'margin': '50px', 'border': '1px solid gray'}),
    # fig 4
    dbc.Row([
        dbc.Col([html.P('From this figure we will try to analyze out of young homeless population, which age group has more homelessness. It can be assumed that those who are under 18 are less likely to be more homeless.')]),
        dbc.Col([html.P('And then we will try to analyze from the other figure  we will try to analyze out of young homeless is there more sheltered than unsheltered. It can be assumed that there are more sheltered young homeless population than unsheltered.')]),
    ]),
    dbc.Row([dbc.Col([dcc.Graph(figure=homeless_youth(selected_year=2018),  style={'display': 'inline-block'}),]),
             dbc.Col([dcc.Graph(figure=homeless_youth_by_age(2018),  style={'display': 'inline-block'}),])]),
    dbc.Row([
        dbc.Col([html.P('From these two figures it is visible out of young population the larger share that is 90.7% are homeless who are above 18 but under 25 age group and only 9.27% is aged under 18  which is 10 times less than homeless population of age group (18-24).')]),
        dbc.Col([html.P('Then we also can see out of young homeless population 58.2% of homeless are sheltered and 41.8% are not sheltered yet. SO the margin between sheltered and unsheltered young homeless population is not large enough and authorities should work more on providing shelters to young homeless population.')]),
    ]),

    dbc.Row(style={'margin': '50px', 'border': '1px solid gray'}),

], fluid=True, style={"height": "100vh"})


################ YOY Analysis Tab ##########################


yoy_analysis = dbc.Container([
    dbc.Row([html.H2('Some Analysis Over Year', style={'text-align': 'center', 'margin-top': '20px'})]),
    # fig 1
    dbc.Row([dbc.Col(), dbc.Col([html.P('We are interested to see how the total number of overall homeless changes over the years from 2007 to 2018')]), dbc.Col()]),
    dbc.Row([dbc.Col(), dbc.Col([dcc.Graph(figure=yoy_fig1(),  style={'display': 'inline-block'}),]), dbc.Col()]),
    dbc.Row([dbc.Col(), dbc.Col([html.P('We can see from the above figure that the number of total overall homeless was the highest in 2007 which was around 650000. The number tends to gradually decrease over the next two years 2008 and 2009 followed by a small increase. There was a decreasing pattern that can be seen from 2013 to 2017. During 2018 the number tends to increase a little.')]), dbc.Col()]),

    dbc.Row(style={'margin': '50px', 'border': '1px solid gray'}),
    # fig 2
    dbc.Row([dbc.Col(), dbc.Col([html.P('In this figure we would like to analyze how the total number of overall homeless differs between the states CA and MI. We assume that CA being larger in both area and population than MI, the number would be more in CA.')]), dbc.Col()]),
    dbc.Row([dbc.Col(), dbc.Col([dcc.Graph(figure=yoy_fig2(),  style={'display': 'inline-block'}),]), dbc.Col()]),
    dbc.Row([dbc.Col(), dbc.Col([html.P('From the above figure we can observe that the number of overall homeless in CA is four times more than the number in MI in 2007 and 2008. And in other years it is around 5 times. We can also see a decreasing trend on the number of overall homeless from 2008 to 2010 in both states. In 2010 the number increased by 0.2 million and decreased again till 2017.')]), dbc.Col()]),

    dbc.Row(style={'margin': '50px', 'border': '1px solid gray'}),
    # fig 3
    dbc.Row([dbc.Col(), dbc.Col([html.P('In this figure we wanted to explore the correlation between the total number of Sheltered Total Homeless Individuals and Unsheltered Homeless through the years in CA state.')]), dbc.Col()]),
    dbc.Row([dbc.Col(), dbc.Col([dcc.Graph(figure=yoy_fig3(),  style={'display': 'inline-block'}),]), dbc.Col()]),
    dbc.Row([dbc.Col(), dbc.Col([html.P('We can see from the figure that the number of unsheltered homeless is 90000 in 2007 which is 3 times more than the  number of Sheltered Total Homeless Individuals which is around 30000. We can see a sharp decrease in the number of unsheltered homeless (around 18000 less ) from 2008 to 2009. However, there is a slight increase in the number of sheltered homeless during that time. From 2012 to 2017 we see that the sheltered homeless count has a slight decreasing trend but the number of unsheltered homeless showed a larger increasing trend.')]), dbc.Col()]),

    dbc.Row(style={'margin': '50px', 'border': '1px solid gray'}),
    # fig 4
    dbc.Row([dbc.Col(), dbc.Col([html.P('In this figure we tried to find out the trend between the overall homeless and sheltered total homeless for 5 different states which are also considered highly populated states.')]), dbc.Col()]),
    dbc.Row([dbc.Col(), dbc.Col([dcc.Graph(figure=yoy_fig4(),  style={'display': 'inline-block'}),]), dbc.Col()]),
    dbc.Row([dbc.Col(), dbc.Col([html.P('From the above figure it can be found that Both CA and NY have a large amount of Overall and Sheltered Total Homeless compared to the other 3 states. In particular, while the other states have a similar proportion of overall homeless and sheltered homeless, CA has more overall homeless than sheltered homeless, approximately 1million more than sheltered homeless.')]), dbc.Col()]),

    dbc.Row(style={'margin': '50px', 'border': '1px solid gray'}),
    # fig 5
    dbc.Row([dbc.Col(), dbc.Col([html.P('In this figure we would like to analyze how the percentage of overall homeless changes over all the states in 2018. We assume to find a higher percentage for states CA and NY as they are known as two of the highest populated states. ')]), dbc.Col()]),
    dbc.Row([dbc.Col(), dbc.Col([dcc.Graph(figure=yoy_fig5(),  style={'display': 'inline-block'}),]), dbc.Col()]),
    dbc.Row([dbc.Col(), dbc.Col([html.P('We can see from the above figure that CA has the highest percentage of overall homeless having a percentage of 35.11. Where NY has  the second highest percentage of 24.8. So our assumption was correct.')]), dbc.Col()]),

    dbc.Row(style={'margin': '50px', 'border': '1px solid gray'}),
    # fig 6
    dbc.Row([dbc.Col(), dbc.Col([html.P('In this figure, we would like to analyze the number of homeless in five categories over the years.')]), dbc.Col()]),
    dbc.Row([dbc.Col(), dbc.Col([dcc.Graph(figure=yoy_fig6(),  style={'display': 'inline-block'}),]), dbc.Col()]),
    dbc.Row([dbc.Col(), dbc.Col([html.P('From the above figure we can see that there was no chronically homeless people until 2011. Also there was no homeless accompanied youth under 18 and homeless children of parenting youth until 2014. The number of homeless family households showed a constant trend till 2012 and a small decrease after that. In 2009 and 2010, the number of homeless veterans was the highest and showed a decreasing trend afterwards.')]), dbc.Col()]),

    dbc.Row(style={'margin': '50px', 'border': '1px solid gray'}),
    # fig 7
    dbc.Row([dbc.Col(), dbc.Col([html.P('In this section we wanted to see which state has the maximum number of overall homeless in each specific year and what is that count.')]), dbc.Col()]),
    dbc.Row([dbc.Col(), dbc.Col([dcc.Graph(figure=yoy_fig7(),  style={'display': 'inline-block'}),]), dbc.Col()]),
    dbc.Row([dbc.Col(), dbc.Col([html.P('It can be seen from the above figure that CA has the maximum number of overall homeless in all years. In 2007, the number was the highest, approximately 140000 overall homeless which tends to show a decreasing trend from 2009 to 2015. After 2015 the number started to increase again, having approximately 130000 overall homeless in 2018.')]), dbc.Col()]),

    dbc.Row(style={'margin': '50px', 'border': '1px solid gray'}),
    # fig 8
    dbc.Row([dbc.Col(), dbc.Col([html.P('In this figure we analyzed how the percentage of different categories of homelessness differs among all the states in 2018.')]), dbc.Col()]),
    dbc.Row([dbc.Col(), dbc.Col([dcc.Graph(figure=yoy_fig8(),  style={'display': 'inline-block'}),]), dbc.Col()]),
    dbc.Row([dbc.Col(), dbc.Col([html.P('We can see that sheltered total homeless comprises the highest percentage 15.5% and sheltered ES homeless comprises 11.9% of the entire homeless counts. Around 7.8% are homeless people in families and 3.84% are chronically homeless individual.')]), dbc.Col()]),

    dbc.Row(style={'margin': '50px', 'border': '1px solid gray'}),
    # fig 9
    dbc.Row([dbc.Col(), dbc.Col([html.P('The boxplot below reveals tha we have some outliers. Some of the states are having extreme homelessness values compared to others. Each year, we have about 4 outliers states, which according to the above table, appear to be always CA, FL, NY , TX ')]), dbc.Col()]),
    dbc.Row([dbc.Col(), dbc.Col([dcc.Graph(figure=yoy_fig9(),  style={'display': 'inline-block'}),]), dbc.Col()]),
    dbc.Row([dbc.Col(), dbc.Col([html.P('We cannot draw the conclusion that the aforementioned states have the highest homelesness rate because their extreme values might be driven by their high population. In order to get a better results, it is good to normalize the numbers and get the true rates (Homeless count divided by population) ')]), dbc.Col()]),

    dbc.Row(style={'margin': '50px', 'border': '1px solid gray'}),

], fluid=True, style={"height": "100vh"})


################ State level tab ##########################
state_level_analysis = dbc.Container([

    dbc.Row([html.Br()]),
    dbc.Row([dbc.Col(), dbc.Col(), dbc.Col(drop_down_state_container)]),
    dbc.Row([html.H2('Homelessness by US Regions')]),
    dbc.Row([html.P('The distribution of homeless people among the four US regions is shown in the table below, along with a comparison to the previous year and the four years preceding. Given its high population and cost of living, the west is predicted to have the highest rate of homelessness.')]),
    dbc.Row([dbc.Col([html.Div(id='yoy_summary')])]),
    dbc.Row(html.P('The results show that the West has the highest percentage of homeless people (38%), followed by the Northeast (26.53%). These two areas host more than half (65%) of the homeless population.')),

    dbc.Row(style={'margin': '50px', 'border': '1px solid gray'}),

    dbc.Row([html.H2('Homelessness by US States')]),
    dbc.Row(html.P('A lot of reasons that are state-specific can contribute to homelessness, like poverty, unemployment, cost of living, cost of housing and mental health, domestic violence. and that explains why some states have more homelessness than others')),
    dbc.Row([dbc.Col(), dbc.Col(), dbc.Col(drop_down_state_container_variable)]),
    dbc.Row([html.Br()]),
    dbc.Row([dbc.Col([dcc.Graph(id="fig_3_state",  style={'display': 'inline-block'}),]),
            dbc.Col([dcc.Graph(id="fig_2_state",  style={'display': 'inline-block'}),]),]),
    dbc.Row(html.P('California has the highest number of homeless people. Its homeless crisis is associated with high housing costs as people not able to find affordable housing. ')),

    dbc.Row(style={'margin': '50px', 'border': '1px solid gray'}),

    dbc.Row([dbc.Col([dcc.Graph(figure=beds_availability(selected_state='AR'),  style={'display': 'inline-block'}),])]),
    dbc.Row([html.P('One of the major reasons why we continue to have unsheltered people, is that we don’t have znough ressources for them.')]),

    dbc.Row(html.P('The above chart illustrates the shelter situation of the homeless people and the beds availability in Arkansas and proves the above assumption. Over time, there have been many fewer beds available in the various shelter kinds (TH,ES,SH) than there have been homeless people.'))


])


app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = html.Div([dbc.Tabs(
    [
        dbc.Tab(Homeless_Subpopulation, label="Homeless Subpopulation"),
        dbc.Tab(yoy_analysis, label="Year over Year Analysis"),
        dbc.Tab(state_level_analysis, label="State Level Analysis")
    ]
)])


@ app.callback(
    [
        Output(component_id='fig_2_state', component_property='figure'),
        Output(component_id='fig_3_state', component_property='figure'),
        Output(component_id='yoy_summary', component_property='children')
    ],
    [Input(component_id='selected_year_state_tab', component_property='value'),
     Input(component_id='variable', component_property='value')
     ],
)
def update_graphs_state(year, variable):
    year = int(year)

    yoy_homeless = state_level_summary(selected_year=year)

    return homeless_count_map(selected_year=year, count_type=variable), top_10_highest_homeless_count(selected_year=year, count_type=variable),  dbc.Table.from_dataframe(yoy_homeless, striped=False, bordered=True, hover=True, index=True, size='sm')


if __name__ == "__main__":
    app.run_server()
