import pandas as pd

data = pd.read_csv(r'https://storage.googleapis.com/assignment-data/Point_in_Time_Estimates_of_Homelessness_in_the_US_by_State.csv')

data.rename(columns={'count_type': 'homeless_type'}, inplace=True)
data = data[data['state'] != 'MP']
data = data[data['state'] != 'Total']
data['count'] = data['count'].astype(int)
data = data.dropna()
