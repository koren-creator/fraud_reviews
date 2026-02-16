# Google Maps Fraud Review Detector

A Python Flask web application to detect fraudulent reviews on Google Maps business pages using rule-based fraud detection algorithms.

## Features

- 🔍 Scrapes Google Maps reviews using Playwright
- 🤖 Detects AI-generated text patterns
- 📊 Analyzes review timing clusters and rating distributions
- 🎯 Fraud score (0-100%) with detailed breakdown
- 🌐 Hebrew + English support with RTL layout
- 💾 Local SQLite database for caching
- 🎨 Beautiful HTML reports

## Setup Instructions

### 1. Install Dependencies

```bash
cd C:\Users\Shirazi\fraud_review
pip install -r requirements.txt
```

### 2. Install Playwright Browser

```bash
playwright install chromium
```

### 3. Download NLTK Data

```bash
python -m nltk.downloader punkt averaged_perceptron_tagger
```

### 4. Initialize Database

```bash
python database/migrations.py
```

This will create the SQLite database at `data/fraud_detection.db`

## Usage

### Run the Web Application

```bash
python app.py
```

Then visit: `http://localhost:5000`

### Analyze a Business

1. Enter a Google Maps business URL
2. Wait for scraping and analysis (2-3 minutes, scrapes up to 100 reviews)
3. View fraud detection report with score and detailed reasoning

**Note**: The system analyzes up to 100 most recent reviews per business for optimal performance. This is typically sufficient for fraud detection patterns.

### Example URL Format

```
https://www.google.com/maps/place/Business+Name/@31.123456,34.123456,17z
```

## Project Structure

```
fraud_review/
├── app.py                     # Flask application
├── config.py                  # Configuration
├── requirements.txt           # Dependencies
├── database/                  # Database layer
│   ├── schema.sql
│   ├── models.py
│   └── migrations.py
├── scraper/                   # Web scraping
│   ├── playwright_scraper.py
│   └── url_parser.py
├── fraud_detection/           # Fraud analysis
│   ├── detector.py
│   ├── scoring.py
│   └── rules/                # Detection rules
├── web/                       # Web interface
│   ├── routes.py
│   └── templates/
└── static/                    # CSS, JS, images
```

## Fraud Detection Rules (POC)

Currently implemented (2 rules):

1. **Text Similarity** (60% weight) - Detects duplicate/copied reviews using Levenshtein distance
2. **Timing Analysis** (40% weight) - Finds review clusters posted simultaneously

Future rules (planned):
- AI-Generated Text - Identifies bot-generated content
- Rating Distribution - Flags unnatural rating patterns
- Reviewer Profiles - Detects suspicious accounts
- Review Bursts - Detects sudden spikes in reviews
- Emoji Density - Flags excessive emoji usage

## Development Status

✅ Phase 1: Foundation (database, project structure) - **COMPLETED**
✅ Phase 2: Scraping module (URL parser, Playwright scraper) - **COMPLETED**
✅ Phase 3: Fraud detection rules (Text Similarity + Timing Analysis) - **COMPLETED**
✅ Phase 4: Scoring system (weighted 60/40 algorithm) - **COMPLETED**
✅ Phase 5: Web interface (Flask app, HTML templates, CSS) - **COMPLETED**
⏳ Phase 6: Testing (in progress)
⏳ Phase 7: Documentation (pending)

## Testing

Before first use, install the Playwright browser:

```bash
python -m playwright install chromium
```

Then start the Flask app:

```bash
python app.py
```

Visit [http://localhost:5000](http://localhost:5000) and enter a Google Maps business URL to analyze.

## License

MIT License

## Contributing

This is a personal project for detecting fraudulent Google Maps reviews. Contributions welcome!
