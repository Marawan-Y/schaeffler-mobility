# ───────────────────────────────────────────────────────── app.py ───────────
import os
import re
import time
import json
import asyncio
import threading
from datetime import datetime, timedelta
from contextlib import contextmanager
from functools import wraps

import pymysql
import markdown as md
from dotenv import load_dotenv
from flask import Flask, render_template, request, session, flash, jsonify, abort, redirect, url_for
from flask_socketio import SocketIO, emit
import openai
from openai import OpenAI

# Import enhanced modules
from modules.monitoring import IntelligentMonitor
from modules.analysis import SemiAutonomousAnalyzer
from modules.feedback import HumanFeedbackRL
from modules.reporting import ReportGenerator
from utils.database import get_db_connection, save_to_db
from utils.helpers import extract_confidence_score, split_trend_blocks

# ─── Flask & SocketIO Setup ─────────────────────────────────────────────────
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "schaeffler_mobility_2024")

def render_markdown(text):
    # enable the "tables" (and fenced code, etc.) extensions
    rendered_html = md.markdown(text or "", extensions=["tables", "fenced_code", "nl2br"])
    
    # Add inline CSS directly to the table element
    table_style = 'style="border-collapse: collapse; width: 100%; margin-bottom: 1rem;"'
    th_style = 'style="border: 1px solid #ddd; padding: 8px; text-align: left; background-color: #f2f2f2; font-weight: bold;"'
    td_style = 'style="border: 1px solid #ddd; padding: 8px; text-align: left;"'
    
    # Replace table tags with styled versions
    rendered_html = rendered_html.replace("<table>", f'<table {table_style}>')
    rendered_html = rendered_html.replace("<th>", f'<th {th_style}>')
    rendered_html = rendered_html.replace("<td>", f'<td {td_style}>')
    
    return rendered_html

# Add the filter to your Jinja environment
app.jinja_env.filters["markdown"] = render_markdown
app.jinja_env.filters['extract_confidence'] = extract_confidence_score
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ─── Database Config ────────────────────────────────────────────────────────
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "your_user"),
    "password": os.getenv("DB_PASSWORD", "your_pass"),
    "database": os.getenv("DB_NAME", "mobility_bot"),
    "charset": "utf8mb4"
}

# ─── LLM Config ─────────────────────────────────────────────────────────────
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
VERTEX_PROJECT = os.getenv("VERTEX_PROJECT")
VERTEX_LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")
VERTEX_MODEL = os.getenv("VERTEX_MODEL", "gemini-2.0-flash")

if LLM_PROVIDER == "vertex":
    import vertexai
    try:
        from vertexai.preview.generative_models import GenerativeModel
    except ImportError:
        from vertexai.generative_models import GenerativeModel
else:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

# ─── Enhanced Features Config ───────────────────────────────────────────────
FEATURES_ENABLED = {
    'monitoring': os.getenv('ENABLE_MONITORING', 'true').lower() == 'true',
    'auto_analysis': os.getenv('ENABLE_AUTO_ANALYSIS', 'true').lower() == 'true',
    'hfrl': os.getenv('ENABLE_HFRL', 'true').lower() == 'true',
    'auto_reports': os.getenv('ENABLE_AUTO_REPORTS', 'true').lower() == 'true'
}

MONITORING_INTERVAL = int(os.getenv('MONITORING_INTERVAL', '300'))
ALERT_THRESHOLD = float(os.getenv('ALERT_THRESHOLD', '0.7'))
APPROVAL_THRESHOLD = float(os.getenv('APPROVAL_THRESHOLD', '0.8'))

