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

def get_ai_analysis(area_bounds):
    """Get AI analysis for the selected area using OpenRouter API"""
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
    
    prompt = f"""
    You are a map visualization expert. Analyze this geographic area with bounds {area_bounds} and suggest PrettyMaps parameters.
    Return ONLY a JSON array with exactly 3 objects, no other text. Each object must follow this exact structure:

    [
        {{
            "layers": {{
                "building": {{"tags": {{"building": true}}}},
                "streets": {{"width": {{"primary": 5, "secondary": 4, "residential": 3}}}}
            }},
            "style": {{
                "building": {{"palette": ["#FF5733", "#33FF57"]}},
                "streets": {{"fc": "#333333", "ec": "#666666"}}
            }},
            "radius": 1000
        }},
        {{
            "layers": {{
                "building": {{"tags": {{"building": true}}}},
                "streets": {{"width": {{"primary": 5, "secondary": 4, "residential": 3}}}}
            }},
            "style": {{
                "building": {{"palette": ["#3357FF", "#FF33F6"]}},
                "streets": {{"fc": "#333333", "ec": "#666666"}}
            }},
            "radius": 1000
        }},
        {{
            "layers": {{
                "building": {{"tags": {{"building": true}}}},
                "streets": {{"width": {{"primary": 5, "secondary": 4, "residential": 3}}}}
            }},
            "style": {{
                "building": {{"palette": ["#33FFF6", "#F6FF33"]}},
                "streets": {{"fc": "#333333", "ec": "#666666"}}
            }},
            "radius": 1000
        }}
    ]

    Focus on these aspects:
    1. Urban features: buildings, streets, parks
    2. Natural features: water bodies, green spaces
    3. Street patterns: grid, organic, or mixed

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
            import re
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                st.error("Could not find valid JSON in the AI response")
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
    map_data = st_folium(m, width=800, height=600)
    
    # Add a button to generate maps
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
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            if st.button("🎨 Generate Beautiful Maps", use_container_width=True):
                with st.spinner("Analyzing area and generating maps..."):
                    # Get AI analysis
                    ai_params = get_ai_analysis(area_bounds)
                    
                    if ai_params:
                        # Generate maps for each parameter set
                        for i, params in enumerate(ai_params):
                            st.subheader(f"Map Style {i+1}")
                            map_image = generate_map(area_bounds, params)
                            
                            if map_image:
                                # Display the map
                                st.image(map_image, use_column_width=True)
                                
                                # Add download button
                                btn = st.download_button(
                                    label=f"Download Map {i+1}",
                                    data=map_image,
                                    file_name=f"pretty_map_{i+1}.png",
                                    mime="image/png"
                                )
    else:
        st.info("👆 Draw an area on the map to get started!")

if __name__ == "__main__":
    main() 