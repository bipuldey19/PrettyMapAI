# PrettyMapAI

A Streamlit application that combines PrettyMaps with AI-powered map generation. Draw an area on the map and get beautiful visualizations generated using AI analysis.

## Credits

This application is built on top of the amazing [PrettyMaps](https://github.com/chrieke/prettymapp) library by [@chrieke](https://github.com/chrieke). All credit for the original map generation functionality goes to them. This project adds AI-powered style generation on top of their excellent work.

## Features

- Interactive map selection using drawing tools
- Search for locations using the map's built-in geocoder
- AI-powered analysis of selected areas using OpenRouter API
- Generation of 2 different map styles based on area characteristics and user prompt
- Robust handling of missing OSM data (no errors for missing features)
- Copyright/attribution text is removed from generated images
- Download generated maps as PNG files
- Rotates between multiple OpenRouter API keys to avoid exhaustion
- Improved error handling and user feedback
- Beautiful and modern UI

## Setup

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the root directory with your OpenRouter API keys:
   ```
   OPENROUTER_API_KEY_1=your_first_key_here
   OPENROUTER_API_KEY_2=your_second_key_here
   OPENROUTER_API_KEY_3=your_third_key_here
   ```
   You can use 1, 2, or 3 keys. The app will randomly select one for each request.
4. Run the Streamlit app:
   ```bash
   streamlit run app.py
   ```

## Usage

1. Open the application in your web browser
2. Use the search box or drawing tools to select an area on the map
3. Optionally, describe your preferred map style in the prompt
4. Click "Generate PrettyMaps" to create visualizations
5. Download your favorite map styles

## Requirements

- Python 3.8+
- Streamlit
- PrettyMaps
- OpenRouter API key(s)

## Deployment

This application can be deployed on any platform that supports Streamlit apps, such as:
- Streamlit Cloud
- Heroku
- AWS
- Google Cloud Platform

Make sure to set the `OPENROUTER_API_KEY_1`, `OPENROUTER_API_KEY_2`, and `OPENROUTER_API_KEY_3` environment variables in your deployment environment.

## License

MIT License 