# ─── Enhanced Application Class ─────────────────────────────────────────────
class EnhancedMobilityApp:
    """Main application class with all enhanced features"""
    
    def __init__(self):
        self.monitor = None
        self.analyzer = None
        self.feedback_system = None
        self.report_generator = None
        self.monitoring_thread = None
        self.active_alerts = []
        self.pending_analyses = []
        
        # Initialize components based on enabled features
        if FEATURES_ENABLED['monitoring']:
            self.monitor = IntelligentMonitor(
                db_config=DB_CONFIG,
                alert_threshold=ALERT_THRESHOLD
            )
        
        if FEATURES_ENABLED['auto_analysis']:
            self.analyzer = SemiAutonomousAnalyzer(
                llm_client=openai_client,
                approval_threshold=APPROVAL_THRESHOLD
            )
        
        if FEATURES_ENABLED['hfrl']:
            self.feedback_system = HumanFeedbackRL(db_config=DB_CONFIG)
        
        if FEATURES_ENABLED['auto_reports']:
            self.report_generator = ReportGenerator(db_config=DB_CONFIG)
    
    def start(self):
        """Start all enabled services"""
        if FEATURES_ENABLED['monitoring'] and self.monitor:
            self.start_monitoring()
        
        if FEATURES_ENABLED['auto_reports'] and self.report_generator:
            self.report_generator.schedule_reports()
    
    def start_monitoring(self):
        """Start background monitoring thread"""
        def run_monitor():
            while True:
                try:
                    # Run async monitoring cycle
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self.monitoring_cycle())
                    loop.close()
                except Exception as e:
                    print(f"Monitoring error: {e}")
                time.sleep(MONITORING_INTERVAL)
        
        self.monitoring_thread = threading.Thread(target=run_monitor, daemon=True)
        self.monitoring_thread.start()
    
    async def monitoring_cycle(self):
        """Single monitoring cycle"""
        if not self.monitor:
            return
        
        # Scan for new alerts
        new_alerts = await self.monitor.scan_sources()
        
        for alert in new_alerts:
            # Store alert
            self.active_alerts.append(alert)
            self.monitor.save_alert(alert)
            
            # Emit to connected clients
            socketio.emit('new_alert', {
                'id': alert.id,
                'title': alert.title,
                'severity': alert.severity,
                'category': alert.category,
                'confidence': alert.confidence
            })
            
            # Analyze high-priority alerts
            if FEATURES_ENABLED['auto_analysis'] and alert.requires_action:
                analysis = await self.analyzer.analyze_trend(alert, self.get_context())
                self.pending_analyses.append(analysis)
                self.analyzer.save_analysis(analysis)
                
                # Notify about new analysis
                socketio.emit('new_analysis', {
                    'analysis_id': analysis.trend_id,
                    'title': analysis.title,
                    'requires_approval': analysis.human_approval_required
                })
    
    def get_context(self):
        """Get current context for analysis"""
        return {
            'company': 'Schaeffler',
            'focus_areas': ['e-mobility', 'autonomous driving', 'sustainability'],
            'risk_tolerance': 'medium',
            'investment_capacity': 'high',
            'core_competencies': ['bearings', 'chassis systems', 'e-mobility solutions']
        }

# ─── Initialize Enhanced App ────────────────────────────────────────────────
enhanced_app = EnhancedMobilityApp()

# ─── Authentication Decorator ───────────────────────────────────────────────
def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Simple session-based auth - enhance for production
        if not session.get('authenticated'):
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

# ─── Universal LLM Helper ───────────────────────────────────────────────────
def call_llm(prompt: str, retries: int = 2, delay: float = 1.0,
             max_tokens: int = 800) -> str:
    """Call LLM with retry logic"""
    for attempt in range(retries):
        try:
            if LLM_PROVIDER == "vertex":
                vertexai.init(project=VERTEX_PROJECT, location=VERTEX_LOCATION)
                model = GenerativeModel(model_name=VERTEX_MODEL)
                return model.generate_content(
                    prompt, temperature=0.5, max_output_tokens=max_tokens
                ).text.strip()
            
            resp = openai_client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=max_tokens,
                timeout=30
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"LLM attempt {attempt+1} failed: {e}")
            if attempt == retries-1:
                return f"Error generating content: {str(e)[:100]}"
            time.sleep(delay)

