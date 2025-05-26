import streamlit as st
import prettymaps
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw
import json
import requests
import os
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import io
import base64
import osmnx as ox
import geopandas as gpd
from shapely.geometry import box
import warnings
import re

# Suppress specific warnings
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)

# Load environment variables
load_dotenv()

# Set page config
st.set_page_config(
    page_title="PrettyMapAI",
    page_icon="🗺️",
    layout="wide"
)

# Initialize session state
if 'selected_area' not in st.session_state:
    st.session_state.selected_area = None
if 'generated_maps' not in st.session_state:
    st.session_state.generated_maps = []

def analyze_osm_area(area_bounds):
    """Analyze the area using OpenStreetMap data"""
    try:
        # Create a bounding box
        bbox = box(area_bounds['west'], area_bounds['south'], 
                  area_bounds['east'], area_bounds['north'])
        
        # Get buildings
        buildings = ox.geometries_from_bbox(
            area_bounds['north'], area_bounds['south'],
            area_bounds['east'], area_bounds['west'],
            tags={'building': True}
        )
        
        # Get streets
        streets = ox.graph_from_bbox(
            area_bounds['north'], area_bounds['south'],
            area_bounds['east'], area_bounds['west'],
            network_type='all'
        )
        
        # Get natural features
        natural = ox.geometries_from_bbox(
            area_bounds['north'], area_bounds['south'],
            area_bounds['east'], area_bounds['west'],
            tags={'natural': True}
        )
        
        # Get amenities
        amenities = ox.geometries_from_bbox(
            area_bounds['north'], area_bounds['south'],
            area_bounds['east'], area_bounds['west'],
            tags={'amenity': True}
        )
        
        # Analyze the data
        analysis = {
            'area_size': bbox.area * 111319.9,  # Convert to square meters
            'building_count': len(buildings),
            'street_count': len(streets.edges),
            'natural_features': {
                'water': len(natural[natural['natural'] == 'water']),
                'wood': len(natural[natural['natural'] == 'wood']),
                'park': len(natural[natural['natural'] == 'park'])
            },
            'amenities': {
                'commercial': len(amenities[amenities['amenity'].isin(['restaurant', 'cafe', 'shop'])]),
                'public': len(amenities[amenities['amenity'].isin(['school', 'hospital', 'library'])]),
                'leisure': len(amenities[amenities['amenity'].isin(['sports_centre', 'stadium', 'swimming_pool'])])
            },
            'street_types': {
                'primary': len([e for e in streets.edges if streets.edges[e].get('highway') == 'primary']),
                'secondary': len([e for e in streets.edges if streets.edges[e].get('highway') == 'secondary']),
                'residential': len([e for e in streets.edges if streets.edges[e].get('highway') == 'residential'])
            }
        }
        
        return analysis
    except Exception as e:
        st.error(f"Error analyzing OSM data: {str(e)}")
        return None

def clean_json_string(json_str):
    """Clean and fix common JSON formatting issues"""
    try:
        # Remove any text before the first [ and after the last ]
        json_str = re.sub(r'^[^[]*\[', '[', json_str)
        json_str = re.sub(r'\][^]]*$', ']', json_str)
        
        # Replace single quotes with double quotes
        json_str = json_str.replace("'", '"')
        
        # Ensure property names are in double quotes
        json_str = re.sub(r'([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', json_str)
        
        # Remove trailing commas
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        
        # Fix boolean values
        json_str = json_str.replace('true', 'true')
        json_str = json_str.replace('false', 'false')
        
        # Fix missing commas between objects in arrays
        json_str = re.sub(r'}\s*{', '},{', json_str)
        
        # Fix missing commas between key-value pairs
        json_str = re.sub(r'"\s*"\s*:', '",":', json_str)
        
        # Remove any whitespace between brackets and content
        json_str = re.sub(r'{\s+', '{', json_str)
        json_str = re.sub(r'\s+}', '}', json_str)
        json_str = re.sub(r'\[\s+', '[', json_str)
        json_str = re.sub(r'\s+\]', ']', json_str)
        
        # Ensure proper array formatting
        json_str = re.sub(r'\[\s*\]', '[]', json_str)
        json_str = re.sub(r'{\s*}', '{}', json_str)
        
        # Fix any remaining delimiter issues
        json_str = re.sub(r',\s*,', ',', json_str)  # Remove duplicate commas
        json_str = re.sub(r',\s*}', '}', json_str)  # Remove trailing commas before closing braces
        json_str = re.sub(r',\s*]', ']', json_str)  # Remove trailing commas before closing brackets
        
        return json_str
    except Exception as e:
        st.error(f"Error cleaning JSON string: {str(e)}")
        return None

