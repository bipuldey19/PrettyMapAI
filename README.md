# 🗺️ PrettyMapAI

PrettyMapAI is an AI-powered map visualization tool that generates beautiful, artistic maps using OpenStreetMap data. Built on top of the [PrettyMapp](https://github.com/chrieke/prettymapp) library, it adds AI-driven style generation to create unique and visually appealing maps.

## ✨ Features

- **Interactive Map Selection**: Draw or search for any location on the map
- **AI-Powered Style Generation**: Get two unique artistic styles for your map based on your description
- **Parallel Processing**: Generate multiple map styles simultaneously
- **Customizable Styles**: Control colors, patterns, and visual elements
- **Multiple Map Shapes**: Choose between circular and rectangular maps
- **High-Resolution Output**: Generate maps in high quality for printing or digital use
- **Easy Download**: Download your generated maps in PNG format

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- OpenStreetMap API access
- OpenRouter API key(s) for AI style generation

### Installation

1. Clone the repository:
```bash
git clone https://github.com/bipuldey19/PrettyMapAI.git
cd PrettyMapAI
```

2. Install the required packages:
```bash
pip install -r requirements.txt
```

3. Set up your environment variables:
```bash
cp .env.example .env
```
Edit the `.env` file and add your OpenRouter API keys:
```
OPENROUTER_API_KEY_1=your_key_here
OPENROUTER_API_KEY_2=your_key_here
OPENROUTER_API_KEY_3=your_key_here
```

### Running the Application

```bash
streamlit run app.py
```

## 🎨 Using PrettyMapAI

1. **Select a Location**:
   - Search for a location using the search bar
   - Or draw an area on the map using the drawing tools

2. **Describe Your Style** (Optional):
   - Enter a description of your desired map style
   - Example: "I want a vintage style map with warm colors and hand-drawn elements"

3. **Generate Maps**:
   - Click the "Generate PrettyMaps" button
   - Wait for the AI to generate two unique styles
   - Download your favorite style

## 🛠️ Customization

The AI can control various aspects of the map style:
- Color palettes
- Line weights
- Patterns
- Background colors
- Building styles
- Street emphasis
- Map shape (circular or rectangular)
- Title and text settings (when requested)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Credits

This project is built on top of the [PrettyMaps](https://github.com/chrieke/prettymapp) library by [@chrieke](https://github.com/chrieke). We extend our thanks to the original author for creating such a beautiful map visualization tool.

## 📞 Support

If you encounter any issues or have questions, please open an issue in the GitHub repository. 