# ─── Trend Generation Functions ─────────────────────────────────────────────
def generate_trends(uc: str, sec: str, dem: str) -> str:
    """Generate trends with enhanced structure"""
    prompt_text = f"""Generate exactly 3 comprehensive mobility trends for Schaeffler:
- **Use-case**: {uc}
- **Sector**: {sec}
- **Demand**: {dem}

Consider Schaeffler's core competencies in bearings, chassis systems, and e-mobility solutions.

For each trend, provide the following structured format:

Trend Title: [Compelling and specific trend name]

Confidence Score: [0.1-1.0]

**Confidence Justification:**
- **Market Evidence**: [supporting market data/signals]
- **Technology Readiness**: [current technology maturity]
- **Industry Adoption**: [adoption indicators]
- **Risk Factors**: [key uncertainties or challenges]

**Description:**
[2-3 sentences describing the trend and its significance for Schaeffler]

**Market Impact:**
- **Market Size**: [estimated market opportunity]
- **Timeline**: [expected timeline for mainstream adoption]
- **Key Drivers**: [primary forces driving this trend]

**Value Proposition for Schaeffler:**
[Clear value proposition specifically for Schaeffler's capabilities]

**Key Players:**
[List 3-4 major companies/organizations involved]

**Implementation Readiness:**
- **Technical Feasibility**: [assessment of technical requirements]
- **Market Readiness**: [assessment of market conditions]
- **Competitive Advantage**: [Schaeffler's potential advantages]

---

Make each trend distinct and actionable with realistic confidence scores based on current market conditions."""

    try:
        result = call_llm(prompt_text, max_tokens=1200)
        if not result or len(result.strip()) < 50:
            return generate_fallback_trends(uc, sec, dem)
        return result
    except Exception as e:
        print(f"Error generating trends: {e}")
        return generate_fallback_trends(uc, sec, dem)

def generate_fallback_trends(uc: str, sec: str, dem: str) -> str:
    """Generate fallback trends"""
    return f"""Trend Title: Intelligent Bearing Systems for {uc}

Confidence Score: 0.8

**Confidence Justification:**
- **Market Evidence**: Growing demand for predictive maintenance in {sec}
- **Technology Readiness**: Schaeffler's smart bearing technology is mature
- **Industry Adoption**: Major OEMs adopting intelligent components
- **Risk Factors**: Integration complexity with existing systems

**Description:**
Smart bearing systems with integrated sensors are revolutionizing {uc} in the {sec} sector. This trend aligns perfectly with Schaeffler's core competencies and addresses {dem}.

**Market Impact:**
- **Market Size**: $2.5B by 2028 for intelligent bearing systems
- **Timeline**: 2-3 years for widespread adoption
- **Key Drivers**: Predictive maintenance, efficiency optimization, safety requirements

**Value Proposition for Schaeffler:**
Leverage existing bearing expertise to capture high-margin smart component market.

**Key Players:**
- Schaeffler (market leader)
- SKF
- Timken
- NSK

**Implementation Readiness:**
- **Technical Feasibility**: High - Schaeffler already has the technology
- **Market Readiness**: High - customers demanding smart solutions
- **Competitive Advantage**: Strong - leveraging 150+ years of bearing expertise

---

Trend Title: E-Mobility Powertrain Solutions for {sec}

Confidence Score: 0.9

**Confidence Justification:**
- **Market Evidence**: Exponential growth in electric {sec} vehicles
- **Technology Readiness**: Schaeffler's e-mobility solutions are production-ready
- **Industry Adoption**: All major OEMs transitioning to electric
- **Risk Factors**: Supply chain constraints for key components

**Description:**
The electrification of {sec} is creating massive opportunities for integrated e-mobility solutions. Schaeffler's complete system approach addresses {dem} with proven technology.

**Market Impact:**
- **Market Size**: $45B e-mobility component market by 2030
- **Timeline**: Immediate - market is growing now
- **Key Drivers**: Emissions regulations, efficiency requirements, TCO benefits

**Value Proposition for Schaeffler:**
Complete e-mobility solutions from a single supplier, reducing integration complexity.

**Key Players:**
- Schaeffler
- Bosch
- Continental
- ZF

**Implementation Readiness:**
- **Technical Feasibility**: Very High - products already in production
- **Market Readiness**: Very High - immediate demand
- **Competitive Advantage**: Excellent - full system capability

---

Trend Title: Autonomous {uc} Safety Systems

Confidence Score: 0.7

**Confidence Justification:**
- **Market Evidence**: Increasing investment in autonomous {uc}
- **Technology Readiness**: Schaeffler's by-wire technology enables autonomy
- **Industry Adoption**: Progressive adoption in controlled environments
- **Risk Factors**: Regulatory uncertainty, technology maturity varies

**Description:**
Autonomous {uc} requires ultra-reliable mechanical systems. Schaeffler's precision components and by-wire technology are essential enablers for safe autonomous operation in {sec}.

**Market Impact:**
- **Market Size**: $8B for autonomous vehicle components by 2030
- **Timeline**: 3-5 years for significant deployment
- **Key Drivers**: Safety requirements, labor shortages, efficiency gains

**Value Proposition for Schaeffler:**
Critical safety components that enable autonomous operation with required reliability.

**Key Players:**
- Schaeffler
- Mobileye
- Aptiv
- Continental

**Implementation Readiness:**
- **Technical Feasibility**: High - technology exists, integration ongoing
- **Market Readiness**: Medium - market developing rapidly
- **Competitive Advantage**: Strong - precision engineering expertise crucial"""

