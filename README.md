# Schaeffler Mobility Insight Platform

An intelligent trend analysis and monitoring platform designed for Schaeffler's mobility solutions, featuring AI-powered insights, real-time monitoring, and automated reporting.

## Features

- **🚀 Intelligent Trend Identification**: AI-powered analysis of mobility trends across various sectors
- **📊 Real-time Monitoring**: Continuous scanning of multiple data sources for relevant insights
- **🤖 Semi-Autonomous Analysis**: Automated trend evaluation with human approval gates
- **🧠 Human Feedback Learning**: Reinforcement learning system that improves with user feedback
- **📈 Automated Reporting**: Weekly, monthly, and quarterly executive reports
- **🎯 Schaeffler-Focused**: Tailored recommendations for Schaeffler's core competencies

## Quick Start

### Prerequisites

- Python 3.8+
- MySQL 5.7+
- OpenAI API Key
- Node.js (for frontend assets)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/schaeffler/mobility-insight-platform.git
cd mobility-insight-platform
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Initialize database:
```bash
mysql -u root -p < migrations/001_enhanced_schema.sql
```

6. Run the application:
```bash
python app.py
```

7. Access the platform:
- Main Application: http://localhost:5000
- Dashboard: http://localhost:5000/dashboard

## Configuration

### Required Environment Variables

```env
# Database
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=mobility_bot

# OpenAI
OPENAI_API_KEY=sk-...

# Flask
SECRET_KEY=your-secret-key
```

### Optional Features

Enable/disable features in `.env`:
```env
ENABLE_MONITORING=true
ENABLE_AUTO_ANALYSIS=true
ENABLE_HFRL=true
ENABLE_AUTO_REPORTS=true
```

## Usage

### 1. Trend Identification
- Select mobility use case (e.g., Delivery bots, People movers)
- Choose sector (e.g., RoboTaxi, Urban Logistics)
- Describe specific demands

### 2. Trend Scouting
- Review AI-generated trends
- Validate trends for detailed analysis
- Fast-track to implementation

### 3. Validation
- Comprehensive assessment
- Strategic positioning (ACT/PREPARE/WATCH)
- PESTEL analysis

### 4. Implementation
- Market-ready solutions
- Strategic partnerships
- Actionable roadmap

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Web Interface │────▶│  Flask Backend  │────▶│  MySQL Database │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │                         │
         │                       ▼                         │
         │              ┌─────────────────┐               │
         └─────────────▶│  OpenAI GPT-4   │               │
                        └─────────────────┘               │
                                 │                         │
                        ┌────────▼────────┐               │
                        │ Monitoring Hub  │◀──────────────┘
                        └─────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
            ┌──────────────┐         ┌──────────────┐
            │ Data Sources │         │   Analyzers  │
            └──────────────┘         └──────────────┘
```

## API Documentation

### REST Endpoints

- `GET /` - Main application interface
- `GET /dashboard` - Monitoring dashboard
- `GET /api/alerts` - Get current alerts
- `GET /api/pending-analyses` - Get analyses pending approval
- `POST /api/feedback` - Submit feedback on analysis
- `GET /api/weekly-report` - Get weekly report
- `GET /api/metrics` - Get system metrics

### WebSocket Events

- `new_alert` - Real-time alert notifications
- `new_analysis` - New analysis available
- `request_analysis` - Manual analysis trigger

## Development

### Project Structure

```
mobility-insight-platform/
├── app.py              # Main application
├── modules/            # Core functionality
│   ├── monitoring.py   # Monitoring system
│   ├── analysis.py     # Analysis engine
│   ├── feedback.py     # HFRL system
│   └── reporting.py    # Report generation
├── static/             # Frontend assets
├── templates/          # HTML templates
└── utils/              # Utilities
```

### Adding New Data Sources

1. Create new class in `data_sources/`
2. Inherit from `BaseDataSource`
3. Implement `fetch_data()` and `process_data()`
4. Register in monitoring system

### Customizing for Your Use Case

1. Update monitored keywords in database
2. Adjust confidence thresholds in `.env`
3. Customize report templates
4. Add sector-specific analysis logic

## Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=modules tests/
```

## Deployment

### Production Checklist

- [ ] Set `FLASK_ENV=production`
- [ ] Use strong `SECRET_KEY`
- [ ] Configure production database
- [ ] Set up SSL certificates
- [ ] Configure reverse proxy (nginx)
- [ ] Set up monitoring alerts
- [ ] Enable automated backups

### Docker Deployment

```bash
docker build -t schaeffler-mobility .
docker run -p 5000:5000 --env-file .env schaeffler-mobility
```

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## Support

For issues and questions:
- Internal: mobility-insights@schaeffler.com
- GitHub Issues: [Create an issue](https://github.com/schaeffler/mobility-insight-platform/issues)

## License

Proprietary - Schaeffler AG. All rights reserved.

---


