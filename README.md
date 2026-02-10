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
2. Wait for scraping and analysis (2-10 minutes depending on review count)
3. View fraud detection report with score and detailed reasoning

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

## Fraud Detection Rules

1. **Text Similarity** (25% weight) - Detects duplicate/copied reviews
2. **AI-Generated Text** (20% weight) - Identifies bot-generated content
3. **Rating Distribution** (15% weight) - Flags unnatural rating patterns
4. **Reviewer Profiles** (15% weight) - Detects suspicious accounts
5. **Timing Analysis** (15% weight) - Finds review clusters posted simultaneously
6. **Review Bursts** (10% weight) - Detects sudden spikes in reviews
7. **Emoji Density** (5% weight) - Flags excessive emoji usage

## Development Status

✅ Phase 1: Foundation (database, project structure) - **COMPLETED**
✅ Phase 2: Scraping module (URL parser, Playwright scraper) - **COMPLETED**
⏳ Phase 3: Fraud detection rules (in progress)
⏳ Phase 4: Scoring system (pending)
⏳ Phase 5: Web interface (pending)
⏳ Phase 6: Testing (pending)
⏳ Phase 7: Documentation (pending)

## License

MIT License

## Contributing

This is a personal project for detecting fraudulent Google Maps reviews. Contributions welcome!