# ─── Enhanced Prompt Wrappers ───────────────────────────────────────────────
def assess_trend(title, block):
    """Enhanced assessment with Schaeffler focus"""
    p = f"""## Comprehensive Trend Assessment for Schaeffler: "{title}"

{block}

Please provide a structured assessment from Schaeffler's perspective:

| Category | Rating (1-10) | Justification |
|----------|---------------|---------------|
| Strategic Fit | [score] | [alignment with Schaeffler's strategy] |
| Market Impact | [score] | [potential market size and growth] |
| Technical Feasibility | [score] | [leveraging Schaeffler's capabilities] |
| Competitive Advantage | [score] | [Schaeffler's unique position] |
| Investment Required | [score] | [resources needed] |
| Time to Market | [score] | [speed of implementation] |
| Risk Level | [score] | [technical and market risks] |
| Revenue Potential | [score] | [expected returns] |
| Sustainability Impact | [score] | [environmental benefits] |
| Innovation Potential | [score] | [breakthrough opportunity] |

## Summary
Provide a 2-3 sentence executive summary for Schaeffler's leadership."""
    return call_llm(p, max_tokens=1200)

def radar_positioning(title, assessment):
    """Strategic positioning for Schaeffler"""
    p = f"""{assessment}

## Strategic Radar Positioning for Schaeffler: "{title}"

**Classification:** [ACT/PREPARE/WATCH]

**Justification:**
- **ACT**: Immediate action required - aligns with core strategy and capabilities
- **PREPARE**: Build capabilities and partnerships for future opportunity
- **WATCH**: Monitor development, not immediate priority

**Recommended Timeline:** [specific timeframe]
**Investment Level:** [Low/Medium/High]
**Key Action Items for Schaeffler:** [list 3-5 specific actions]
**Success Metrics:** [measurable KPIs]"""
    return call_llm(p, max_tokens=400)

def pestel_driver(title, block):
    """PESTEL analysis for Schaeffler"""
    p = f"""{block}

## PESTEL Analysis for Schaeffler: "{title}"

**Primary Driver:** [Political/Economic/Social/Technological/Ecological/Legal]

**Impact on Schaeffler:**
[Specific implications for Schaeffler's business]

**Detailed Analysis:**
- **Political**: [government policies affecting Schaeffler]
- **Economic**: [market conditions and financial implications]
- **Social**: [changing customer preferences and workforce]
- **Technological**: [innovation requirements and opportunities]
- **Ecological**: [sustainability and environmental regulations]
- **Legal**: [compliance and regulatory requirements]

**Strategic Response:**
[Recommended actions for Schaeffler]"""
    return call_llm(p, max_tokens=500)

