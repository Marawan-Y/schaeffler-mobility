# config/settings.py
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base configuration class"""
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'schaeffler-mobility-2024-change-this')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Database
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 3306))
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', 'mobility_bot')
    
    # LLM Configuration
    LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'openai').lower()
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    VERTEX_PROJECT = os.getenv('VERTEX_PROJECT')
    VERTEX_LOCATION = os.getenv('VERTEX_LOCATION', 'us-central1')
    VERTEX_MODEL = os.getenv('VERTEX_MODEL', 'gemini-1.0-pro')
    
    # Feature Flags
    ENABLE_MONITORING = os.getenv('ENABLE_MONITORING', 'true').lower() == 'true'
    ENABLE_AUTO_ANALYSIS = os.getenv('ENABLE_AUTO_ANALYSIS', 'true').lower() == 'true'
    ENABLE_HFRL = os.getenv('ENABLE_HFRL', 'true').lower() == 'true'
    ENABLE_AUTO_REPORTS = os.getenv('ENABLE_AUTO_REPORTS', 'true').lower() == 'true'
    
    # Monitoring Settings
    MONITORING_INTERVAL = int(os.getenv('MONITORING_INTERVAL', 300))
    ALERT_THRESHOLD = float(os.getenv('ALERT_THRESHOLD', 0.7))
    APPROVAL_THRESHOLD = float(os.getenv('APPROVAL_THRESHOLD', 0.8))
    
    # API Keys
    NEWS_API_KEY = os.getenv('NEWS_API_KEY')
    ALPHA_VANTAGE_KEY = os.getenv('ALPHA_VANTAGE_KEY')
    
    @property
    def DATABASE_CONFIG(self):
        return {
            'host': self.DB_HOST,
            'port': self.DB_PORT,
            'user': self.DB_USER,
            'password': self.DB_PASSWORD,
            'database': self.DB_NAME,
            'charset': 'utf8mb4'
        }
    
    @property
    def FEATURES_ENABLED(self):
        return {
            'monitoring': self.ENABLE_MONITORING,
            'auto_analysis': self.ENABLE_AUTO_ANALYSIS,
            'hfrl': self.ENABLE_HFRL,
            'auto_reports': self.ENABLE_AUTO_REPORTS
        }

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # Override with production values
    MONITORING_INTERVAL = int(os.getenv('MONITORING_INTERVAL', 600))  # 10 minutes

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get configuration based on environment"""
    env = os.getenv('FLASK_ENV', 'development')
    return config.get(env, config['default'])