def get_ai_analysis(area_bounds, osm_analysis):
    """Get AI analysis for the selected area using OpenRouter API"""
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
    
    prompt = f"""
    You are a map visualization expert. Analyze this geographic area with the following characteristics:

    Area Size: {osm_analysis['area_size']:.2f} square meters
    Building Count: {osm_analysis['building_count']}
    Street Count: {osm_analysis['street_count']}

    Natural Features:
    - Water bodies: {osm_analysis['natural_features']['water']}
    - Woods: {osm_analysis['natural_features']['wood']}
    - Parks: {osm_analysis['natural_features']['park']}

    Amenities:
    - Commercial: {osm_analysis['amenities']['commercial']}
    - Public: {osm_analysis['amenities']['public']}
    - Leisure: {osm_analysis['amenities']['leisure']}

    Street Types:
    - Primary: {osm_analysis['street_types']['primary']}
    - Secondary: {osm_analysis['street_types']['secondary']}
    - Residential: {osm_analysis['street_types']['residential']}

    Based on these characteristics, suggest PrettyMaps parameters for three different map styles.
    Return ONLY a JSON array with exactly 3 objects, no other text. Each object must follow this exact structure.
    Make sure all property names and string values are enclosed in double quotes.
    Do not include any comments or trailing commas.
    Ensure proper comma placement between objects and key-value pairs.

    Example structure (modify the values, keep the structure):
    [
        {{
            "layers": {{
                "perimeter": {{}},
                "streets": {{
                    "width": {{
                        "motorway": 6,
                        "trunk": 5,
                        "primary": 4.5,
                        "secondary": 4,
                        "tertiary": 3.5,
                        "residential": 3,
                        "path": 2
                    }}
                }},
                "waterway": {{
                    "tags": {{"waterway": ["river", "stream"]}},
                    "width": {{"river": 20, "stream": 10}}
                }},
                "building": {{
                    "tags": {{
                        "building": true,
                        "leisure": ["park", "garden"],
                        "natural": ["wood", "water"]
                    }}
                }},
                "water": {{
                    "tags": {{"natural": ["water", "bay"]}}
                }},
                "green": {{
                    "tags": {{
                        "landuse": ["grass", "orchard"],
                        "natural": ["island", "wood", "wetland"],
                        "leisure": "park"
                    }}
                }}
            }},
            "style": {{
                "perimeter": {{
                    "fill": false,
                    "lw": 0,
                    "zorder": 0
                }},
                "background": {{
                    "fc": "#F2F4CB",
                    "zorder": -1
                }},
                "green": {{
                    "fc": "#8BB174",
                    "ec": "#2F3737",
                    "hatch_c": "#A7C497",
                    "hatch": "ooo...",
                    "lw": 1,
                    "zorder": 1
                }},
                "water": {{
                    "fc": "#a8e1e6",
                    "ec": "#2F3737",
                    "hatch_c": "#9bc3d4",
                    "hatch": "ooo...",
                    "lw": 1,
                    "zorder": 99
                }},
                "streets": {{
                    "fc": "#2F3737",
                    "ec": "#475657",
                    "alpha": 1,
                    "lw": 0,
                    "zorder": 4
                }},
                "building": {{
                    "palette": ["#433633", "#FF5E5B"],
                    "ec": "#2F3737",
                    "lw": 0.5,
                    "zorder": 5
                }}
            }},
            "circle": true,
            "radius": 1500,
            "dilate": 0,
            "figsize": [12, 12],
            "scale_x": 1,
            "scale_y": 1,
            "adjust_aspect_ratio": true,
            "keypoints": {{
                "tags": {{"natural": ["beach", "peak"]}},
                "specific": {{
                    "central park": {{"tags": {{"leisure": "park"}}}}
                }}
            }}
        }}
    ]

    Return ONLY the JSON array, no other text or explanation.
    """
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "mistralai/mistral-7b-instruct",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data
        )
        response.raise_for_status()
        
        # Extract the content from the response
        content = response.json()['choices'][0]['message']['content'].strip()
        
        # Try to find JSON in the response
        try:
            # First try direct JSON parsing
            return json.loads(content)
        except json.JSONDecodeError:
            # If that fails, try to extract JSON from the text
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                try:
                    # Try parsing the extracted JSON
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    # If still fails, try cleaning the JSON
                    cleaned_json = clean_json_string(json_match.group())
                    if cleaned_json:
                        try:
                            return json.loads(cleaned_json)
                        except json.JSONDecodeError as e:
                            st.error(f"Could not parse JSON after cleaning: {str(e)}")
                            # Print the problematic JSON for debugging
                            st.code(cleaned_json, language='json')
                            return None
                    else:
                        st.error("Failed to clean JSON string")
                        return None
            else:
                st.error("Could not find JSON array in the AI response")
                return None
                
    except Exception as e:
        st.error(f"Error getting AI analysis: {str(e)}")
        return None