def market_ready_solution(title, block):
    """Implementation roadmap for Schaeffler"""
    p = f"""{block}

## Schaeffler Implementation Roadmap: "{title}"

### 1. Technology Integration at Schaeffler
- **Current Capabilities**: [existing Schaeffler technologies]
- **Required Technologies**: [gaps to fill]
- **Integration Approach**: [leveraging Schaeffler's R&D]
- **Timeline**: [specific phases]

### 2. Product Development
- **Product Portfolio**: [specific Schaeffler products]
- **Innovation Requirements**: [new development needs]
- **Development Timeline**: [milestones]
- **Resource Allocation**: [teams and budget]

### 3. Manufacturing & Production
- **Production Locations**: [Schaeffler facilities]
- **Capacity Requirements**: [volume projections]
- **Quality Standards**: [Schaeffler quality systems]
- **Supply Chain**: [supplier integration]

### 4. Market Strategy
- **Target Customers**: [specific OEMs and segments]
- **Value Proposition**: [Schaeffler's unique offering]
- **Pricing Strategy**: [competitive positioning]
- **Sales Channels**: [go-to-market approach]

### 5. Partnership Strategy
- **Technology Partners**: [complementary capabilities]
- **Customer Partnerships**: [co-development opportunities]
- **Supplier Relationships**: [strategic sourcing]

### 6. Financial Projections
- **Investment Required**: [CAPEX and OPEX]
- **Revenue Projections**: [5-year forecast]
- **ROI Timeline**: [payback period]
- **Risk Mitigation**: [financial hedging strategies]

### 7. Success Metrics
- **KPIs**: [specific measurable goals]
- **Milestones**: [key achievement dates]
- **Review Process**: [governance structure]"""
    return call_llm(p, max_tokens=1200)

def partners_navigation(title, block):
    """Strategic partnerships for Schaeffler"""
    p = f"""{block}

## Strategic Partnership Analysis for Schaeffler: "{title}"

| Partner Category | Recommended Partner | Strategic Value | Collaboration Model | Priority |
|-----------------|-------------------|-----------------|-------------------|----------|
| Technology Partner | [Company] | [Value to Schaeffler] | [JV/License/Co-dev] | [H/M/L] |
| OEM Customer | [Company] | [Market access] | [Supply agreement] | [H/M/L] |
| Research Institute | [Institution] | [Innovation] | [Joint research] | [H/M/L] |
| Startup/Innovator | [Company] | [Disruptive tech] | [Investment/Acquisition] | [H/M/L] |
| System Integrator | [Company] | [Market reach] | [Channel partnership] | [H/M/L] |

## Partnership Execution Plan
- **Immediate Actions**: [first 30 days]
- **Partnership Terms**: [key negotiation points]
- **Success Criteria**: [measurable outcomes]
- **Risk Management**: [mitigation strategies]"""
    return call_llm(p, max_tokens=800)

# ─── MAIN ROUTES ────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Redirect to dashboard as the main page"""
    return redirect(url_for('dashboard'))

