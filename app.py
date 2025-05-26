import streamlit as st
import prettymaps
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw, Geocoder
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
from stqdm import stqdm

# Suppress specific warnings
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)

# Load environment variables
load_dotenv()

# Set page config
st.set_page_config(
    page_title="PrettyMapAI",
    page_icon="🗺️",
    layout="centered"
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
        
        # Replace 'NULL' with null
        json_str = re.sub(r'\bNULL\b', 'null', json_str, flags=re.IGNORECASE)
        
        # Replace 'tag' with 'tags' (only as a key)
        json_str = re.sub(r'"tag"\s*:', '"tags":', json_str)
        
        # Convert numeric-keyed dicts to lists (e.g., {"0": "river", "1": "stream"} -> ["river", "stream"])
        def fix_numeric_keys(match):
            items = match.group(1)
            # Find all "number": value pairs
            pairs = re.findall(r'"(\\d+)":\s*([\[\]{}"a-zA-Z0-9_.:-]+)', items)
            values = [v.strip('"') for _, v in pairs]
            return '[' + ', '.join(f'"{v}"' for v in values) + ']'
        # Replace all dicts with only numeric keys with lists
        json_str = re.sub(r'\{((?:\s*"\\d+":\s*[^,}]+,?)+)\}', fix_numeric_keys, json_str)
        
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
        
        # Count opening and closing brackets to fix incomplete JSON
        open_braces = json_str.count('{')
        close_braces = json_str.count('}')
        open_brackets = json_str.count('[')
        close_brackets = json_str.count(']')
        
        # Add missing closing brackets
        if open_braces > close_braces:
            json_str += '}' * (open_braces - close_braces)
        if open_brackets > close_brackets:
            json_str += ']' * (open_brackets - close_brackets)
        
        # Ensure the JSON has the required structure
        required_keys = ['layers', 'style', 'circle', 'radius', 'figsize']
        try:
            data = json.loads(json_str)
            if not isinstance(data, list):
                json_str = f'[{json_str}]'
            data = json.loads(json_str)
            
            # Validate each object in the array
            valid_objects = []
            for obj in data:
                if all(key in obj for key in required_keys):
                    valid_objects.append(obj)
            
            if valid_objects:
                return json.dumps(valid_objects)
            else:
                st.error("No valid objects found in JSON")
                st.code(json_str, language='json')
                return None
                
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON structure after cleaning: {str(e)}")
            st.code(json_str, language='json')
            return None
            
        return json_str
    except Exception as e:
        st.error(f"Error cleaning JSON string: {str(e)}")
        st.code(json_str, language='json')
        return None

def get_ai_analysis(area_bounds, osm_analysis, user_prompt):
    """Get AI analysis for the selected area using OpenRouter API"""
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
    
    system_message = """You are a map visualization expert. Your task is to generate exactly two different map styles for a given area based on the user's description.
    You must always return a JSON array containing exactly two objects, each with a unique style.
    Do not return any text before or after the JSON array.
    Each style must be significantly different from the other in terms of colors, patterns, and visual elements."""
    
    prompt = f"""
    Generate exactly two different map styles for this geographic area based on the user's description: "{user_prompt}"

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

    Create two DISTINCT styles that best match the user's description while being different from each other.
    Consider different approaches to:
    - Color palettes
    - Line weights
    - Patterns
    - Background colors
    - Building styles
    - Street emphasis

    Return ONLY a JSON array with exactly 2 objects. Each object must include:
    - name: A short descriptive name for the style
    - layers: All required layer configurations
    - style: All style parameters
    - circle: true/false
    - radius: number
    - figsize: [width, height]
    - scale_x: number
    - scale_y: number
    - adjust_aspect_ratio: true/false

    Example structure (modify the values, keep the structure):
    [
        {{
            "name": "Style Name",
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
        "model": "deepseek/deepseek-chat-v3-0324:free",
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "stream": False  # Ensure we get the complete response
    }
    
    try:
        # Show progress while waiting for AI response
        progress = st.empty()
        progress.info("🤖 Waiting for AI to generate map styles...")
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=60  # 60 second timeout
        )
        response.raise_for_status()
        
        # Extract the content from the response
        content = response.json()['choices'][0]['message']['content'].strip()
        
        # Try to find JSON in the response
        try:
            # First try direct JSON parsing
            data = json.loads(content)
            if not isinstance(data, list) or len(data) != 2:
                st.error("AI response did not contain exactly 2 map styles")
                st.code(content, language='json')
                return None
            return data
        except json.JSONDecodeError:
            # If that fails, try to extract JSON from the text
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                try:
                    # Try parsing the extracted JSON
                    data = json.loads(json_match.group())
                    if not isinstance(data, list) or len(data) != 2:
                        st.error("AI response did not contain exactly 2 map styles")
                        st.code(json_match.group(), language='json')
                        return None
                    return data
                except json.JSONDecodeError:
                    # If still fails, try cleaning the JSON
                    cleaned_json = clean_json_string(json_match.group())
                    if cleaned_json:
                        try:
                            data = json.loads(cleaned_json)
                            if not isinstance(data, list) or len(data) != 2:
                                st.error("AI response did not contain exactly 2 map styles")
                                st.code(cleaned_json, language='json')
                                return None
                            return data
                        except json.JSONDecodeError as e:
                            st.error(f"Could not parse JSON after cleaning: {str(e)}")
                            # Print the problematic JSON for debugging
                            st.code(cleaned_json, language='json')
                            return None
                    else:
                        st.error("Failed to clean JSON string")
                        st.code(json_match.group(), language='json')
                        return None
            else:
                st.error("Could not find JSON array in the AI response")
                st.code(content, language='text')
                return None
                
    except requests.Timeout:
        st.error("AI response timed out. Please try again.")
        return None
    except Exception as e:
        st.error(f"Error getting AI analysis: {str(e)}")
        return None
    finally:
        # Clear the progress message
        progress.empty()

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
            figsize=(12, 12),
            credit={}
        )
        
        # Convert plot to image
        buf = io.BytesIO()
        plot.fig.savefig(buf, format='png', bbox_inches='tight', dpi=300)
        buf.seek(0)
        return buf
    except Exception as e:
        st.error(f"Error generating map: {str(e)}")
        st.write("Parameters used for map generation:")
        st.json(params)
        return None

def main():
    # Load custom CSS
    with open('static/style.css') as f:
        st.write(f"<style>{f.read()}</style>", unsafe_allow_html=True)
        
    st.title("🗺️ PrettyMapAI")
    st.write("Search for a location or draw an area on the map to generate beautiful visualizations!")
    
    # Create containers with borders
    map_container = st.container(border=True)
    with map_container:
        # Create a map centered on a default location
        m = folium.Map(location=[0, 0], zoom_start=2)
        
        # Add Geocoder plugin for search functionality
        Geocoder(
            placeholder='Search for a location...',
            add_marker=False,
            collapsed=False,
            search_zoom=15
        ).add_to(m)
        
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
        map_data = st_folium(m, width=700, height=500)
    
    # User prompt container
    prompt_container = st.container(border=True)
    with prompt_container:
        user_prompt = st.text_area(
            "🎨 (Optional) Describe your preferred map style",
            placeholder="Example: I want a vintage style map with warm colors and hand-drawn elements",
            height=100
        )
        
        # Add a prominent button in full width
        if st.button("🎨 Generate PrettyMaps", use_container_width=True):
            if not map_data or not map_data.get('last_active_drawing'):
                st.error("Please draw an area on the map first!")
            else:
                # Create a progress container
                progress_container = st.container(border=True)
                with progress_container:
                    # Initialize progress message
                    progress_message = progress_container.empty()
                    progress_message.info("Starting map generation process...")
                    
                    # Extract bounds from the drawn area
                    drawn_features = map_data['last_active_drawing']
                    bounds = drawn_features['geometry']['coordinates'][0]
                    area_bounds = {
                        'north': max(coord[1] for coord in bounds),
                        'south': min(coord[1] for coord in bounds),
                        'east': max(coord[0] for coord in bounds),
                        'west': min(coord[0] for coord in bounds)
                    }
                    
                    # Step 1: Analyzing OSM data
                    progress_message.info("📊 Analyzing OpenStreetMap data...")
                    osm_analysis = analyze_osm_area(area_bounds)
                    
                    if osm_analysis:
                        # Step 2: Getting AI analysis
                        progress_message.info("🤖 Getting AI analysis for map styles...")
                        ai_params = get_ai_analysis(area_bounds, osm_analysis, user_prompt)
                        
                        if ai_params and len(ai_params) == 2:  # Now expecting 2 maps
                            # Step 3: Generating maps
                            progress_message.info("🎨 Generating beautiful maps...")
                            
                            # Create two columns for the maps
                            map_cols = st.columns(2)
                            
                            # Generate maps for each parameter set
                            for i, params in enumerate(ai_params):
                                with map_cols[i]:
                                    map_name = params.get('name', f"Map Style {i+1}")
                                    st.subheader(map_name)
                                    progress_message.info(f"Generating {map_name}...")
                                    map_image = generate_map(area_bounds, params)
                                    
                                    if map_image:
                                        # Display the map
                                        st.image(map_image, use_container_width=True)
                                        
                                        # Add download button
                                        btn = st.download_button(
                                            label=f"Download {map_name}",
                                            data=map_image,
                                            file_name=f"pretty_map_{map_name.lower().replace(' ', '_')}.png",
                                            mime="image/png",
                                            use_container_width=True
                                        )
                            
                            # Clear progress message when done
                            progress_message.success("✨ Map generation complete! You can download your maps above.")
                        else:
                            progress_message.error("❌ Failed to generate map styles. Please try again.")
                    else:
                        progress_message.error("❌ Failed to analyze area. Please try again.")
        else:
            st.info("👆 Draw an area on the map to get started!")

if __name__ == "__main__":
    main() 