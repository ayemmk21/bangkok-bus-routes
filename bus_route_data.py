import pandas as pd
import geopandas as gpd

# Load and inspect your data
gdf = gpd.read_file('bangkok_bus_routes_20250927_163403.geojson')
df = pd.read_csv('bangkok_bus_routes_info_20250927_163403.csv')

# Check data quality
print(f"Total routes: {len(gdf)}")
print(f"Routes missing names: {sum(gdf['name'] == 'Unknown')}")
print(f"Routes missing ref numbers: {sum(gdf['ref'] == 'Unknown')}")
print(f"Average coordinates per route: {gdf['coord_count'].mean()}")
print(gdf)