@app.route("/chat", methods=["GET", "POST"])
def chat():
    """Main workflow route - enhanced with monitoring integration"""
    if request.method == "GET":
        # Check if continuing from previous analysis
        if request.args.get('continue') == 'true' and session.get('remaining_trends'):
            session["step"] = "scouting"
        else:
            # New analysis - clear session
            session.clear()
            session["step"] = "identification"
            session["authenticated"] = True  # Simple auth for demo
        
        return render_template("index.html", session=session, features=FEATURES_ENABLED)

    step = session.get("step")

    try:
        # Phase 1: Identification
        if step == "identification":
            uc = request.form.get("use_case", "").strip()
            sec = request.form.get("sector", "").strip()
            dem = request.form.get("demand", "").strip()
            
            if not (uc and sec and dem):
                flash("Please fill in all fields.", "warning")
                return render_template("index.html", session=session, features=FEATURES_ENABLED)

            # Generate trends
            raw = generate_trends(uc, sec, dem)
            titles, blocks = split_trend_blocks(raw)
            
            if not titles:
                flash("Could not generate trends. Please try again.", "error")
                return render_template("index.html", session=session, features=FEATURES_ENABLED)
            
            trends_md = "\n\n".join(f"### Trend {i+1}: {t}\n{blocks[i]}"
                                   for i, t in enumerate(titles))

            session.update({
                "step": "scouting",
                "use_case": uc, "sector": sec, "demand": dem,
                "titles": titles, "blocks": blocks, "trends_md": trends_md,
                "remaining_trends": titles.copy(), "validation_results": {}
            })
            
            # Log to monitoring if enabled
            if FEATURES_ENABLED['monitoring'] and enhanced_app.monitor:
                enhanced_app.monitor.log_user_query(uc, sec, dem)
            
            return render_template("index.html", session=session, features=FEATURES_ENABLED)

        # Phase 2: Scouting
        elif step == "scouting":
            idx_str = request.form.get("selected_trend_idx", "")
            action = request.form.get("action", "")
            
            if not (idx_str.isdigit() and action in ("validate", "implement")):
                flash("Please select a trend and action.", "warning")
                return render_template("index.html", session=session, features=FEATURES_ENABLED)

            idx = int(idx_str)
            rem = session.get("remaining_trends", [])
            
            if idx < 0 or idx >= len(rem):
                flash("Invalid trend selection.", "warning")
                return render_template("index.html", session=session, features=FEATURES_ENABLED)

            sel = rem.pop(idx)
            titles = session.get("titles", [])
            blocks = session.get("blocks", [])
            
            block = blocks[titles.index(sel)]
            session["selected_trend"] = sel
            session["remaining_trends"] = rem  # Update remaining trends
            session.modified = True

            if action == "validate":
                ass = assess_trend(sel, block)
                rad = radar_positioning(sel, ass)
                pes = pestel_driver(sel, block)
                
                if "validation_results" not in session:
                    session["validation_results"] = {}
                    
                session["validation_results"][sel] = {
                    "assessment": ass, "radar": rad, "pestel": pes
                }
                session["step"] = "validation"
                session.modified = True
                return render_template("index.html", session=session, features=FEATURES_ENABLED)

            # Direct implementation
            msol = market_ready_solution(sel, block)
            prts = partners_navigation(sel, block)
            
            # Save to database
            save_to_db(
                session["use_case"], session["sector"], session["demand"],
                session["trends_md"], sel, "", "", "", msol, prts,
                titles, blocks, DB_CONFIG
            )
            
            session["market_solution"] = msol
            session["partners"] = prts
            session["step"] = "implementation"
            session.modified = True
            return render_template("index.html", session=session, features=FEATURES_ENABLED)

        # Phase 3: Validation
        elif step == "validation":
            action = request.form.get("action", "")
            sel = session.get("selected_trend", "")
            titles = session.get("titles", [])
            blocks = session.get("blocks", [])
            
            if not sel or sel not in titles:
                flash("No trend selected.", "error")
                session["step"] = "scouting"
                return render_template("index.html", session=session, features=FEATURES_ENABLED)
            
            block = blocks[titles.index(sel)]

            if action == "validate_more":
                session["step"] = "scouting"
                return render_template("index.html", session=session, features=FEATURES_ENABLED)

            # Proceed to implementation
            msol = market_ready_solution(sel, block)
            prts = partners_navigation(sel, block)
            vr = session.get("validation_results", {}).get(sel, {})
            
            # Save to database
            save_to_db(
                session["use_case"], session["sector"], session["demand"],
                session["trends_md"], sel,
                vr.get("assessment", ""), vr.get("radar", ""), vr.get("pestel", ""),
                msol, prts, titles, blocks, DB_CONFIG
            )
            
            session["market_solution"] = msol
            session["partners"] = prts
            session["step"] = "implementation"
            session.modified = True
            return render_template("index.html", session=session, features=FEATURES_ENABLED)

    except Exception as e:
        print(f"Error in chat route: {e}")
        flash(f"An error occurred: {str(e)}", "error")
        session["step"] = "identification"
        return render_template("index.html", session=session, features=FEATURES_ENABLED)

    # Fallback
    session["step"] = "identification"
    return render_template("index.html", session=session, features=FEATURES_ENABLED)

# ─── Dashboard Route ────────────────────────────────────────────────────────
@app.route("/dashboard")
def dashboard():
    """Enhanced monitoring dashboard"""
    # Ensure user is authenticated
    if not session.get('authenticated'):
        session['authenticated'] = True  # Auto-authenticate for demo
    
    return render_template("dashboard.html", features=FEATURES_ENABLED)

# ─── Additional Pages Routes ────────────────────────────────────────────────
@app.route("/analyses")
def analyses():
    """Trend analyses page"""
    if not session.get('authenticated'):
        return redirect(url_for('dashboard'))
    
    return render_template("analyses.html", features=FEATURES_ENABLED)

