#!/usr/bin/env python3
"""
Bangkok Bus Route Extraction from OpenStreetMap
This script extracts bus route data from OSM and saves it as GeoJSON
"""

import overpy
import geopandas as gpd
from shapely.geometry import LineString
import json
import pandas as pd
import os
from datetime import datetime

def extract_bangkok_bus_routes():
    """
    Extract Bangkok bus routes from OpenStreetMap using Overpass API
    """
    print("Initializing Overpass API connection...")
    api = overpy.Overpass()
    
    # Define Bangkok bounding box (approximate)
    # SW: 13.4942, 100.3234 NE: 13.9562, 100.9006
    bbox = "13.4942,100.3234,13.9562,100.9006"
    
    # Comprehensive query for Bangkok bus routes
    query = f"""
    [out:json][timeout:300][bbox:{bbox}];
    (
      relation["type"="route"]["route"="bus"];
      relation["type"="route_master"]["route_master"="bus"];
    );
    (._;>;);
    out geom;
    """
    
    print("Querying OpenStreetMap for Bangkok bus routes...")
    print("This may take several minutes...")
    
    try:
        result = api.query(query)
        print(f"Found {len(result.relations)} route relations")
        
    except Exception as e:
        print(f"Error querying OSM: {e}")
        print("Trying simplified query...")
        
        # Fallback to simpler query
        simple_query = f"""
        [out:json][timeout:180][bbox:{bbox}];
        relation["route"="bus"];
        out geom;
        """
        result = api.query(simple_query)
        print(f"Found {len(result.relations)} route relations with simple query")
    
    return result

def process_route_data(result):
    """
    Process the OSM query result into structured route data
    """
    routes = []
    processed_count = 0
    
    print("Processing route data...")
    
    for relation in result.relations:
        try:
            route_data = {
                'route_id': relation.id,
                'name': relation.tags.get('name', 'Unknown'),
                'ref': relation.tags.get('ref', 'Unknown'),
                'from': relation.tags.get('from', ''),
                'to': relation.tags.get('to', ''),
                'operator': relation.tags.get('operator', ''),
                'network': relation.tags.get('network', ''),
                'route_type': relation.tags.get('route', ''),
                'coordinates': []
            }
            
            # Extract coordinates from way members
            coord_count = 0
            for member in relation.members:
                if hasattr(member, 'resolve') and member.resolve():
                    resolved_member = member.resolve()
                    
                    if hasattr(resolved_member, 'nd'):
                        # This is a way with nodes
                        for node in resolved_member.nd:
                            if hasattr(node, 'lat') and hasattr(node, 'lon'):
                                route_data['coordinates'].append([float(node.lon), float(node.lat)])
                                coord_count += 1
                    elif hasattr(resolved_member, 'lat') and hasattr(resolved_member, 'lon'):
                        # This is a node
                        route_data['coordinates'].append([float(resolved_member.lon), float(resolved_member.lat)])
                        coord_count += 1
            
            # Only keep routes with sufficient coordinate data
            if coord_count > 2:
                routes.append(route_data)
                processed_count += 1
                
                if processed_count % 10 == 0:
                    print(f"Processed {processed_count} routes...")
                    
        except Exception as e:
            print(f"Error processing route {relation.id}: {e}")
            continue
    
    print(f"Successfully processed {len(routes)} routes")
    return routes

def create_geodataframe(routes):
    """
    Convert processed routes into a GeoPandas GeoDataFrame
    """
    print("Creating GeoDataFrame...")
    
    geometries = []
    route_info = []
    
    for route in routes:
        if len(route['coordinates']) > 1:
            try:
                # Create LineString geometry
                line = LineString(route['coordinates'])
                geometries.append(line)
                
                # Store route metadata
                route_info.append({
                    'route_id': route['route_id'],
                    'name': route['name'],
                    'ref': route['ref'],
                    'from_stop': route['from'],
                    'to_stop': route['to'],
                    'operator': route['operator'],
                    'network': route['network'],
                    'route_type': route['route_type'],
                    'coord_count': len(route['coordinates'])
                })
                
            except Exception as e:
                print(f"Error creating geometry for route {route['route_id']}: {e}")
                continue
    
    if not geometries:
        print("Warning: No valid geometries created")
        return None
    
    # Create GeoDataFrame
    gdf = gpd.GeoDataFrame(route_info, geometry=geometries, crs='EPSG:4326')
    print(f"Created GeoDataFrame with {len(gdf)} routes")
    
    return gdf

def save_data(gdf, routes_raw):
    """
    Save the extracted data in multiple formats
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if gdf is not None and not gdf.empty:
        # Save as GeoJSON
        geojson_filename = f'bangkok_bus_routes_{timestamp}.geojson'
        gdf.to_file(geojson_filename, driver='GeoJSON')
        print(f"Saved GeoJSON: {geojson_filename}")
        
        # Save as CSV (without geometry for easy viewing)
        csv_filename = f'bangkok_bus_routes_info_{timestamp}.csv'
        route_df = gdf.drop('geometry', axis=1)
        route_df.to_csv(csv_filename, index=False)
        print(f"Saved CSV: {csv_filename}")
        
        # Print summary statistics
        print("\n=== DATA SUMMARY ===")
        print(f"Total routes extracted: {len(gdf)}")
        print(f"Routes with names: {len(gdf[gdf['name'] != 'Unknown'])}")
        print(f"Routes with reference numbers: {len(gdf[gdf['ref'] != 'Unknown'])}")
        print(f"Unique operators: {gdf['operator'].nunique()}")
        print(f"Unique networks: {gdf['network'].nunique()}")
        
        # Show sample of extracted routes
        print("\n=== SAMPLE ROUTES ===")
        sample_df = gdf[['ref', 'name', 'from_stop', 'to_stop', 'operator']].head(10)
        print(sample_df.to_string(index=False))
    
    # Save raw data as backup
    raw_filename = f'bangkok_bus_routes_raw_{timestamp}.json'
    with open(raw_filename, 'w', encoding='utf-8') as f:
        json.dump(routes_raw, f, ensure_ascii=False, indent=2)
    print(f"Saved raw data: {raw_filename}")

def main():
    """
    Main execution function
    """
    print("Bangkok Bus Route Extraction from OpenStreetMap")
    print("=" * 50)
    
    try:
        # Step 1: Extract data from OSM
        result = extract_bangkok_bus_routes()
        
        # Step 2: Process the raw data
        routes = process_route_data(result)
        
        if not routes:
            print("No routes found. Check your internet connection and try again.")
            return
        
        # Step 3: Create GeoDataFrame and save
        gdf = create_geodataframe(routes)
        save_data(gdf, routes)
        
        print("\n=== EXTRACTION COMPLETE ===")
        print("Files saved successfully!")
        print("\nNext steps:")
        print("1. Review the CSV file to see extracted route information")
        print("2. Load the GeoJSON file in QGIS or similar GIS software for visualization")
        print("3. Check data quality and fill in missing information as needed")
        
    except Exception as e:
        print(f"Fatal error: {e}")
        print("Please check your internet connection and try again.")

if __name__ == "__main__":
    # Check if required packages are installed
    try:
        import overpy
        import geopandas
        import shapely
    except ImportError as e:
        print("Missing required packages. Please install:")
        print("pip install overpy geopandas shapely")
        exit(1)
    
    main()