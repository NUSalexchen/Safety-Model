import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import scipy.stats as stats
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter
from io import BytesIO
import base64
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import uuid

pd.set_option('display.float_format', lambda x: '%.0f' % x)
st.set_page_config(layout='wide')

# page_bg_color = """
# <style>
# [data-testid="stAppViewContainer"] > .main {
# background-color: white;
# background-size: cover;
# background-position: center center;
# background-repeat: no-repeat;
# background-attachment: local;
# }
# [data-testid="stHeader"] {
# background: rgba(255,0,0,0);
# }
# </style>
# """
#st.markdown(page_bg_color, unsafe_allow_html=True)

uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"])

if uploaded_file is not None:
    # Read the uploaded Excel file
    overall = pd.read_excel(uploaded_file, sheet_name='Sheet2')
    df = pd.read_excel(uploaded_file, sheet_name='Sheet1')
else:
    overall = pd.read_excel('singapore9.xlsx', sheet_name='Sheet2')
    df = pd.read_excel('singapore9.xlsx', sheet_name='Sheet1')
    st.write("Please upload an Excel file.")


st.subheader("Overall Singapore Deadstock (Total Stock)")


# Round the values in 'Total Deadstock' and 'Average Inventory' to the nearest 1000
overall.loc[overall['Measurement'] == 'Total Deadstock', overall.columns[1:]] = overall.loc[overall['Measurement'] == 'Total Deadstock', overall.columns[1:]].round(-3)
overall.loc[overall['Measurement'] == 'Average Inventory', overall.columns[1:]] = overall.loc[overall['Measurement'] == 'Average Inventory', overall.columns[1:]].round(-3)

# Add ($) to the 'Measurement' row names for 'Total Deadstock' and 'Average Inventory'
overall.loc[overall['Measurement'] == 'Total Deadstock', 'Measurement'] = 'Total Deadstock ($)'
overall.loc[overall['Measurement'] == 'Average Inventory', 'Measurement'] = 'Average Inventory ($)'

# Change 'Overall' column name to 'P3M'
overall.rename(columns={'Overall': 'P3M'}, inplace=True)
overall


df['Actuals_P3M'] = df[['Actuals_Apr', 'Actuals_May','Actuals_Jun']].mean(axis=1)

df = df.sort_values(by='Actuals_P3M', ascending=False)

# Calculate the cumulative percentage
df['Cumulative Percent'] = df['Actuals_P3M'].cumsum() / df['Actuals_P3M'].sum() * 100

# Define the ABC classification based on the cumulative percentage
def classify_abc(cumulative_percent):
    if cumulative_percent <= 75:
        return 'A'
    elif cumulative_percent <= 90:
        return 'B'
    else:
        return 'C'

# Apply the classification
df['ABC'] = df['Cumulative Percent'].apply(classify_abc)

# Plotting the bar graph
abc_counts = df['ABC'].value_counts().sort_index()

# abc_colors = {
#     'A': '#DCB0F2',  # Hex code for rgb(220, 176, 242)
#     'B': '#F6CF71',  # Hex code for rgb(246, 207, 113)
#     'C': '#F89C74'   # Hex code for rgb(248, 156, 116)
# }

# fig, ax = plt.subplots()
# ax.bar(abc_counts.index, abc_counts.values, color=[abc_colors.get(x) for x in abc_counts.index])
# for i in range(len(abc_counts)):
#     ax.text(i, abc_counts.values[i] + 0.5, str(abc_counts.values[i]), ha='center', va='bottom')
# ax.set_xlabel('ABC Category')
# ax.set_ylabel('Number of SKUs')
# ax.set_title('Number of SKUs in Each ABC Category')

# # Display the plot in Streamlit
# st.pyplot(fig)

# Selection to choose data display format
display_format = st.radio('Choose data display format:', ['$ (SGD)', 'Quantity (Cartons)'])

# Adjust the DataFrame based on the selected display format
if display_format == 'Quantity (Cartons)':
    df_quantity = df.copy()
    numeric_columns = df_quantity.select_dtypes(include=[np.number]).columns.tolist()
    # Exclude the specified columns from division
    exclude_columns = ['SKU', 'average_lead_time',  'Lead Time Variance', 'lead_time_std_dev','COGS', 'MOQ', 'Shelf Life', 'deadstock%', 'DFC','Inventory Policy','Cumulative Percent','ABC']
    columns_to_divide = [col for col in numeric_columns if col not in exclude_columns]

    df_quantity[columns_to_divide] = round(df_quantity[columns_to_divide].div(df['COGS'], axis=0),-1)
    deadstock = df_quantity[['Name','SKU','brand','deadstock%','Deadstock','DFC','ABC']]
    df = df_quantity
    currency = "Quantity"
    currency_symbol = "Cartons"
else:
    currency = "Dollar"
    currency_symbol = "SGD"
    deadstock = df[['Name','SKU','brand','deadstock%','Deadstock','DFC','ABC']]
    
pd.set_option('display.float_format', lambda x: '%.0f' % x)

# Brand options
brands = df['brand'].unique().tolist()

# Sidebar options for brand selection
selected_brands = st.sidebar.multiselect('Select brands to include:', brands, default=['Yeos Food','Yeos Beverage','Yeos Others'])

# Filter based on selected brands
deadstock_yeos = deadstock[deadstock['brand'].isin(selected_brands)]

# Sidebar options for sorting
sort_options = ['Deadstock','deadstock%', 'DFC']
sort_column = st.sidebar.selectbox('Select column to sort by:', sort_options)
sort_order = st.sidebar.radio('Sort order:', ['Descending','Ascending'])
sort_ascending = sort_order == 'Ascending'

# Sidebar options for filtering
sort_options2 = ['deadstock%','Deadstock', 'DFC']
filter_column = st.sidebar.selectbox('Select column to filter by:', sort_options2)
filter_value = st.sidebar.slider('Filter value for {}:'.format(filter_column), 0, 100, 20)  # Adjust range as needed

# Apply filtering
filtered_df = deadstock_yeos[deadstock_yeos[filter_column] >= filter_value]

# Apply sorting
sorted_df = filtered_df.sort_values(by=sort_column, ascending=sort_ascending)
sorted_df['Cumulative Deadstock'] = sorted_df['Deadstock'].cumsum()
sorted_df['Cumulative Deadstock %'] = np.round(sorted_df['Cumulative Deadstock'] / deadstock['Deadstock'].sum() * 100, 0)
max_rows = len(sorted_df)

# Number of rows to display
num_rows = st.sidebar.slider('Number of rows to display:', 1, max_rows, 10)

# Reset the index
sorted_df = sorted_df.reset_index(drop=True)
sorted_df.index = sorted_df.index + 1

# Display the table
sorted_df_head = sorted_df.head(num_rows)
sorted_df_head['SKU'] = sorted_df_head['SKU'].astype(str)
sorted_df_head = sorted_df_head.rename(columns={'deadstock%':'Deadstock (%)','DFC':'DFC (Days)'})
st.subheader("Top {} SKU Analysis with greater than {}% Deadstock".format(num_rows, filter_value))
st.dataframe(sorted_df_head)

# Add an export button to download the data as CSV or Excel
def to_excel(df):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Sheet1')
    writer.save()
    processed_data = output.getvalue()
    return processed_data
    
# Function to load an image and convert it to base64
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()
    