@app.route("/reports")
def reports():
    """Reports page"""
    if not session.get('authenticated'):
        return redirect(url_for('dashboard'))
    
    return render_template("reports.html", features=FEATURES_ENABLED)

@app.route("/ai_learning")
def ai_learning():
    """AI Learning page"""
    if not session.get('authenticated'):
        return redirect(url_for('dashboard'))
    
    return render_template("ai_learning.html", features=FEATURES_ENABLED)

@app.route("/alerts")
def alerts():
    """Alerts page"""
    if not session.get('authenticated'):
        return redirect(url_for('dashboard'))
    
    return render_template("alerts.html", features=FEATURES_ENABLED)

# ─── API Routes for Enhanced Features ───────────────────────────────────────
@app.route('/api/alerts')
@require_auth
def get_alerts():
    """Get current alerts"""
    if not FEATURES_ENABLED['monitoring']:
        return jsonify({'error': 'Monitoring not enabled'}), 404
    
    try:
        alerts = enhanced_app.monitor.get_recent_alerts(limit=20) if enhanced_app.monitor else []
        return jsonify([alert.to_dict() for alert in alerts])
    except:
        return jsonify([])  # Return empty list if error

@app.route('/api/pending-analyses')
@require_auth
def get_pending_analyses():
    """Get analyses pending approval"""
    if not FEATURES_ENABLED['auto_analysis']:
        return jsonify({'error': 'Auto-analysis not enabled'}), 404
    
    try:
        analyses = enhanced_app.analyzer.get_pending_analyses() if enhanced_app.analyzer else []
        return jsonify([analysis.to_dict() for analysis in analyses])
    except:
        return jsonify([])

