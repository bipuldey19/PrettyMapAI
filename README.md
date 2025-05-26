# PrettyMapAI

A Streamlit application that combines PrettyMaps with AI-powered map generation. Draw an area on the map and get beautiful visualizations generated using AI analysis.

## Features

- Interactive map selection using drawing tools
- AI-powered analysis of selected areas using OpenRouter API
- Generation of 3 different map styles based on area characteristics
- Download generated maps as PNG files
- Beautiful and modern UI

## Setup

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the root directory with your OpenRouter API key:
   ```
   OPENROUTER_API_KEY=your_api_key_here
   ```
4. Run the Streamlit app:
   ```bash
   streamlit run app.py
   ```

## Usage

1. Open the application in your web browser
2. Use the drawing tools to select an area on the map
3. Click "Generate Maps" to create visualizations
4. Download your favorite map styles

## Requirements

- Python 3.8+
- Streamlit
- PrettyMaps
- OpenRouter API key

## Deployment

This application can be deployed on any platform that supports Streamlit apps, such as:
- Streamlit Cloud
- Heroku
- AWS
- Google Cloud Platform

Make sure to set the `OPENROUTER_API_KEY` environment variable in your deployment environment.

## License

MIT License 