def generate_map(area_bounds, params):
    """Generate a map using PrettyMaps with given parameters"""
    try:
        # Calculate center point from bounds
        center_lat = (area_bounds['north'] + area_bounds['south']) / 2
        center_lon = (area_bounds['east'] + area_bounds['west']) / 2
        
        # Create the plot
        plot = prettymaps.plot(
            (center_lat, center_lon),
            radius=params.get('radius', 1000),
            layers=params.get('layers', {}),
            style=params.get('style', {}),
            figsize=(12, 12)
        )
        
        # Convert plot to image
        buf = io.BytesIO()
        plot.fig.savefig(buf, format='png', bbox_inches='tight', dpi=300)
        buf.seek(0)
        return buf
    except Exception as e:
        st.error(f"Error generating map: {str(e)}")
        return None

def main():
    st.title("🗺️ PrettyMapAI")
    st.write("Draw an area on the map to generate beautiful visualizations using AI-powered PrettyMaps!")
    
    # Create two columns for the layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Create a map centered on a default location
        m = folium.Map(location=[0, 0], zoom_start=2)
        
        # Add drawing tools
        draw = Draw(
            draw_options={
                'polyline': False,
                'polygon': True,
                'circle': False,
                'rectangle': True,
                'marker': False,
                'circlemarker': False,
            }
        )
        draw.add_to(m)
        
        # Display the map using st_folium
        map_data = st_folium(m, width=600, height=400)
    
    with col2:
        if map_data and map_data.get('last_active_drawing'):
            drawn_features = map_data['last_active_drawing']
            
            # Extract bounds from the drawn area
            bounds = drawn_features['geometry']['coordinates'][0]
            area_bounds = {
                'north': max(coord[1] for coord in bounds),
                'south': min(coord[1] for coord in bounds),
                'east': max(coord[0] for coord in bounds),
                'west': min(coord[0] for coord in bounds)
            }
            
            # Add a prominent button
            if st.button("🎨 Generate Beautiful Maps", use_container_width=True):
                with st.spinner("Analyzing area and generating maps..."):
                    # First analyze the OSM data
                    osm_analysis = analyze_osm_area(area_bounds)
                    
                    if osm_analysis:
                        # Show area analysis in a more subtle way
                        with st.expander("Area Analysis", expanded=False):
                            cols = st.columns(2)
                            with cols[0]:
                                st.metric("Area Size", f"{osm_analysis['area_size']/1000000:.2f} km²")
                                st.metric("Buildings", osm_analysis['building_count'])
                                st.metric("Streets", osm_analysis['street_count'])
                            with cols[1]:
                                st.metric("Water Bodies", osm_analysis['natural_features']['water'])
                                st.metric("Parks", osm_analysis['natural_features']['park'])
                                st.metric("Amenities", sum(osm_analysis['amenities'].values()))
                        
                        # Get AI analysis with OSM data
                        ai_params = get_ai_analysis(area_bounds, osm_analysis)
                        
                        if ai_params:
                            # Generate maps for each parameter set
                            for i, params in enumerate(ai_params):
                                st.subheader(f"Map Style {i+1}")
                                map_image = generate_map(area_bounds, params)
                                
                                if map_image:
                                    # Display the map
                                    st.image(map_image, use_container_width=True)
                                    
                                    # Add download button
                                    btn = st.download_button(
                                        label=f"Download Map {i+1}",
                                        data=map_image,
                                        file_name=f"pretty_map_{i+1}.png",
                                        mime="image/png",
                                        use_container_width=True
                                    )
        else:
            st.info("👆 Draw an area on the map to get started!")

if __name__ == "__main__":
    main() 