@app.route('/api/feedback', methods=['POST'])
@require_auth
def submit_feedback():
    """Submit feedback on analysis"""
    if not FEATURES_ENABLED['hfrl']:
        return jsonify({'error': 'HFRL not enabled'}), 404
    
    data = request.json
    analysis_id = data.get('analysis_id')
    feedback_data = data.get('feedback')
    
    if not analysis_id or not feedback_data:
        return jsonify({'error': 'Missing required data'}), 400
    
    try:
        # Process feedback
        if enhanced_app.feedback_system:
            enhanced_app.feedback_system.record_feedback(
                analysis_id,
                feedback_data,
                session.get('user_id', 'anonymous')
            )
        
        # Update analysis status if approved
        if feedback_data.get('type') == 'approval' and enhanced_app.analyzer:
            enhanced_app.analyzer.approve_analysis(analysis_id)
        
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/weekly-report')
@require_auth
def get_weekly_report():
    """Get weekly report"""
    if not FEATURES_ENABLED['auto_reports']:
        return jsonify({'error': 'Auto-reports not enabled'}), 404
    
    try:
        report = enhanced_app.report_generator.get_latest_report('weekly') if enhanced_app.report_generator else None
        if report:
            return jsonify(report.to_dict())
        
        # Generate new report if none exists
        if enhanced_app.report_generator:
            report = enhanced_app.report_generator.generate_report('weekly')
            return jsonify(report.to_dict())
        else:
            return jsonify({'error': 'Report generator not available'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/learning-insights')
@require_auth
def get_learning_insights():
    """Get insights from reinforcement learning"""
    if not FEATURES_ENABLED['hfrl']:
        return jsonify({'error': 'HFRL not enabled'}), 404
    
    try:
        insights = enhanced_app.feedback_system.get_learning_insights() if enhanced_app.feedback_system else {}
        return jsonify(insights)
    except:
        return jsonify({})

@app.route('/api/metrics')
@require_auth
def get_metrics():
    """Get system metrics"""
    try:
        metrics = {
            'active_alerts': len(enhanced_app.active_alerts) if FEATURES_ENABLED['monitoring'] else 0,
            'pending_analyses': len(enhanced_app.pending_analyses) if FEATURES_ENABLED['auto_analysis'] else 0,
            'total_feedbacks': enhanced_app.feedback_system.get_total_feedbacks() if FEATURES_ENABLED['hfrl'] and enhanced_app.feedback_system else 0,
            'avg_confidence': enhanced_app.analyzer.get_average_confidence() if FEATURES_ENABLED['auto_analysis'] and enhanced_app.analyzer else 0
        }
        return jsonify(metrics)
    except Exception as e:
        return jsonify({
            'active_alerts': 0,
            'pending_analyses': 0,
            'total_feedbacks': 0,
            'avg_confidence': 0
        })

@app.route('/api/dashboard-data')
@require_auth
def get_dashboard_data():
    """Get all dashboard data in one call"""
    try:
        data = {
            'metrics': {
                'active_alerts': len(enhanced_app.active_alerts) if FEATURES_ENABLED['monitoring'] else 0,
                'trends_analyzed': session.get('trends_analyzed_count', 0),
                'avg_confidence': enhanced_app.analyzer.get_average_confidence() if FEATURES_ENABLED['auto_analysis'] and enhanced_app.analyzer else 0,
                'pending_approval': len(enhanced_app.pending_analyses) if FEATURES_ENABLED['auto_analysis'] else 0
            },
            'alerts': [],
            'recent_analyses': [],
            'trend_activity': {
                'dates': [],
                'alerts': [],
                'analyses': []
            }
        }
        
        # Get recent alerts
        if FEATURES_ENABLED['monitoring'] and enhanced_app.monitor:
            try:
                alerts = enhanced_app.monitor.get_recent_alerts(limit=5)
                data['alerts'] = [alert.to_dict() for alert in alerts]
            except:
                pass
        
        # Get recent analyses
        if FEATURES_ENABLED['auto_analysis'] and enhanced_app.analyzer:
            try:
                analyses = enhanced_app.analyzer.get_recent_analyses(limit=5)
                data['recent_analyses'] = [analysis.to_dict() for analysis in analyses]
            except:
                pass
        
        return jsonify(data)
    except Exception as e:
        print(f"Dashboard data error: {e}")
        return jsonify({
            'metrics': {
                'active_alerts': 0,
                'trends_analyzed': 0,
                'avg_confidence': 0,
                'pending_approval': 0
            },
            'alerts': [],
            'recent_analyses': [],
            'trend_activity': {
                'dates': [],
                'alerts': [],
                'analyses': []
            }
        })

# ─── WebSocket Events ───────────────────────────────────────────────────────
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f'Client connected: {request.sid}')
    emit('connected', {
        'message': 'Connected to Schaeffler Mobility Insight Platform',
        'features': FEATURES_ENABLED
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f'Client disconnected: {request.sid}')

@socketio.on('request_analysis')
def handle_analysis_request(data):
    """Handle manual analysis request"""
    if not FEATURES_ENABLED['auto_analysis']:
        emit('error', {'message': 'Auto-analysis not enabled'})
        return
    
    trend_id = data.get('trend_id')
    if trend_id and enhanced_app.analyzer:
        try:
            # Trigger analysis for specific trend
            analysis = enhanced_app.analyzer.analyze_trend_by_id(trend_id)
            emit('analysis_complete', analysis.to_dict())
        except Exception as e:
            emit('error', {'message': str(e)})

@socketio.on('manual_alert')
def handle_manual_alert(data):
    """Handle manually created alert"""
    if not FEATURES_ENABLED['monitoring']:
        emit('error', {'message': 'Monitoring not enabled'})
        return
    
    if enhanced_app.monitor:
        try:
            alert = enhanced_app.monitor.create_manual_alert(
                title=data.get('title'),
                description=data.get('description'),
                category=data.get('category', 'manual'),
                severity=data.get('severity', 'medium')
            )
            
            # Broadcast to all clients
            socketio.emit('new_alert', alert.to_dict())
        except Exception as e:
            emit('error', {'message': str(e)})

@socketio.on('refresh_dashboard')
def handle_refresh_dashboard():
    """Handle dashboard refresh request"""
    try:
        # Emit updated data
        emit('dashboard_update', {
            'timestamp': datetime.now().isoformat(),
            'active_alerts': len(enhanced_app.active_alerts),
            'pending_analyses': len(enhanced_app.pending_analyses)
        })
    except Exception as e:
        emit('error', {'message': str(e)})

# ─── Error Handlers ─────────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

# ─── Main ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Start enhanced features
    enhanced_app.start()
    
    # Run Flask with SocketIO
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)