# Load icons and convert to base64
csv_icon = get_base64_of_bin_file('csv.png')  # Update the path if necessary
excel_icon = get_base64_of_bin_file('excel.png')  # Update the path if necessary

# Convert dataframe to CSV
csv = sorted_df_head.to_csv(index=False).encode('utf-8')

# Convert dataframe to Excel
excel = to_excel(sorted_df_head)

# Display download buttons with icons
col1, col2 = st.columns(2)

with col1:
    st.markdown(
        f'<img src="data:image/png;base64,{excel_icon}" width="30" height="30" style="vertical-align: middle; margin-right: 10px;">',
        unsafe_allow_html=True,
    )
    st.download_button(
        label="Download data as Excel",
        data=excel,
        file_name='deadstock_analysis.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    
with col2:
    st.markdown(
        f'<img src="data:image/png;base64,{csv_icon}" width="30" height="30" style="vertical-align: middle; margin-right: 10px;">',
        unsafe_allow_html=True,
    )
    st.download_button(
        label="Download data as CSV",
        data=csv,
        file_name='deadstock_analysis.csv',
        mime='text/csv',
    )


# Calculate average daily consumption for each month


pd.set_option('display.float_format', lambda x: '%.0f' % x)

# Streamlit UI
st.title("SKU Analysis")

# Add CSS to style the number input
st.markdown(
    """
    <style>
    div[data-baseweb="input"] {
        max-width: 100px;  /* Adjust the width as needed */
    }
    </style>
    """,
    unsafe_allow_html=True
)

col1, col2, col3 = st.columns(3)
with col1:
    service_level_a = st.number_input("Service Level for A", min_value=0.0, max_value=1.0, value=0.99)
with col2:
    service_level_b = st.number_input("Service Level for B", min_value=0.0, max_value=1.0, value=0.97)
with col3:
    service_level_c = st.number_input("Service Level for C", min_value=0.0, max_value=1.0, value=0.97)

def map_service_level(abc_class):
    if abc_class == 'A':
        return service_level_a
    elif abc_class == 'B':
        return service_level_b
    else:
        return service_level_c

# Apply the service level mapping
df['Service_Level'] = df['ABC'].apply(map_service_level)

# Calculate the safety factor based on the new service levels
df['safety_factor'] = df['Service_Level'].apply(lambda x: stats.norm.ppf(x))

# Create a new column combining Name and SKU
df['Name_SKU'] = df['Name'] + ' (' + df['SKU'].astype(str) + ')'
# Select SKU
sku_options = df['Name_SKU'].tolist()
selected_name_sku = st.selectbox("Choose SKU:", sku_options)

# Extract the SKU from the selected option
SKU = int(selected_name_sku.split('(')[-1].strip(')'))

# Apply the service level mapping
df['Service_Level'] = df['ABC'].apply(map_service_level)

# Calculate the safety factor based on the new service levels
df['safety_factor'] = df['Service_Level'].apply(lambda x: stats.norm.ppf(x))

# Get the default service level for the selected SKU
default_service_level = df.loc[df['SKU'] == SKU, 'Service_Level'].values[0]

service_level = st.number_input("Enter Service Level (as a decimal):", min_value=0.0, max_value=1.01, value=df.loc[df['SKU'] == SKU, 'Service_Level'].values[0])
safety_factor = stats.norm.ppf(service_level)

st.latex(r'''
SS = Z \times \sqrt{\left(\frac{LT}{T_1} \times \sigma_{RMSE}\right)^2 + \left(\sigma_{LT} \times RMSE_{avg}\right)^2}
''')


df['safety_factor'] = safety_factor

# Update 'Average_Lead_Time' and 'lead_time_std_dev' for specific brands
df.loc[df['brand'].isin(['Agency Beverage', 'Agency Food','Agency Others']), ['average_lead_time', 'lead_time_std_dev']] = [90, 0]

df['Forecast_Error_Mar'] = (np.maximum(df['Actuals_Mar'], 0) - df['Forecast_Mar'])
df['Forecast_Error_Apr'] = (np.maximum(df['Actuals_Apr'], 0) - df['Forecast_Apr'])
df['Forecast_Error_May'] = (np.maximum(df['Actuals_May'], 0) - df['Forecast_May'])
df['Forecast_Error_Jun'] = (np.maximum(df['Actuals_Jun'], 0) - df['June_FC_Future'])
df['Forecast_Error'] = df[['Forecast_Error_Apr', 'Forecast_Error_May', 'Forecast_Error_Jun']].abs().mean(axis=1)


    # Calculate the standard deviation of the forecast error for each row
#df['Forecast_Error'] = df[['Forecast_Error_Apr', 'Forecast_Error_May','Forecast_Error_Jun']].mean(axis=1)
df['Forecast_Error_Std_Dev'] = df[['Forecast_Error_Apr', 'Forecast_Error_May','Forecast_Error_Jun']].std(axis=1)
df['Forecast Error (%)'] = df['Forecast_Error']/(df[['Forecast_Mar','Forecast_Apr', 'Forecast_May','June_FC_Future']].mean(axis=1))*100

df['Forecast_Error_Mar2'] = (np.maximum(df['Actuals_Mar'], 0) - df['Forecast_Mar'])
df['Forecast_Error_Apr2'] = (np.maximum(df['Actuals_Apr'], 0) - df['Forecast_Apr'])
df['Forecast_Error_May2'] = (np.maximum(df['Actuals_May'], 0) - df['Forecast_May'])
df['Forecast_Error_Jun2'] = (np.maximum(df['Actuals_Jun'], 0) - df['June_FC_Future'])

df['Adjusted_Error_Mar'] = np.where(df['Forecast_Error_Mar2'] < 0, df['Forecast_Error_Mar2'] * 0.5, df['Forecast_Error_Mar2'])
df['Adjusted_Error_Apr'] = np.where(df['Forecast_Error_Apr2'] < 0, df['Forecast_Error_Apr2'] * 0.5, df['Forecast_Error_Apr2'])
df['Adjusted_Error_May'] = np.where(df['Forecast_Error_May2'] < 0, df['Forecast_Error_May2'] * 0.5, df['Forecast_Error_May2'])
df['Adjusted_Error_Jun'] = np.where(df['Forecast_Error_Jun2'] < 0, df['Forecast_Error_Jun2'] * 0.5, df['Forecast_Error_Jun2'])

# df['Adjusted_Error_Mar'] = np.where(df['Forecast_Error_Mar'] < 0, df['Forecast_Error_Mar'] * 0.9, df['Forecast_Error_Mar'])
# df['Adjusted_Error_Apr'] = np.where(df['Forecast_Error_Apr'] < 0, df['Forecast_Error_Apr'] * 0.9, df['Forecast_Error_Apr'])
# df['Adjusted_Error_May'] = np.where(df['Forecast_Error_May'] < 0, df['Forecast_Error_May'] * 0.9, df['Forecast_Error_May'])
# df['Adjusted_Error_Jun'] = np.where(df['Forecast_Error_Jun'] < 0, df['Forecast_Error_Jun'] * 0.9, df['Forecast_Error_Jun'])

# Step 2: Square the errors
df['Squared_Error_Mar'] = df['Adjusted_Error_Mar'] ** 2
df['Squared_Error_Apr'] = df['Adjusted_Error_Apr'] ** 2
df['Squared_Error_May'] = df['Adjusted_Error_May'] ** 2
df['Squared_Error_Jun'] = df['Adjusted_Error_Jun'] ** 2

# Step 3: Calculate the mean of the squared errors
df['Mean_Squared_Error'] = df[['Squared_Error_Apr', 'Squared_Error_May', 'Squared_Error_Jun']].mean(axis=1)

# Step 4: Take the square root to get RMSE
df['Forecast_Error2'] = np.sqrt(df['Mean_Squared_Error'])

df['MOQ'] = df['MOQ'].replace({'5x1200 ( If no Co-run with other country )': '6000'})
df['MOQ'] = df['MOQ'].replace({'Take MY Stock': '6000'})

df['MOQ'] = df['MOQ'].fillna(0).astype(int)

df['Months_Covered_By_Lot_Size'] = df['MOQ'] / (df['Average_FC_Future_3M']/df['COGS'])

#Calculate Safety Stock using the adjusted formula

# df['Safety_Stock'] = round(
#     np.maximum(
#         df['safety_factor'] * np.sqrt(
#             (df['average_lead_time']/30 * (df['Forecast_Error_Std_Dev']**2) +
#             (df['Forecast_Error']**2 * (df['lead_time_std_dev']/np.sqrt(30))**2))
#         ) * (1 - df['Months_Covered_By_Lot_Size'] / 12),
#         (df['Average_FC_Future_3M'] / (30/7))
#     ),
#     0
# )

df['Safety_Stock'] = round(
    np.maximum(
        df['safety_factor'] * np.sqrt(
            (df['average_lead_time']/30 * (df['Forecast_Error_Std_Dev']**2) +
            (df['Forecast_Error2'])**2 * (df['lead_time_std_dev']/np.sqrt(30))**2)
        ) * (1 - df['Months_Covered_By_Lot_Size'] / 12),
        (df['Average_FC_Future_3M'] / (30/7))
    ),
    0
)

# Calculate Safety Stock using RMSE
#df['Safety_Stock'] = df['safety_factor'] * df['RMSE_Forecast_Error'] * np.sqrt(df['average_lead_time'])

df['Safety_Stock_qty'] = df['Safety_Stock']/df['COGS']

df['Safety_Stock_days'] = df['Safety_Stock'] /df['Average_FC_Future_3M'] * 30

###########################

business_days_per_week = 5
# Calculate Safety Stock in business days
df['Safety_Stock_bus_days'] = round(df['Safety_Stock'] /df['Average_FC_Future_3M'] * 21.4,0)
df['Safety_Stock_Proposed_Mar'] = df['Forecast_Mar']/30*df['Safety_Stock_days']
df['Safety_Stock_Proposed_Apr'] = df['Forecast_Apr']/30*df['Safety_Stock_days']
df['Safety_Stock_Proposed_May'] = df['Forecast_May']/30*df['Safety_Stock_days']
df['Safety_Stock_Proposed_Jun'] = df['June_FC_Future']/30*df['Safety_Stock_days']
df['Safety_Stock_Proposed_Jul'] = df['July_FC_Future']/30*df['Safety_Stock_days']
df['Safety_Stock_Proposed_Aug'] = df['August_FC_Future']/30*df['Safety_Stock_days']
# Calculate Current Safety Stock for each month
df['Current_Safety_Stock_Mar'] = (df['Forecast_Mar'] / 4) * df['Inventory Policy']
df['Current_Safety_Stock_Apr'] = (df['Forecast_Apr'] / 4) * df['Inventory Policy']
df['Current_Safety_Stock_May'] = (df['Forecast_May'] / 4) * df['Inventory Policy']
df['Current_Safety_Stock_Jun'] = (df['June_FC_Future'] / 4) * df['Inventory Policy']
df['Current_Safety_Stock_Jul'] = (df['July_FC_Future'] / 4) * df['Inventory Policy']
df['Current_Safety_Stock_Aug'] = (df['August_FC_Future'] / 4) * df['Inventory Policy']
df['Current_Safety_Stock']=df[['Current_Safety_Stock_Jun', 'Current_Safety_Stock_Jul', 'Current_Safety_Stock_Aug']].mean(axis=1)
df['Proposed_Safety_Stock'] = df[['Safety_Stock_Proposed_Jun', 'Safety_Stock_Proposed_Jul', 'Safety_Stock_Proposed_Aug']].mean(axis=1)

df['Current_Safety_Stock_bus_days'] = round(df['Current_Safety_Stock']/df['Average_FC_Future_3M'] * 21.4,0)
df['days_diff'] = round(df['Current_Safety_Stock_bus_days']-df['Safety_Stock_bus_days'],0)

df['Savings'] = df['Current_Safety_Stock'] - df['Proposed_Safety_Stock']
df['Savings Deadstock'] = df['Deadstock'] - df['Current_Safety_Stock']
df = df.rename(columns={'June_FC_Future':'Forecast_Jun','July_FC_Future':'Forecast_Jul','August_FC_Future':'Forecast_Aug'})
## For Later Simulation
df['Avg_Daily_Consumption_Mar'] = df['Actuals_Mar'] / 30
df['Avg_Daily_Consumption_Apr'] = df['Actuals_Apr'] / 30
df['Avg_Daily_Consumption_May'] = df['Actuals_May'] / 30
df['Avg_Daily_Consumption_Jun'] = df['Actuals_Jun'] / 30
df['Avg_Daily_Consumption_Jul'] = df['Forecast_Jul'] / 30
df['Avg_Daily_Consumption_Aug'] = df['Forecast_Aug'] / 30
df['Starting_Inventory'] = df['1-Mar']

df_sku=df[df['SKU']==SKU]



df_sku=df[df['SKU']==SKU]

inventory_data = df_sku.iloc[0, 2:99]
inventory_data = pd.to_numeric(inventory_data, errors='coerce')

inventory_data = pd.to_numeric(inventory_data, errors='coerce')
def convert_index_to_datetime(index, date_format='%d-%b', year=2024):
    dates = pd.to_datetime(index, format=date_format, errors='coerce')
    return dates.map(lambda d: d.replace(year=year) if pd.notnull(d) else d)

# Create a DataFrame for the complete date range
date_range = pd.date_range(start='2024-03-01', end='2024-08-30', freq='D')

# Convert inventory_data index to datetime format with the correct year
inventory_data.index = convert_index_to_datetime(inventory_data.index)


# Generate continuous date range from 1-Mar to 30-Aug
date_range = pd.date_range(start='2024-03-01', end='2024-08-30', freq='D')

# Define the indices for each month
mar_start_index = date_range.get_loc('2024-03-01')
mar_end_index = date_range.get_loc('2024-03-30')
apr_start_index = date_range.get_loc('2024-04-01')
apr_end_index = date_range.get_loc('2024-04-30')
may_start_index = date_range.get_loc('2024-05-02')
may_end_index = date_range.get_loc('2024-05-31')
jun_start_index = date_range.get_loc('2024-06-03')
jun_end_index = date_range.get_loc('2024-06-30')
jul_start_index = date_range.get_loc('2024-07-01')
jul_end_index = date_range.get_loc('2024-07-31')
aug_start_index = date_range.get_loc('2024-08-01')
aug_end_index = date_range.get_loc('2024-08-30')

# Combine data for each category into single continuous lines
forecast_x = []
forecast_y = []
actuals_x = []
actuals_y = []
safety_stock_proposed_x = []
safety_stock_proposed_y = []
current_safety_stock_x = []
current_safety_stock_y = []

# Months definitions
months = ['Mar', 'Apr', 'May', 'Jun']
future_months = ['Jul', 'Aug']

# Add forecast, actuals, safety stock proposed, and current safety stock for each month
for month in months + future_months:
    start_index = locals()[f'{month.lower()[:3]}_start_index']
    end_index = locals()[f'{month.lower()[:3]}_end_index']
    
    forecast_x.extend(date_range[start_index:end_index+1])
    forecast_y.extend([df_sku[f'Forecast_{month}'].values[0]]*(end_index-start_index+1))
    
    if month in months:
        actuals_x.extend(date_range[start_index:end_index+1])
        actuals_y.extend([df_sku[f'Actuals_{month}'].values[0]]*(end_index-start_index+1))
    
    safety_stock_proposed_x.extend(date_range[start_index:end_index+1])
    safety_stock_proposed_y.extend([df_sku[f'Safety_Stock_Proposed_{month}'].values[0]]*(end_index-start_index+1))
    
    current_safety_stock_x.extend(date_range[start_index:end_index+1])
    current_safety_stock_y.extend([df_sku[f'Current_Safety_Stock_{month}'].values[0]]*(end_index-start_index+1))

# Create the figure

# Create figure with secondary y-axis
fig = make_subplots(specs=[[{"secondary_y": True}]])

# Add inventory data
fig.add_trace(go.Scatter(x=inventory_data.index, y=inventory_data.values, mode='lines', name='Daily Inventory', line=dict(color='blue')))

# Add horizontal lines for deadstock and average
fig.add_trace(go.Scatter(x=date_range[:jun_end_index+1], y=[df_sku['Deadstock'].values[0]]*(jun_end_index+1), mode='lines', name='Deadstock', line=dict(color='red')))
fig.add_trace(go.Scatter(
    x=date_range,
    y=[0]*len(date_range[:jun_end_index+1]),
    fill='tonexty',
    mode='none',
    fillcolor='rgba(255, 0, 0, 0.2)',
    showlegend=False
))

# fig.add_trace(go.Scatter(x=date_range[:jun_end_index+1], y=[df_sku['Average'].values[0]]*(jun_end_index+1), mode='lines', name='Average Inventory', line=dict(color='blue', dash='dash')))

# Add combined lines for each category
fig.add_trace(go.Scatter(x=forecast_x, y=forecast_y, mode='lines', name='Forecast', line=dict(color='green',dash='dash')))
fig.add_trace(go.Scatter(x=actuals_x, y=actuals_y, mode='lines', name='Shipments', line=dict(color='purple',dash='dash')))
fig.add_trace(go.Scatter(x=safety_stock_proposed_x, y=safety_stock_proposed_y, mode='lines', name='Safety Stock Proposed', line=dict(color='black')))
fig.add_trace(go.Scatter(x=current_safety_stock_x, y=current_safety_stock_y, mode='lines', name='Current Safety Stock', line=dict(color='orange')))

march_data = inventory_data['2024-03']
min_value_mar = round(march_data.min(),-1)
min_index_mar = march_data.idxmin()
formatted_min_value = f"{int(min_value_mar):,}"

fig.add_trace(go.Scatter(x=[min_index_mar], y=[min_value_mar], mode='markers+text', name='March Min', marker=dict(color='blue', size=10, opacity=0.6)))
# Add annotation with black background, moving it further down


# Add minimum point for April
april_data = inventory_data['2024-04']
min_value_apr = round(april_data.min(),-1)
min_index_apr = april_data.idxmin()
fig.add_trace(go.Scatter(x=[min_index_apr], y=[min_value_apr], mode='markers+text', name='April Min', marker=dict(color='blue', size=10, opacity=0.6)))

# Add minimum point for May
may_data = inventory_data['2024-05']
min_value_may = round(may_data.min(),-1)
min_index_may = may_data.idxmin()
fig.add_trace(go.Scatter(x=[min_index_may], y=[min_value_may], mode='markers+text', name='May Min', marker=dict(color='blue', size=10, opacity=0.6)))

jun_data = inventory_data['2024-06']
min_value_jun = round(jun_data.min(),-1)
min_index_jun = jun_data.idxmin()
fig.add_trace(go.Scatter(x=[min_index_jun], y=[min_value_jun], mode='markers+text', name='June Min', marker=dict(color='blue', size=10, opacity=0.6)))

# Find the overall minimum value and its corresponding date
overall_min_value = min(min_value_apr, min_value_may, min_value_jun)
if overall_min_value == min_value_apr:
    overall_min_index = min_index_apr
elif overall_min_value == min_value_may:
    overall_min_index = min_index_may
else:
    overall_min_index = min_index_jun

# Add the overall minimum point to the plot
fig.add_trace(go.Scatter(x=[overall_min_index], y=[overall_min_value], mode='markers+text', name='Overall Min Value', textposition='top right', marker=dict(color='red', size=10)))

min_indices = [min_index_mar, min_index_apr, min_index_may, min_index_jun]
min_values = [min_value_mar, min_value_apr, min_value_may, min_value_jun]
# Determine the minimum value among April, May, and June
min_value_apr_may_jun = min(min_value_apr, min_value_may, min_value_jun)

# Loop through each month's minimum value and index to add the annotation
for min_index, min_value in zip(min_indices, min_values):
    formatted_min_value = f"{int(min_value):,}"
    
    # Determine the background color (red for the lowest among April, May, June; black otherwise)
    if min_value == min_value_apr_may_jun and min_value in [min_value_apr, min_value_may, min_value_jun]:
        bgcolor = 'red'
        
    else:
        bgcolor = 'black'
    
    fig.add_annotation(
        x=min_index,
        y=min_value,
        text=f'<b>{formatted_min_value}</b>',
        showarrow=False,
        font=dict(color='white', size=12),
        align='center',
        bgcolor=bgcolor,
        borderpad=4,
        opacity=1,
        yshift=-20  # Move the annotation further down
    )

sku_name = df_sku['Name'].values[0] if not df_sku.empty else "Unknown"

# Define custom x-axis ticks to show more ticks
x_tick_values = pd.date_range(start='2024-03-01', end='2024-08-30', freq='7D')
x_tick_text = x_tick_values.strftime('%-d-%b')

# Define colors for each month
month_colors = ['rgba(255, 0, 0, 0.1)', 'rgba(0, 255, 0, 0.1)', 'rgba(0, 0, 255, 0.1)', 
                'rgba(255, 255, 0, 0.1)', 'rgba(255, 0, 255, 0.1)', 'rgba(0, 255, 255, 0.1)']

# Add shapes for each month
all_months = months + future_months
for i, month in enumerate(all_months):
    if i == 0:
        # First month starts at the beginning
        start_index = date_range.get_loc(f'2024-03-01')
    else:
        # Subsequent months start from the end of the previous month
        prev_month = all_months[i - 1]
        prev_month_end = 31 if prev_month in ['May', 'Jul'] else 30
        start_index = date_range.get_loc(f'2024-{prev_month[:3].capitalize()}-{prev_month_end}')
    
    month_end = 31 if month in ['May', 'Jul'] else 30
    end_index = date_range.get_loc(f'2024-{month[:3].capitalize()}-{month_end}')
    
    fig.add_shape(
        type="rect",
        x0=date_range[start_index],
        x1=date_range[end_index],
        y0=0,
        y1=1,
        yref='paper',  # reference to the whole plot height
        fillcolor=month_colors[i % len(month_colors)],
        opacity=0.3,
        layer="below",
        line_width=0,
        name=f"{month}"
    )

# Assuming 'COGS_value' is your cost of goods sold value
COGS_value = df_sku['COGS'].values[0]  # Replace with your actual COGS retrieval logic


# Add trace for the secondary y-axis (quantity), simply the primary y-axis divided by COGS
fig.add_trace(
    go.Scatter(x=inventory_data.index, y=inventory_data.values / COGS_value, name="Quantity (Cartons)", line=dict(color='rgba(0,0,0,0)')),  # Invisible line
    secondary_y=True,
)

# Update layout with dynamic y ticks, more x-axis ticks, white background, and black text
fig.update_layout(
    title=dict(
        text=f'<span style="color:red;">{sku_name}</span> in <span style="color:blue;"> Singapore </span>',
        font=dict(family='Times New Roman', size=35),
        x=0.1
    ),
    title_font_color = "black",
    xaxis_title='Date',
    yaxis_title=f'Inventory in {currency} ({currency_symbol})',
    yaxis2_title='Quantity (Cartons)',
    legend_title='Legend',
    legend_font_color="black",
    legend_title_font_color="black",
    xaxis=dict(
        tickmode='array',
        tickvals=x_tick_values,
        ticktext=x_tick_text,
        tickfont=dict(color='black'),  # Set x-axis tick font color to black
        color='black',
        title_font_color="black",
    ),
    yaxis=dict(
        tickformat='~s',  # Use SI unit suffixes, such as "k" for thousands and "M" for millions
        tickfont=dict(color='black'),  # Set y-axis tick font color to black
        color='black',
        title_font_color='black',
    ),
    yaxis2=dict(
        tickfont=dict(color='black'),  # Set y-axis tick font color to black
        color='black',
        title_font_color='black',
        showgrid=False,
    ),
    width=1200,  # Adjust the width as needed
    height=600,
    plot_bgcolor='white',  # Set plot background to white
    paper_bgcolor='white',
    font=dict(
        family="Courier New, monospace",
        size=18,
        color="black"  # Set the overall font color to black
    )
)

# Display the rounded DataFrame
df_sku2 = df_sku[['Name', 'SKU', 'deadstock%', 'Deadstock', 'DFC', 'Forecast_Error', 'Forecast_Error_Std_Dev','Forecast Error (%)', 'average_lead_time', 'lead_time_std_dev', 'Safety_Stock', 'Safety_Stock_days', 'Savings']]

# Format SKU to have no commas
df_sku2['SKU'] = df_sku2['SKU'].apply(lambda x: "{:.0f}".format(x))

# Round the specified columns to integers
columns_to_round = [
    'deadstock%', 'Deadstock', 'DFC', 'Forecast_Error', 'Forecast_Error_Std_Dev', 'Forecast Error (%)',
    'average_lead_time', 'lead_time_std_dev', 'Safety_Stock', 'Safety_Stock_days', 'Savings'
]
df_sku2[columns_to_round] = df_sku2[columns_to_round].applymap(lambda x: round(x) if pd.notnull(x) and np.isfinite(x) else x)


# Rename the specified columns
df_sku2 = df_sku2.rename(columns={
    'deadstock%': 'Deadstock (%)',
    'Deadstock': f'Deadstock ({currency_symbol})',
    'DFC': 'DFC (days)',
    'Forecast_Error': 'Forecast Error',
    'Forecast_Error_Std_Dev': 'Forecast Std Dev',
    'average_lead_time': 'Avg Lead Time (Days)',
    'lead_time_std_dev': 'Lead Time Std Dev',
    'Safety_Stock': f'SS ({currency_symbol})',
    'Safety_Stock_days': 'SS (Days)',
    'Savings': f'Savings ({currency_symbol})',
    'Savings Deadstock': f'Savings Deadstock ({currency_symbol})'
})

# Reset index to remove it
df_sku2 = df_sku2.reset_index(drop=True)
st.data_editor(df_sku2)

# Show the plot in Streamlit
st.plotly_chart(fig, use_container_width=True)
#####

# Ensure specified columns are rounded to the closest integer while keeping NaN values
columns_to_round = ['deadstock%', 'Deadstock', 'DFC', 'average_lead_time', 'lead_time_std_dev', 'Safety_Stock', 'Safety_Stock_days', 'Savings']
df_sku[columns_to_round] = df_sku[columns_to_round].apply(lambda x: pd.to_numeric(x.round(0), errors='coerce', downcast='integer'))

df['SKU'] = df['SKU'].astype(str)

# Remove commas from SKU column
df['SKU'] = df['SKU'].str.replace(',', '')

df['Current_Safety_Stock'] = df['Current_Safety_Stock'].round(-3)
df['Proposed_Safety_Stock'] = df['Proposed_Safety_Stock'].round(-1)
df['Savings'] = df['Savings'].round(-3)
df = df[df['Savings'].notna()]
df['Savings Deadstock'] = df['Savings Deadstock'].round(-3)

###################################
#Daily Simulation with MOQ
###################################


# Create columns
col1, col2, col3 = st.columns(3)

sku_index = 0

# Column 1: Input fields
with col1:
    starting_inventory = st.number_input("Enter Starting Inventory (Value):", value=int(df_sku['Starting_Inventory'].iloc[sku_index]))
    sku_MOQ = st.number_input("Enter MOQ (Quantity):", value=int(df_sku['MOQ'].iloc[sku_index]))
    col1_1, col1_2 = st.columns([1, 1.5])
    with col1_1:
        extension_months = st.selectbox("Extend Months:", options=[0, 1, 2, 3, 4, 5, 6], index=0, key='extension_dropdown')


# Function to simulate inventory over a continuous period
def simulate_inventory_continuous(starting_inventory, daily_consumption_list, safety_stock_list, moq, cogs):
    inventory = starting_inventory
    inventory_levels = []

    for day in range(len(daily_consumption_list)):
        inventory -= daily_consumption_list[day]
        inventory_levels.append(inventory)

        if inventory <= safety_stock_list[day]:
            inventory += moq * cogs

    return inventory_levels

# Generate timelines for daily consumption and safety stocks for each SKU
for i, row in df.iterrows():
    daily_consumption_timeline = (
        [row['Avg_Daily_Consumption_Mar']] * 30 +
        [row['Avg_Daily_Consumption_Apr']] * 30 +
        [row['Avg_Daily_Consumption_May']] * 30 +
        [row['Avg_Daily_Consumption_Jun']] * 30 +
        [row['Avg_Daily_Consumption_Jul']] * 30 +
        [row['Avg_Daily_Consumption_Aug']] * 30
    )

    safety_stock_timeline_proposed = (
        [row['Safety_Stock_Proposed_Mar']] * 30 +
        [row['Safety_Stock_Proposed_Apr']] * 30 +
        [row['Safety_Stock_Proposed_May']] * 30 +
        [row['Safety_Stock_Proposed_Jun']] * 30 +
        [row['Safety_Stock_Proposed_Jul']] * 30 +
        [row['Safety_Stock_Proposed_Aug']] * 30
    )

    safety_stock_timeline_current = (
        [row['Current_Safety_Stock_Mar']] * 30 +
        [row['Current_Safety_Stock_Apr']] * 30 +
        [row['Current_Safety_Stock_May']] * 30 +
        [row['Current_Safety_Stock_Jun']] * 30 +
        [row['Current_Safety_Stock_Jul']] * 30 +
        [row['Current_Safety_Stock_Aug']] * 30
    )

    # Extend the simulation based on user input
    if extension_months > 0:
        daily_consumption_timeline += [row['Avg_Daily_Consumption_Aug']] * 30 * extension_months
        safety_stock_timeline_proposed += [row['Safety_Stock_Proposed_Aug']] * 30 * extension_months
        safety_stock_timeline_current += [row['Current_Safety_Stock_Aug']] * 30 * extension_months

    # Run the simulation for each SKU
    df.at[i, 'Inventory_Timeline_Proposed'] = simulate_inventory_continuous(
        starting_inventory=row['Starting_Inventory'],
        daily_consumption_list=daily_consumption_timeline,
        safety_stock_list=safety_stock_timeline_proposed,
        moq=row['MOQ'],
        cogs=row['COGS']
    )

    df.at[i, 'Inventory_Timeline_Current'] = simulate_inventory_continuous(
        starting_inventory=row['Starting_Inventory'],
        daily_consumption_list=daily_consumption_timeline,
        safety_stock_list=safety_stock_timeline_current,
        moq=row['MOQ'],
        cogs=row['COGS']
    )

# Calculate the average inventory for both proposed and current safety stock levels
df['Average_Inventory_Proposed'] = df['Inventory_Timeline_Proposed'].apply(lambda x: sum(x) / len(x))
df['Average_Inventory_Current'] = df['Inventory_Timeline_Current'].apply(lambda x: sum(x) / len(x))

# Calculate quantities
df['Average_Inventory_Proposed_Quantity'] = df['Average_Inventory_Proposed'] / df['COGS']
df['Average_Inventory_Current_Quantity'] = df['Average_Inventory_Current'] / df['COGS']

# Calculate the change in inventory
df['Change in Inventory Value ($ SGD)'] = df['Average_Inventory_Current'] - df['Average_Inventory_Proposed']
df['Change in Inventory Quantity (Cartons)'] = df['Average_Inventory_Current_Quantity'] - df['Average_Inventory_Proposed_Quantity']

# Calculate the percentage reduction
df['Percentage_Reduction'] = (df['Change in Inventory Quantity (Cartons)'] / df['Average_Inventory_Current_Quantity']) * 100

# Visualization settings and layout
extended_month_names = ['Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar']

# Define y-axis max values for scaling
yaxis_max = max(max(sku_data['Inventory_Timeline_Proposed']), max(sku_data['Inventory_Timeline_Current']))
yaxis2_max = yaxis_max / sku_data['COGS']
# Create a figure with secondary Y-axis
fig = make_subplots(specs=[[{"secondary_y": True}]])
sku_index = 0


# Add the original traces (using the primary Y-axis)
fig.add_trace(
    go.Scatter(
        x=list(range(1, len(inventory_timeline_proposed) + 1)),
        y=inventory_timeline_proposed,
        mode='lines',
        name='Inventory Level (Proposed Safety Stock)',
        line=dict(color='red', dash='dot'),
    ),
    secondary_y=False
)

fig.add_trace(
    go.Scatter(
        x=list(range(1, len(inventory_timeline_current) + 1)),
        y=inventory_timeline_current,
        mode='lines',
        name='Inventory Level (Current Safety Stock)',
        line=dict(color='blue', dash='dash'),
    ),
    secondary_y=False
)

fig.add_trace(
    go.Scatter(
        x=list(range(1, len(safety_stock_timeline_proposed) + 1)),
        y=safety_stock_timeline_proposed,
        mode='lines',
        name='Proposed Safety Stock',
        line=dict(color='red', width=2, dash='dashdot'),
    ),
    secondary_y=False
)

fig.add_trace(
    go.Scatter(
        x=list(range(1, len(safety_stock_timeline_current) + 1)),
        y=safety_stock_timeline_current,
        mode='lines',
        name='Current Safety Stock',
        line=dict(color='blue', width=2, dash='dashdot'),
    ),
    secondary_y=False
)

cogs_value = df_sku['COGS'].iloc[sku_index]  # Retrieve the COGS value for the selected SKU

fig.add_trace(
    go.Scatter(
        x=list(range(1, len(inventory_timeline_proposed) + 1)),
        y=[val / cogs_value for val in inventory_timeline_proposed],
        mode='lines',
        line=dict(color='rgba(0,0,0,0)'),
        showlegend=False  # Hide from legend
    ),
    secondary_y=True
)

fig.add_trace(
    go.Scatter(
        x=list(range(1, len(inventory_timeline_current) + 1)),
        y=[val / cogs_value for val in inventory_timeline_current],
        mode='lines',
        line=dict(color='rgba(0,0,0,0)'),
        showlegend=False  # Hide from legend
    ),
    secondary_y=True
)


extended_month_names = ['Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar']


yaxis_max = max(max(inventory_timeline_proposed), max(inventory_timeline_current))
yaxis2_max = yaxis_max / cogs_value

# Update the layout with Y-axis starting from 0
fig.update_layout(
    title=dict(
        text=f'<span style="color:red;">{sku_name}</span><br><span>Daily Inventory Simulation with MOQ = {sku_MOQ} cartons </span>',
        font=dict(family='Times New Roman', size=35),
        x=0.1
    ),
    title_font_color="black",
    xaxis=dict(
        title='Date',
        tickvals=[1, 30, 60, 90, 120, 150,180] + list(range(210, 210 + 30 * extension_months, 30)),
        ticktext=['Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sept'] + extended_month_names[:extension_months],
        tickfont=dict(color='black'),
        color='black',
        title_font_color="black"
    ),
    yaxis=dict(
        title='Inventory Value (SGD)',
        tickformat='~s',  # Use SI unit suffixes, such as "k" for thousands and "M" for millions
        tickfont=dict(color='black'),
        color='black',
        title_font_color='black',
        range=[0, yaxis_max]  # Ensure Y-axis starts from 0
    ),
    yaxis2=dict(
        title='Inventory Quantity (Cartons)',  # Label this axis as quantity in units
        tickformat='~s',  # Use SI unit suffixes
        tickfont=dict(color='black'),
        color='black',
        title_font_color='black',
        showgrid=False,
        range=[0, yaxis2_max]  # Ensure secondary Y-axis starts from 0
    ),
    legend=dict(
        title='Legend',
        font=dict(color="black"),  # Set legend font color
        title_font=dict(color="black")  # Set legend title font color
    ),
    showlegend=True,
    width=1200,  # Adjust the width as needed
    height=600,
    plot_bgcolor='white',  # Set plot background to white
    paper_bgcolor='white',
    font=dict(
        family="Courier New, monospace",
        size=18,
        color="black"  # Set the overall font color to black
    )
)

# Calculate the average inventory for the current safety stock level
average_inventory_current_value = sum(inventory_timeline_current) / len(inventory_timeline_current) 
average_inventory_current = sum(inventory_timeline_current) / len(inventory_timeline_current) / cogs_value

# Calculate the average inventory for the proposed safety stock level
average_inventory_proposed_value = sum(inventory_timeline_proposed) / len(inventory_timeline_proposed) 
average_inventory_proposed = sum(inventory_timeline_proposed) / len(inventory_timeline_proposed) / cogs_value


# Calculate the percentage reduction
if average_inventory_current != 0:
    percentage_reduction = ((average_inventory_current - average_inventory_proposed) / average_inventory_current) * 100
else:
    percentage_reduction = 0  # Avoid division by zero

 # Function to apply color formatting
def color_change(val):
        background_color = 'lightgreen' if float(val.replace(",", "")) > 0 else 'lightcoral'
        return f'background-color: {background_color}; color: black;'

data = {
    "Metric": [
        "Current Safety Stock Avg. Inventory",
        "Proposed Safety Stock AInventory",
        "Change in Inventory"
    ],
    "$ SGD": [
        f"{average_inventory_current_value:,.0f}",
        f"{average_inventory_proposed_value:,.0f}",
        f"{average_inventory_current_value - average_inventory_proposed_value:,.0f}"
    ],
    "Quantity (Cartons)": [
        f"{average_inventory_current:,.0f}",
        f"{average_inventory_proposed:,.0f}",
        f"{average_inventory_current - average_inventory_proposed:,.0f}"
    ]
}

with col2:
    # Create the main DataFrame with metrics as index
    df_results = pd.DataFrame(data)
    df_results.set_index("Metric", inplace=True)
    st.write("### Inventory Comparison")
    # Apply the color change to the "Change in Inventory" row
    df_styled = df_results.style.applymap(color_change, subset=pd.IndexSlice["Change in Inventory", ["$ SGD", "Quantity (Cartons)"]])
    
    st.dataframe(df_styled)

# Prepare the data for the percentage reduction DataFrame
percentage_reduction_data = {
    "Metric": ["Change in Inventory (%)"],
    "Value": [f"{percentage_reduction:.0f}%"]
}

# Create the percentage reduction DataFrame
df_percentage_reduction = pd.DataFrame(percentage_reduction_data)
df_percentage_reduction.set_index("Metric", inplace=True)
def color_reduction(val):
    background_color = 'lightgreen' if percentage_reduction > 0 else 'lightcoral'
    return f'background-color: {background_color}; color: black;'
        
with col3:
    df_percentage_reduction_styled = df_percentage_reduction.style.applymap(color_reduction)
    # Display the styled DataFrame
    st.write("### Percentage Change")
    st.dataframe(df_percentage_reduction_styled)
    
# Display the figure in Streamlit
st.plotly_chart(fig, use_container_width=True)

##############################



# Initialize the session state for the data editor key
if 'dek' not in ss:
    ss.dek = str(uuid.uuid4())

def update_value():
    """Update the key to refresh the data editor."""
    ss.dek = str(uuid.uuid4())  # triggers reset

# Function to recalculate proposed safety stock and savings
def recalculate_safety_and_savings(row):
    new_service_level = row['Service_Level']
    SKU = row['SKU']
    df_sku = df[df['SKU'] == SKU]

    if not df_sku.empty:
        old_service_level = df_sku['Service_Level'].values[0]
        old_safety_factor = stats.norm.ppf(old_service_level)
        new_safety_factor = stats.norm.ppf(new_service_level)

        # Recalculate Proposed_Safety_Stock and Savings
        proposed_safety_stock = df_sku['Proposed_Safety_Stock'].values[0] / old_safety_factor * new_safety_factor
        savings = df_sku['Current_Safety_Stock'].values[0] - proposed_safety_stock

        # Update the main dataframe
        df.loc[df['SKU'] == SKU, 'Proposed_Safety_Stock'] = proposed_safety_stock
        df.loc[df['SKU'] == SKU, 'Savings'] = savings
        return proposed_safety_stock, savings


df = df[df['brand'].isin(selected_brands)]
df = df[df[filter_column] >= filter_value]
df = df.sort_values(by=sort_column, ascending=sort_ascending)


# Display the table
df = df.head(num_rows)

df = df.rename(columns={
    'Safety_Stock_bus_days': 'Safety_Days',
    'Current_Safety_Stock_bus_days': 'Current_Safety_Days',
    'days_diff': 'Days_Diff'
})

# Calculate weighted values for the safety days columns based on Actuals_P3M
df['Weighted_Current_Safety_Days'] = df['Actuals_P3M'] * df['Current_Safety_Days']
df['Weighted_Proposed_Safety_Days'] = df['Actuals_P3M'] * df['Safety_Days']
df['Weighted_Days_Diff'] = df['Weighted_Current_Safety_Days'] - df['Weighted_Proposed_Safety_Days']

# Calculate weighted values for lead time and forecast error columns
df['Weighted_Forecast_Error'] = df['Actuals_P3M'] * df['Forecast_Error']
df['Weighted_Forecast_Error_Std_Dev'] = df['Actuals_P3M'] * df['Forecast_Error_Std_Dev']
df['Weighted_Average_Lead_Time'] = df['Actuals_P3M'] * df['average_lead_time']
df['Weighted_Lead_Time_Std_Dev'] = df['Actuals_P3M'] * df['lead_time_std_dev']
df['Forecast_P3M'] = df[['Forecast_Apr', 'Forecast_May','Forecast_Jun']].mean(axis=1)

# Sum for forecast error and lead time metrics
total_current_safety_stock = df['Current_Safety_Stock'].sum()
total_proposed_safety_stock = df['Proposed_Safety_Stock'].sum()
total_savings = df['Savings'].sum()
total_weighted_current_safety_days = df['Weighted_Current_Safety_Days'].sum()
total_weighted_proposed_safety_days = df['Weighted_Proposed_Safety_Days'].sum()
total_weighted_days_diff = df['Weighted_Days_Diff'].sum()
total_actuals_p3m = df['Actuals_P3M'].sum()
total_weighted_forecast_error = df['Weighted_Forecast_Error'].sum()
total_weighted_forecast_error_std_dev = df['Weighted_Forecast_Error_Std_Dev'].sum()
total_weighted_average_lead_time = df['Weighted_Average_Lead_Time'].sum()
total_weighted_lead_time_std_dev = df['Weighted_Lead_Time_Std_Dev'].sum()

# Calculate the weighted averages
average_current_safety_days = total_weighted_current_safety_days / total_actuals_p3m
average_proposed_safety_days = total_weighted_proposed_safety_days / total_actuals_p3m
average_days_diff = total_weighted_days_diff / total_actuals_p3m
average_forecast_error = total_weighted_forecast_error / total_actuals_p3m
average_forecast_error_std_dev = total_weighted_forecast_error_std_dev / total_actuals_p3m
average_lead_time = total_weighted_average_lead_time / total_actuals_p3m
average_lead_time_std_dev = total_weighted_lead_time_std_dev / total_actuals_p3m
forecast_error_percentage = df['Forecast_Error'].sum() /df['Forecast_P3M'].sum()

# Create the final row for the overall totals and weighted averages
final_row_forecast_lead_time = pd.DataFrame([{
    'Name': 'Overall',
    'Savings': total_savings,
    'Safety_Days': round(average_proposed_safety_days, 0),  # No conversion needed
    'Days_Diff': round(average_current_safety_days - average_proposed_safety_days, 0),
    'Forecast_Error': round(average_forecast_error, -3),
    'Forecast_Error_%': round(forecast_error_percentage * 100, 2),
    'Forecast_Error_Std_Dev': round(average_forecast_error_std_dev, -3),
    'average_lead_time': round(average_lead_time, 0),
    'lead_time_std_dev': round(average_lead_time_std_dev, 0)
}])

st.subheader("Overall Summary of Top {} SKU Analysis with greater than {}% Deadstock".format(num_rows, filter_value))
# Display the table with weighted values for forecast and lead time
st.data_editor(final_row_forecast_lead_time)
df['Forecast_Error_qty'] = df['Forecast_Error']/df['COGS']
# Filter and sort the dataframe
# sorted_df_head = df.dropna(subset=['Savings'])
sorted_df_head = df.copy()
sorted_df = sorted_df_head.reset_index(drop=True)
sorted_df.index = sorted_df.index + 1
sorted_df = sorted_df.sort_values(by='Savings', ascending=False)

st.subheader("Planner Summary")

df['Savings'] = df['Current_Safety_Stock'] - df['Proposed_Safety_Stock']
df['Savings Deadstock'] = df['Deadstock'] - df['Current_Safety_Stock']


sorted_df['Current_Safety_Stock_Qty'] = sorted_df['Current_Safety_Stock']/sorted_df['COGS']
sorted_df['Proposed_Safety_Stock_Qty'] = sorted_df['Proposed_Safety_Stock']/sorted_df['COGS']
sorted_df['Savings_Qty']=sorted_df['Current_Safety_Stock_Qty']-sorted_df['Proposed_Safety_Stock_Qty']

sorted_df[['Name', 'SKU', 'ABC','Service_Level', 'Current_Safety_Stock_Qty','Proposed_Safety_Stock_Qty','Savings_Qty', 'Current_Safety_Days', 'Safety_Days', 'Days_Diff','Forecast_Error_qty','Forecast_Error_Std_Dev', 'Forecast Error (%)','average_lead_time','lead_time_std_dev','Current_Safety_Stock', 'Proposed_Safety_Stock', 'Savings', 'Deadstock','deadstock%']]


# Allow user to edit service levels
edited_df = st.data_editor(sorted_df[['Name', 'SKU', 'ABC','Service_Level', 'Current_Safety_Stock', 'Proposed_Safety_Stock', 'Savings','Savings Deadstock', 'Current_Safety_Days', 'Safety_Days', 'Days_Diff']].reset_index(drop=True), num_rows='dynamic', key=ss.dek)


# Recalculate based on edited service levels
for idx, row in edited_df.iterrows():
    new_service_level = row['Service_Level']
    SKU = row['SKU']
    df_sku = df[df['SKU'] == SKU]

    if not df_sku.empty:
        old_service_level = df_sku['Service_Level'].values[0]
        old_safety_factor = stats.norm.ppf(old_service_level)
        new_safety_factor = stats.norm.ppf(new_service_level)

        # Recalculate Proposed_Safety_Stock and Savings
        proposed_safety_stock = df_sku['Proposed_Safety_Stock'].values[0] / old_safety_factor * new_safety_factor
        savings = df_sku['Current_Safety_Stock'].values[0] - proposed_safety_stock

        # Recalculate Safety Stock days and business days
        average_fc_future_3m = df_sku['Average_FC_Future_3M'].values[0]
        safety_stock_days = proposed_safety_stock / average_fc_future_3m * 30
        safety_stock_bus_days = round(proposed_safety_stock / average_fc_future_3m * 21.4, 0)
        current_safety_stock_bus_days = df_sku['Current_Safety_Days'].values[0]
        days_diff = round(current_safety_stock_bus_days - safety_stock_bus_days, 0)

        # Update the main dataframe
        df.loc[df['SKU'] == SKU, 'Proposed_Safety_Stock'] = round(proposed_safety_stock, -3)
        df.loc[df['SKU'] == SKU, 'Savings'] = round(savings, -3)
        df.loc[df['SKU'] == SKU, 'Savings Deadstock'] = round(savings, -3)
        df.loc[df['SKU'] == SKU, 'Safety_Stock_days'] = safety_stock_days
        df.loc[df['SKU'] == SKU, 'Safety_Stock_bus_days'] = safety_stock_bus_days
        df.loc[df['SKU'] == SKU, 'Current_Safety_Stock_bus_days'] = current_safety_stock_bus_days
        df.loc[df['SKU'] == SKU, 'days_diff'] = days_diff

        edited_df.at[idx, 'Proposed_Safety_Stock'] = round(proposed_safety_stock, -3)
        edited_df.at[idx, 'Savings'] = round(savings, -3)
        edited_df.at[idx, 'Savings Deadstock'] = round(savings, -3)
        edited_df.at[idx, 'Safety_Days'] = safety_stock_bus_days
        edited_df.at[idx, 'Current_Safety_Days'] = current_safety_stock_bus_days
        edited_df.at[idx, 'Days_Diff'] = days_diff


# Calculate total savings
total_savings = round(sorted_df['Savings'].sum(), -3)
total_savings_deadstock = round(sorted_df['Savings Deadstock'].sum(), -3)
st.write(f"**Total {currency} Savings:** {total_savings:,.0f} {currency_symbol}")

styled_df = edited_df.style.applymap(lambda x: 'background-color: lightgreen; color: black;' if x > 0 else 'background-color: lightcoral; color: black;', subset=['Savings', 'Days_Diff'])
styled_df = styled_df.format({
    'Service_Level': '{:.2f}',
    'Savings': '{:.0f}',
    'Current_Safety_Stock': '{:.0f}',
    'Proposed_Safety_Stock': '{:.0f}',
    'Savings Deadstock': '{:.0f}', 
    'Current_Safety_Days': '{:.0f}', 
    'Safety_Days': '{:.0f}', 
    'Days_Diff': '{:.0f}'
})
# Display the styled DataFrame using st.dataframe
st.dataframe(styled_df)
total_savings = round(edited_df['Savings'].sum(), -3)
total_savings_deadstock = round(sorted_df['Savings Deadstock'].sum(), -3)
st.write(f"**Total {currency} Savings:** {total_savings:,.0f} {currency_symbol}")

# Convert dataframe to CSV
csv = edited_df.head(num_rows).to_csv(index=False).encode('utf-8')

# Convert dataframe to Excel
excel = to_excel(edited_df.head(num_rows))

# Display download buttons with icons
col1, col2 = st.columns(2)

with col1:
    st.markdown(
        f'<img src="data:image/png;base64,{excel_icon}" width="30" height="30" style="vertical-align: middle; margin-right: 10px;">',
        unsafe_allow_html=True,
    )
    st.download_button(
        label="Download data as Excel",
        data=excel,
        file_name='overall_summary.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        key='download_excel'
    )
with col2:
    st.markdown(
        f'<img src="data:image/png;base64,{csv_icon}" width="30" height="30" style="vertical-align: middle; margin-right: 10px;">',
        unsafe_allow_html=True,
    )
    st.download_button(
        label="Download data as CSV",
        data=csv,
        file_name='overall_summary.csv',
        mime='text/csv',
        key='download_csv'
    )

st.button("Reset", on_click=update_value, key='reset_button')

