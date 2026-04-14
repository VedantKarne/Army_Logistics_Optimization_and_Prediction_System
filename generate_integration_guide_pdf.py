"""
DATABASE_INTEGRATION_GUIDE.md -> PDF converter
Saves: docs/DATABASE_INTEGRATION_GUIDE.pdf
"""

import os, sys
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from datetime import datetime

# ?? Palette ???????????????????????????????????????????????????????????????????
DARK_BG     = (18, 24, 38)
SECTION_BG  = (30, 42, 65)
ACCENT_GOLD = (212, 168, 78)
ACCENT_BLUE = (52, 120, 190)
ACCENT_GRN  = (46, 139, 87)
ACCENT_RED  = (192, 57, 43)
ACCENT_ORG  = (200, 100, 30)
WHITE       = (255, 255, 255)
TEXT_DARK   = (22, 33, 52)
TEXT_MID    = (70, 85, 110)
TEXT_LIGHT  = (200, 210, 228)
CODE_BG     = (28, 35, 52)
CODE_FG     = (170, 215, 135)
WARN_BG     = (255, 248, 220)
NOTE_BG     = (230, 242, 255)

PW = 210   # A4 width mm
LM = 15    # left margin
RM = 15    # right margin
TW = PW - LM - RM   # text width = 180 mm


class GuidePDF(FPDF):
    def __init__(self):
        super().__init__('P', 'mm', 'A4')
        self.set_auto_page_break(auto=True, margin=20)
        self.set_left_margin(LM)
        self.set_right_margin(RM)

    def header(self):
        if self.page_no() == 1:
            return
        self.set_fill_color(*DARK_BG)
        self.rect(0, 0, PW, 11, 'F')
        self.set_y(1.5)
        self.set_font('Helvetica', 'B', 7.5)
        self.set_text_color(*ACCENT_GOLD)
        self.cell(0, 8, 'MILITARY VEHICLE INVENTORY LOGISTICS OPTIMIZATION AND PREDICTION SYSTEM'
                  '  |  Database Integration Guide  |  INTERNAL', align='C')
        self.set_y(13)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-12)
        self.set_fill_color(*DARK_BG)
        self.rect(0, self.h - 12, PW, 12, 'F')
        self.set_font('Helvetica', '', 7)
        self.set_text_color(*TEXT_LIGHT)
        self.cell(0, 12, f'Generated: {datetime.now().strftime("%d %b %Y, %H:%M")}', align='L')
        self.set_y(-12)
        self.cell(0, 12, f'Page {self.page_no()}', align='R')

    # ?? Helpers ???????????????????????????????????????????????????????????????
    def h_rule(self, color=ACCENT_GOLD, lw=0.3):
        self.set_draw_color(*color)
        self.set_line_width(lw)
        x = self.get_x(); y = self.get_y()
        self.line(LM, y, PW - RM, y)
        self.ln(2)

    def body(self, text, sz=9, color=TEXT_DARK):
        self.set_font('Helvetica', '', sz)
        self.set_text_color(*color)
        self.set_x(LM)
        self.multi_cell(TW, 5.5, text)
        self.ln(1)

    def bullet(self, items, sz=9, indent=4, color=TEXT_DARK):
        self.set_font('Helvetica', '', sz)
        self.set_text_color(*color)
        bw = TW - indent - 5
        for item in items:
            self.set_x(LM + indent)
            self.cell(5, 5.5, '-')
            x = self.get_x(); y = self.get_y()
            self.set_xy(x, y)
            self.multi_cell(bw, 5.5, item)

    def code(self, lines, max_lines=20):
        clipped = lines[:max_lines]
        if len(lines) > max_lines:
            clipped.append(f'  ... ({len(lines)-max_lines} more lines)')
        bh = len(clipped) * 4.5 + 5
        x, y = LM, self.get_y()
        self.set_fill_color(*CODE_BG)
        self.rect(x, y, TW, bh, 'F')
        self.set_xy(x + 2, y + 2)
        self.set_font('Courier', '', 7.2)
        self.set_text_color(*CODE_FG)
        for line in clipped:
            safe = line.encode('latin-1', errors='replace').decode('latin-1')[:115]
            self.cell(TW - 4, 4.5, safe, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_x(x + 2)
        self.ln(2)
        self.set_text_color(*TEXT_DARK)

    def note_box(self, text, bg=NOTE_BG, label='NOTE', label_color=ACCENT_BLUE):
        x, y = LM, self.get_y()
        self.set_font('Helvetica', '', 8.5)
        lines = self._estimate_lines(text, TW - 20, 8.5)
        bh = max(lines * 5 + 8, 14)
        self.set_fill_color(*bg)
        self.rect(x, y, TW, bh, 'F')
        self.set_draw_color(*label_color)
        self.set_line_width(1.2)
        self.line(x, y, x, y + bh)
        self.set_xy(x + 5, y + 2)
        self.set_font('Helvetica', 'B', 8)
        self.set_text_color(*label_color)
        self.cell(18, 5, label + ':')
        self.set_font('Helvetica', '', 8.5)
        self.set_text_color(*TEXT_DARK)
        self.set_xy(x + 5, self.get_y() + 5)
        self.multi_cell(TW - 8, 5, text)
        self.ln(2)

    def _estimate_lines(self, text, w, sz):
        char_per_line = int(w / (sz * 0.45))
        words = text.split()
        lines, cur = 1, 0
        for word in words:
            if cur + len(word) + 1 > char_per_line:
                lines += 1; cur = len(word)
            else:
                cur += len(word) + 1
        return lines

    def step_banner(self, number, title, subtitle=''):
        self.ln(3)
        bh = 14 if subtitle else 10
        x, y = LM, self.get_y()
        # Step number badge
        self.set_fill_color(*ACCENT_GOLD)
        self.set_text_color(*DARK_BG)
        self.set_font('Helvetica', 'B', 9)
        self.rect(x, y, 28, bh, 'F')
        self.set_xy(x, y)
        self.cell(28, bh, f'STEP {number}', align='C')
        # Title bar
        self.set_fill_color(*DARK_BG)
        self.set_text_color(*ACCENT_GOLD)
        self.set_font('Helvetica', 'B', 12)
        self.rect(x + 29, y, TW - 29, bh, 'F')
        self.set_xy(x + 31, y + (0 if subtitle else 0))
        self.cell(TW - 33, 10, title)
        if subtitle:
            self.set_xy(x + 31, y + 8)
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(*TEXT_LIGHT)
            self.cell(TW - 33, 6, subtitle)
        self.ln(bh + 3)
        self.set_text_color(*TEXT_DARK)

    def section_head(self, title, color=ACCENT_BLUE):
        self.ln(2)
        self.set_font('Helvetica', 'B', 10.5)
        self.set_text_color(*color)
        self.set_x(LM)
        self.cell(0, 7, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.h_rule(color=color, lw=0.2)

    def sub_head(self, title):
        self.ln(1)
        self.set_font('Helvetica', 'B', 9)
        self.set_text_color(*TEXT_MID)
        self.set_x(LM)
        self.cell(0, 6, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*TEXT_DARK)

    def table_header(self, cols, widths):
        self.set_fill_color(*SECTION_BG)
        self.set_text_color(*WHITE)
        self.set_font('Helvetica', 'B', 8)
        self.set_x(LM)
        for col, w in zip(cols, widths):
            self.cell(w, 7, col, border=0, fill=True)
        self.ln()

    def table_row(self, cells, widths, shade=False):
        bg = (240, 245, 252) if shade else WHITE
        self.set_fill_color(*bg)
        self.set_text_color(*TEXT_DARK)
        self.set_font('Helvetica', '', 8)
        self.set_x(LM)
        row_h = 6
        # Calculate max height
        for cell, w in zip(cells, widths):
            self.cell(w, row_h, str(cell), border=0, fill=True)
        self.ln()

    def check_row(self, cells, widths, shade=False, status=None):
        """Table row with colored status badge."""
        bg = (240, 245, 252) if shade else WHITE
        self.set_fill_color(*bg)
        self.set_x(LM)
        for i, (cell, w) in enumerate(zip(cells, widths)):
            if i == 1 and status == 'yes':
                self.set_text_color(*ACCENT_GRN)
                self.set_font('Helvetica', 'B', 8)
            elif i == 1 and status == 'no':
                self.set_text_color(*ACCENT_RED)
                self.set_font('Helvetica', 'B', 8)
            else:
                self.set_text_color(*TEXT_DARK)
                self.set_font('Helvetica', '', 8)
            self.cell(w, 6, str(cell), fill=True)
        self.ln()


# ??????????????????????????????????????????????????????????????????????????????
# COVER PAGE
# ??????????????????????????????????????????????????????????????????????????????
def make_cover(pdf: GuidePDF):
    pdf.add_page()
    pdf.set_fill_color(*DARK_BG)
    pdf.rect(0, 0, PW, 297, 'F')

    pdf.set_fill_color(*ACCENT_GOLD)
    pdf.rect(0, 0, PW, 5, 'F')
    pdf.rect(0, 292, PW, 5, 'F')

    # Vertical accent bar
    pdf.set_fill_color(30, 42, 65)
    pdf.rect(0, 5, 8, 287, 'F')

    pdf.set_y(38)
    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(*ACCENT_GOLD)
    pdf.cell(0, 6, 'INTERNAL TECHNICAL DOCUMENT  |  FOR AUTHORIZED PERSONNEL ONLY', align='C',
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(6)

    # Title block
    pdf.set_fill_color(30, 42, 65)
    pdf.rect(18, pdf.get_y(), 174, 68, 'F')
    pdf.set_draw_color(*ACCENT_GOLD)
    pdf.set_line_width(0.7)
    pdf.rect(18, pdf.get_y(), 174, 68)
    pdf.ln(10)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(*ACCENT_GOLD)
    pdf.cell(0, 7, 'MILITARY VEHICLE INVENTORY LOGISTICS', align='C',
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 7, 'OPTIMIZATION AND PREDICTION SYSTEM', align='C',
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)
    pdf.set_font('Helvetica', 'B', 18)
    pdf.set_text_color(*WHITE)
    pdf.cell(0, 11, 'DATABASE INTEGRATION GUIDE', align='C',
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(6)
    pdf.set_font('Helvetica', '', 9.5)
    pdf.set_text_color(*TEXT_LIGHT)
    pdf.cell(0, 6, 'Step-by-step instructions to connect the ML pipeline', align='C',
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, 'to a real Army vehicle telemetry database', align='C',
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(32)

    # Info cards
    def card(label, value, x, y, w=85):
        pdf.set_fill_color(24, 34, 55)
        pdf.rect(x, y, w, 16, 'F')
        pdf.set_draw_color(*ACCENT_GOLD)
        pdf.set_line_width(0.25)
        pdf.rect(x, y, w, 16)
        pdf.set_xy(x + 3, y + 2)
        pdf.set_font('Helvetica', '', 6.5)
        pdf.set_text_color(*ACCENT_GOLD)
        pdf.cell(w - 6, 4.5, label.upper())
        pdf.set_xy(x + 3, y + 7)
        pdf.set_font('Helvetica', 'B', 8.5)
        pdf.set_text_color(*WHITE)
        pdf.cell(w - 6, 6, value)

    card('For',            'Database Engineer / Integration Specialist',    18, 155, 174)
    card('Document Type',  'Integration & Configuration Guide',              18, 176, 84)
    card('Reference Doc',  'Army_ML_Pipeline_Documentation.pdf',            107, 176, 85)
    card('Date',           datetime.now().strftime('%d %B %Y'),              18, 197, 84)
    card('Pipeline Version', 'v3.1 (Temporal-Fusion Ensemble)',             107, 197, 85)
    card('Est. Time',      '2 - 4 Hours (depending on schema differences)', 18, 218, 174)


# ??????????????????????????????????????????????????????????????????????????????
# OVERVIEW PAGE
# ??????????????????????????????????????????????????????????????????????????????
def make_overview(pdf: GuidePDF):
    pdf.add_page()
    pdf.set_y(18)

    # Banner
    pdf.set_fill_color(*SECTION_BG)
    pdf.rect(LM, pdf.get_y(), TW, 12, 'F')
    pdf.set_xy(LM + 2, pdf.get_y() + 1.5)
    pdf.set_font('Helvetica', 'B', 13)
    pdf.set_text_color(*WHITE)
    pdf.cell(0, 9, 'OVERVIEW')
    pdf.ln(14)
    pdf.set_text_color(*TEXT_DARK)

    pdf.body(
        'This ML pipeline was developed and validated on a synthetic database that mirrors a real '
        'Army vehicle telemetry system. Your job is to point all ML scripts at the real production '
        'database and verify the schema matches what the pipeline expects.',
        sz=9.5
    )
    pdf.body(
        'The pipeline does NOT generate any data ? it only reads from the database via SQL queries. '
        'Once DB credentials and schema are confirmed, the pipeline runs identically on real data.',
        sz=9.5
    )

    pdf.note_box(
        'data_generation/ is intentionally excluded from this repository. '
        'Those scripts were used during development to build a synthetic test database. '
        'The real pipeline starts from feature_engineering.py onwards.',
        label='IMPORTANT', label_color=ACCENT_ORG, bg=(255, 245, 220)
    )

    pdf.section_head('What This Document Covers')
    steps = [
        ('Step 1', 'Update DB_CONFIG credentials in all 11 ML files'),
        ('Step 2', 'Verify your real database schema matches the required 7 tables'),
        ('Step 3', 'Run the one-time vehicle_status label assignment script'),
        ('Step 4', 'Execute the full ML pipeline on real data'),
        ('Step 5', 'Verify successful integration via outputs and DB checks'),
        ('Step 6', 'Delete synthetic-era artefacts (models, reports, parquet)'),
    ]
    pdf.table_header(['Step', 'Action'], [28, 152])
    for i, (step, action) in enumerate(steps):
        pdf.table_row([step, action], [28, 152], shade=(i % 2 == 0))

    pdf.ln(3)
    pdf.section_head('Pipeline Architecture (Real Data Flow)')
    pdf.body('Once integrated, data flows through the pipeline as follows:', sz=9)

    pdf.set_fill_color(*CODE_BG)
    flow = [
        'Real Army MySQL Database',
        '    |',
        '    |-- vehicles table          (fleet records)',
        '    |-- telemetry_data table    (sensor readings)',
        '    |-- maintenance_records     (service history + vehicle_status labels)',
        '    |-- diagnostic_codes        (DTC fault records)',
        '    |-- operational_logs        (trip data)',
        '    +-- fuel_records            (efficiency logs)',
        '    |',
        '    v',
        'assign_vehicle_status.py   [ONE-TIME SETUP: adds 5-class labels to maintenance_records]',
        '    |',
        '    v',
        'feature_engineering.py     [SQL -> vehicle_features.parquet (1 row per vehicle)]',
        '    |',
        '    v',
        'train_health_model.py      [XGBoost + LightGBM + TabNet with Bayesian HPO]',
        '    |',
        '    v  (optional)',
        'temporal_model.py          [Bi-LSTM on last-50 telemetry steps]',
        '    |',
        '    v',
        'optimize_ensemble.py       [Tournament -> champion ensemble selected]',
        '    |',
        '    v',
        'run_inference.py           -> health_scores table (predictions for all vehicles)',
        '    |',
        '    v',
        'evaluate_ensemble.py       -> reports/ (confusion matrix, ROC curves, F1 metrics)',
    ]
    pdf.code(flow, max_lines=30)


# ??????????????????????????????????????????????????????????????????????????????
# STEP 1 ? CREDENTIALS
# ??????????????????????????????????????????????????????????????????????????????
def make_step1(pdf: GuidePDF):
    pdf.add_page()
    pdf.set_y(18)
    pdf.step_banner('1', 'Update Database Credentials in All ML Files')

    pdf.body(
        'Find the DB_CONFIG block in every file listed below and replace it with your real '
        'MySQL credentials. The block looks like this in every file:'
    )

    pdf.sub_head('BEFORE (synthetic/dev credentials ? change these):')
    pdf.code([
        'DB_CONFIG = {',
        "    'host':     'localhost',",
        "    'port':     3306,",
        "    'database': 'military_vehicle_health',",
        "    'user':     'root',",
        "    'password': 'vedant@14',       # <-- CHANGE THIS",
        "    'charset':  'utf8mb4',",
        '}',
    ])

    pdf.sub_head('AFTER (your real database credentials):')
    pdf.code([
        'DB_CONFIG = {',
        "    'host':     'YOUR_DB_HOST',    # e.g. '192.168.1.100' or 'db.army.mil.in'",
        "    'port':     3306,              # change if MySQL runs on a non-standard port",
        "    'database': 'YOUR_DB_NAME',    # your actual database name",
        "    'user':     'YOUR_DB_USER',",
        "    'password': 'YOUR_DB_PASSWORD',",
        "    'charset':  'utf8mb4',",
        '}',
    ])

    pdf.section_head('Files That Require This Change (11 files)')
    files = [
        ('assign_vehicle_status.py',   'Army_ML_Pipeline_and_Files/'),
        ('feature_engineering.py',     'Army_ML_Pipeline_and_Files/'),
        ('train_health_model.py',      'Army_ML_Pipeline_and_Files/'),
        ('temporal_model.py',          'Army_ML_Pipeline_and_Files/'),
        ('run_inference.py',           'Army_ML_Pipeline_and_Files/'),
        ('evaluate_ensemble.py',       'Army_ML_Pipeline_and_Files/'),
        ('export_database.py',         'database_utils/'),
        ('export_db_stats.py',         'database_utils/'),
        ('verify_database.py',         'database_utils/'),
        ('verify_labels.py',           'database_utils/'),
        ('find_db_location.py',        'database_utils/'),
    ]
    pdf.table_header(['File', 'Folder'], [80, 100])
    for i, (f, folder) in enumerate(files):
        pdf.table_row([f, folder], [80, 100], shade=(i % 2 == 0))

    pdf.ln(2)
    pdf.note_box(
        'Security Note: Do not commit real passwords to GitHub. '
        'Consider using environment variables instead: '
        "os.environ.get('DB_PASSWORD', 'fallback')",
        label='SECURITY', label_color=ACCENT_RED, bg=(255, 235, 235)
    )


# ??????????????????????????????????????????????????????????????????????????????
# STEP 2 ? SCHEMA VERIFICATION
# ??????????????????????????????????????????????????????????????????????????????
def make_step2(pdf: GuidePDF):
    pdf.add_page()
    pdf.set_y(18)
    pdf.step_banner('2', 'Verify Your Database Schema',
                    'Run the verification script, then cross-check each table below')

    pdf.sub_head('Run verification first:')
    pdf.code(['generate_data_env\\Scripts\\python.exe database_utils\\verify_database.py'])

    # ?? Table 1: vehicles ??????????????????????????????????????????????????
    pdf.section_head('Table 1: vehicles')
    pdf.table_header(['Column Name', 'Type', 'Used By'], [55, 35, 90])
    rows = [
        ('vehicle_id',         'VARCHAR / INT (PK)', 'All scripts ? primary join key'),
        ('vehicle_type',       'VARCHAR',            'feature_engineering.py (one-hot encoding)'),
        ('acquisition_date',   'DATE',               'feature_engineering.py (vehicle age calc)'),
        ('operational_status', 'VARCHAR',            'verify_database.py'),
    ]
    for i, r in enumerate(rows):
        pdf.table_row(r, [55, 35, 90], shade=(i % 2 == 0))

    # ?? Table 2: telemetry_data ????????????????????????????????????????????
    pdf.section_head('Table 2: telemetry_data  (most critical ? check all columns)')
    pdf.table_header(['Expected Column', 'Description', 'If Your Name Differs'], [55, 60, 65])
    trows = [
        ('vehicle_id',                   'FK to vehicles',          'Update SQL JOIN'),
        ('timestamp',                    'Reading datetime',         'Update ORDER BY / GROUP BY'),
        ('engine_coolant_temp_celsius',  'Coolant temp (degrees C)', 'Add AS alias in query'),
        ('battery_voltage',              'Voltage reading (V)',      'Add AS alias in query'),
        ('engine_rpm',                   'Engine RPM',              'Update temporal_model.py L19'),
        ('engine_load_percent',          '0-100% engine load',      'Add AS alias in query'),
        ('fuel_consumption_lph',         'Fuel burn (litres/hour)',  'Add AS alias in query'),
        ('idle_time_minutes',            'Idle mins per reading',    'Add AS alias in query'),
        ('current_speed_kmph',           'Speed (km/h)',             'Add AS alias in query'),
        ('oil_pressure_psi',             'Oil pressure',            'Update temporal_model.py'),
        ('tire_pressure_psi_avg',        'Avg tire pressure',        'Update temporal_model.py'),
        ('odometer_km',                  'Total km reading',         'Update temporal_model.py'),
        ('fuel_level_percent',           'Fuel tank %',              'Update temporal_model.py'),
    ]
    for i, r in enumerate(trows):
        pdf.table_row(r, [55, 60, 65], shade=(i % 2 == 0))

    pdf.ln(2)
    pdf.body('How to remap column names using SQL AS aliases (no Python changes needed):', sz=8.5)
    pdf.code([
        '# In feature_engineering.py, find the telemetry SQL query and add AS aliases:',
        'SELECT',
        '    vehicle_id,',
        '    coolant_temp       AS engine_coolant_temp_celsius,  -- map your name -> expected',
        '    volt               AS battery_voltage,',
        '    load_pct           AS engine_load_percent,',
        '    fuel_lph           AS fuel_consumption_lph,',
        '    idle_mins          AS idle_time_minutes,',
        '    speed_kph          AS current_speed_kmph,',
        '    reading_time       AS timestamp',
        'FROM vehicle_telemetry                                  -- if table name also differs',
        'WHERE vehicle_id = %s ORDER BY reading_time',
    ])

    # ?? Table 3: maintenance_records ???????????????????????????????????????
    pdf.section_head('Table 3: maintenance_records')
    pdf.table_header(['Column', 'Description', 'Notes'], [52, 80, 48])
    mrows = [
        ('maintenance_id',          'Primary key (auto-increment)',    ''),
        ('vehicle_id',              'FK to vehicles',                  'Required for joins'),
        ('service_date',            'Date of service',                 'DATE type'),
        ('service_type',            "'emergency'/'corrective'/'preventive'", 'MUST match exactly'),
        ('pre_service_health_score','Health score before service (0-100)', 'DECIMAL'),
        ('post_service_health_score','Health score after service',     'DECIMAL'),
        ('service_cost',            'Cost (INR)',                      'DECIMAL'),
        ('vehicle_status',          '5-class label ADDED by pipeline', 'Added by Step 3'),
    ]
    for i, r in enumerate(mrows):
        pdf.table_row(r, [52, 80, 48], shade=(i % 2 == 0))

    pdf.note_box(
        "If your service_type uses different values (e.g. 'urgent' instead of 'emergency'), "
        "update SVC_TYPE_BASE dictionary in assign_vehicle_status.py around line 71.",
        label='NOTE', label_color=ACCENT_BLUE
    )

    # ?? Tables 4-6 ????????????????????????????????????????????????????????
    pdf.section_head('Table 4: diagnostic_codes')
    pdf.table_header(['Column', 'Description'], [60, 120])
    dcols = [
        ('vehicle_id',           'FK to vehicles'),
        ('code',                 "DTC code string (e.g. 'P0300')"),
        ('severity',             "'critical' / 'major' / 'minor' / 'warning'"),
        ('system_affected',      "e.g. 'Engine', 'Electrical', 'Brakes'"),
        ('detected_timestamp',   'DATETIME when code was triggered'),
        ('resolved_timestamp',   'DATETIME when resolved (NULL if still active)'),
        ('is_active',            'BOOLEAN: 1=active, 0=resolved'),
    ]
    for i, r in enumerate(dcols):
        pdf.table_row(r, [60, 120], shade=(i % 2 == 0))

    pdf.section_head('Table 5: operational_logs')
    pdf.table_header(['Column', 'Description'], [60, 120])
    ocols = [
        ('vehicle_id',              'FK to vehicles'),
        ('mission_type',            "e.g. 'combat_training', 'transport', 'patrol'"),
        ('terrain_difficulty_score','1-10 difficulty rating'),
        ('harsh_braking_count',     'Number of harsh braking events per trip'),
        ('trip_distance_km',        'Trip distance in km'),
        ('cargo_weight_kg',         'Cargo load in kg'),
    ]
    for i, r in enumerate(ocols):
        pdf.table_row(r, [60, 120], shade=(i % 2 == 0))

    pdf.section_head('Table 6: fuel_records')
    pdf.table_header(['Column', 'Description'], [60, 120])
    fcols = [
        ('vehicle_id',          'FK to vehicles'),
        ('refuel_date',         'DATE of refuelling'),
        ('fuel_efficiency_kmpl','Kilometres per litre at this refuel'),
    ]
    for i, r in enumerate(fcols):
        pdf.table_row(r, [60, 120], shade=(i % 2 == 0))

    pdf.section_head('Table 7: health_scores  (OUTPUT ? create if not exists)')
    pdf.body("This table is written to by run_inference.py. Create it in your DB if it doesn't exist:", sz=8.5)
    pdf.code([
        'CREATE TABLE IF NOT EXISTS health_scores (',
        '    score_id                  INT AUTO_INCREMENT PRIMARY KEY,',
        '    vehicle_id                VARCHAR(20) NOT NULL,',
        '    assessment_date           DATE NOT NULL,',
        '    overall_health_score      DECIMAL(5,2),',
        "    health_status             ENUM('critical','poor','fair','good','excellent'),",
        '    engine_health_score       DECIMAL(5,2),',
        '    transmission_health_score DECIMAL(5,2),',
        '    brake_system_score        DECIMAL(5,2),',
        '    electrical_system_score   DECIMAL(5,2),',
        '    predicted_days_to_service INT,',
        '    predicted_service_date    DATE,',
        '    confidence_level          DECIMAL(5,2),',
        "    risk_category             ENUM('critical','high','medium','low'),",
        '    recommended_action        TEXT,',
        '    risk_evidence             TEXT,',
        '    model_version             VARCHAR(50),',
        '    created_at                TIMESTAMP DEFAULT CURRENT_TIMESTAMP,',
        '    INDEX idx_vehicle_date (vehicle_id, assessment_date)',
        ');',
    ])


# ??????????????????????????????????????????????????????????????????????????????
# STEPS 3?6
# ??????????????????????????????????????????????????????????????????????????????
def make_steps_3_to_6(pdf: GuidePDF):
    pdf.add_page()
    pdf.set_y(18)

    # STEP 3
    pdf.step_banner('3', 'Run the One-Time Label Assignment',
                    'Adds vehicle_status column and assigns 5-class health labels to maintenance_records')

    pdf.body(
        'Before training the ML models, you must add a vehicle_status classification column '
        'to maintenance_records. This is a ONE-TIME setup step ? run it once on your real DB:'
    )
    pdf.code([
        'generate_data_env\\Scripts\\python.exe -X utf8 '
        'Army_ML_Pipeline_and_Files\\assign_vehicle_status.py',
    ])
    pdf.body('This script:', sz=9)
    pdf.bullet([
        'Adds vehicle_status VARCHAR(20) column to maintenance_records',
        'Computes a composite health score (service_type x DTC severity x recency) per record',
        'Assigns labels using exact quintile bucketing: bottom 20% = Critical, next 20% = Poor, '
        'middle 20% = Attention, next 20% = Good, top 20% = Excellent',
        'Guarantees a perfectly class-balanced training dataset (20% each class)',
    ])
    pdf.sub_head('Expected output:')
    pdf.code([
        '============================',
        'LABEL DISTRIBUTION',
        '============================',
        '  Critical     xxxx  (20.00%)  ##########',
        '  Poor         xxxx  (20.00%)  ##########',
        '  Attention    xxxx  (20.00%)  ##########',
        '  Good         xxxx  (20.00%)  ##########',
        '  Excellent    xxxx  (20.00%)  ##########',
        'Done. Run feature_engineering.py next.',
    ])
    pdf.note_box(
        "If you see errors, verify that service_type values in your DB are exactly "
        "'emergency', 'corrective', or 'preventive' (lowercase). "
        "If different, update SVC_TYPE_BASE in assign_vehicle_status.py.",
        label='CHECK', label_color=ACCENT_ORG, bg=(255, 245, 220)
    )

    # STEP 4
    pdf.step_banner('4', 'Run the Full ML Pipeline')

    pdf.sub_head('Option A ? Full automatic run via orchestrator:')
    pdf.code(['.\\run_pipeline.ps1'])

    pdf.sub_head('Option B ? Run each step individually (recommended for first integration):')
    pdf.code([
        '# Step 1: Build feature matrix from real DB (~5-15 min depending on data size)',
        'generate_data_env\\Scripts\\python.exe -X utf8 '
        'Army_ML_Pipeline_and_Files\\feature_engineering.py',
        '',
        '# Step 2: Train all three models (20-60 min, GPU optional)',
        'generate_data_env\\Scripts\\python.exe -X utf8 '
        'Army_ML_Pipeline_and_Files\\train_health_model.py',
        '',
        '# Step 3 (Optional): Generate Bi-LSTM temporal probability channel',
        'generate_data_env\\Scripts\\python.exe -X utf8 '
        'Army_ML_Pipeline_and_Files\\temporal_model.py',
        '',
        '# Step 4: Optimise ensemble ? selects champion prediction strategy',
        'generate_data_env\\Scripts\\python.exe -X utf8 '
        'Army_ML_Pipeline_and_Files\\optimize_ensemble.py',
        '',
        '# Step 5: Run inference -> writes to health_scores table',
        'generate_data_env\\Scripts\\python.exe -X utf8 '
        'Army_ML_Pipeline_and_Files\\run_inference.py',
        '',
        '# Step 6: Generate final evaluation metrics and ROC curves',
        'generate_data_env\\Scripts\\python.exe -X utf8 '
        'Army_ML_Pipeline_and_Files\\evaluate_ensemble.py',
    ])

    # STEP 5
    pdf.step_banner('5', 'Verify Integration Success')

    pdf.sub_head('5a. Verify the feature matrix was built correctly:')
    pdf.code([
        "generate_data_env\\Scripts\\python.exe -c \"",
        "import pandas as pd",
        "df = pd.read_parquet('Army_ML_Pipeline_and_Files/vehicle_features.parquet')",
        "print('Shape:', df.shape)          # Expected: (N_VEHICLES, ~59)",
        "print('Null columns:', df.isnull().all().sum())  # Should be 0",
        "print(df.head(3))",
        "\"",
    ])
    pdf.body('Expected shape: (N_VEHICLES, ~59) ? one row per vehicle, ~59 feature columns.', sz=8.5)

    pdf.sub_head('5b. Verify health_scores table was populated:')
    pdf.code(['generate_data_env\\Scripts\\python.exe database_utils\\verify_database.py'])
    pdf.body('health_scores row count should equal your total vehicle count.', sz=8.5)

    pdf.sub_head('5c. Check ML evaluation metrics:')
    pdf.body(
        'Open Army_ML_Pipeline_and_Files/reports/ensemble_evaluation_detailed.txt  '
        'Expected on real data: Macro F1 > 0.85 (baseline was 91.06% on synthetic data). '
        'If F1 drops significantly, increase N_TRIALS in train_health_model.py and retrain.',
        sz=8.5
    )

    # STEP 6
    pdf.step_banner('6', 'Delete Synthetic-Era Artefacts After Successful Integration',
                    'These files were generated from synthetic data and are now superseded by real-data outputs')

    pdf.sub_head('Delete these (old synthetic-trained artefacts):')
    pdf.code([
        '# OLD model binaries (trained on synthetic data ? pipeline regenerates these):',
        'Army_ML_Pipeline_and_Files/models/xgb_best.pkl',
        'Army_ML_Pipeline_and_Files/models/lgbm_best.pkl',
        'Army_ML_Pipeline_and_Files/models/tabnet_best.zip',
        'Army_ML_Pipeline_and_Files/models/meta_learner.pkl',
        'Army_ML_Pipeline_and_Files/models/meta_learner_rf.pkl',
        'Army_ML_Pipeline_and_Files/models/oof_xgb.npy',
        'Army_ML_Pipeline_and_Files/models/oof_lgbm.npy',
        'Army_ML_Pipeline_and_Files/models/oof_tabnet.npy',
        'Army_ML_Pipeline_and_Files/models/temporal_probs.npy',
        'Army_ML_Pipeline_and_Files/models/temporal_sequences.npy',
        '',
        '# OLD feature matrix (regenerated from real DB by feature_engineering.py):',
        'Army_ML_Pipeline_and_Files/vehicle_features.parquet',
        '',
        '# OLD reports (regenerated from real-data training):',
        'Army_ML_Pipeline_and_Files/reports/*.png',
        'Army_ML_Pipeline_and_Files/reports/*.txt',
        'Army_ML_Pipeline_and_Files/reports/mlops/run_*.json',
    ])

    pdf.sub_head('Keep these (code + lightweight config ? not data-dependent):')
    pdf.bullet([
        'All *.py scripts ? KEEP. They are data-agnostic.',
        'models/*.json ? KEEP (will be auto-overwritten by real-data training runs)',
        'docs/ ? KEEP. All documentation.',
        'database_utils/ ? KEEP. All verification scripts.',
        'run_pipeline.ps1 ? KEEP. The orchestrator.',
        'README.md, .gitignore ? KEEP.',
    ])

    pdf.note_box(
        'The .json files in models/ (ensemble_config.json, ensemble_weights.json, '
        'feature_names.json, temperature_scalars.json) are automatically OVERWRITTEN when '
        'optimize_ensemble.py runs on real data. You do not need to manually delete them.',
        label='NOTE', label_color=ACCENT_BLUE
    )


# ??????????????????????????????????????????????????????????????????????????????
# TROUBLESHOOTING
# ??????????????????????????????????????????????????????????????????????????????
def make_troubleshooting(pdf: GuidePDF):
    pdf.add_page()
    pdf.set_y(18)

    pdf.set_fill_color(*SECTION_BG)
    pdf.rect(LM, pdf.get_y(), TW, 12, 'F')
    pdf.set_xy(LM + 2, pdf.get_y() + 1.5)
    pdf.set_font('Helvetica', 'B', 13)
    pdf.set_text_color(*WHITE)
    pdf.cell(0, 9, 'TROUBLESHOOTING REFERENCE')
    pdf.ln(15)
    pdf.set_text_color(*TEXT_DARK)

    errors = [
        (
            "ProgrammingError: Unknown column 'engine_coolant_temp_celsius'",
            'Real DB uses a different telemetry column name',
            'Add SQL AS alias in feature_engineering.py (see Step 2)'
        ),
        (
            "KeyError: 'vehicle_status'",
            'assign_vehicle_status.py has not been run yet',
            'Run Step 3 first before feature_engineering.py'
        ),
        (
            'Empty feature matrix or all-NaN columns',
            'No telemetry records match your vehicle IDs in the DB join',
            'Check vehicle_id FK consistency across all tables'
        ),
        (
            'SMOTE error: n_samples < n_neighbors',
            'One or more classes has too few samples after label assignment',
            'Check label distribution output from assign_vehicle_status.py'
        ),
        (
            'UnicodeEncodeError on Windows',
            'Windows console default encoding is CP1252',
            'Always run scripts with the -X utf8 flag (already in run_pipeline.ps1)'
        ),
        (
            "health_scores table doesn't exist",
            'Table was not created in your real DB',
            'Run the CREATE TABLE SQL provided in Step 2 of this guide'
        ),
        (
            'F1 drops to < 0.70 on real data',
            'Real data distribution differs significantly from synthetic',
            'Increase N_TRIALS to 100 in train_health_model.py and retrain'
        ),
        (
            'mysql.connector.errors.InterfaceError: 2003',
            'Cannot connect to MySQL ? host or port wrong',
            'Verify DB_CONFIG host/port, check MySQL is running, check firewall'
        ),
        (
            'feature_engineering.py hangs for > 30 min',
            'DB has very large telemetry table (millions of rows)',
            'Add a LIMIT or date-range filter to the telemetry SQL query in feature_engineering.py'
        ),
        (
            'ModuleNotFoundError for xgboost/lightgbm/torch',
            'Virtual environment not activated or requirements not installed',
            'Run: generate_data_env\\Scripts\\pip.exe install -r Army_ML_Pipeline_and_Files\\requirements.txt'
        ),
    ]

    pdf.table_header(['Error / Symptom', 'Likely Cause', 'Fix'], [65, 55, 60])
    for i, (err, cause, fix) in enumerate(errors):
        bg = (240, 245, 252) if i % 2 == 0 else WHITE
        pdf.set_fill_color(*bg)
        pdf.set_x(LM)
        # Print 3 cells with auto-wrap in first col using multi-line approach
        y_start = pdf.get_y()
        pdf.set_font('Courier', '', 6.5)
        pdf.set_text_color(170, 50, 50)
        pdf.multi_cell(65, 4.5, err, fill=True)
        yend = pdf.get_y()
        row_h = yend - y_start
        pdf.set_xy(LM + 65, y_start)
        pdf.set_font('Helvetica', '', 7.5)
        pdf.set_text_color(*TEXT_DARK)
        pdf.multi_cell(55, max(row_h, 9) / max(int(row_h / 4.5), 1), cause, fill=True)
        max_y = max(pdf.get_y(), yend)
        pdf.set_xy(LM + 120, y_start)
        pdf.set_font('Helvetica', 'I', 7.5)
        pdf.set_text_color(*ACCENT_BLUE)
        pdf.multi_cell(60, max(row_h, 9) / max(int(row_h / 4.5), 1), fix, fill=True)
        pdf.set_y(max(pdf.get_y(), max_y))
        pdf.set_x(LM)

    pdf.ln(4)

    pdf.set_fill_color(*SECTION_BG)
    pdf.rect(LM, pdf.get_y(), TW, 10, 'F')
    pdf.set_xy(LM + 2, pdf.get_y() + 1)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(*WHITE)
    pdf.cell(0, 8, 'REFERENCE DOCUMENTS')
    pdf.ln(12)
    pdf.set_text_color(*TEXT_DARK)

    refs = [
        ('Army_ML_Pipeline_Documentation.pdf',
         'Root directory',
         '21-page full technical reference for every file, function, and design decision'),
        ('README_DATABASE.md',
         'docs/',
         'Database schema definitions and field-level descriptions for all 9 tables'),
        ('QUICK_REFERENCE.md',
         'docs/',
         'One-page command cheat sheet for running the pipeline'),
        ('IMPORT_INSTRUCTIONS.md',
         'docs/',
         'How to import a SQL dump file into a fresh MySQL instance'),
        ('VIRTUALENV_SETUP.md',
         'docs/',
         'Step-by-step Python virtual environment setup on Windows'),
        ('README.md',
         'Root directory',
         'Project overview, repo structure, prerequisites, and contributing guide'),
    ]
    pdf.table_header(['Document', 'Location', 'Description'], [62, 30, 88])
    for i, r in enumerate(refs):
        pdf.table_row(r, [62, 30, 88], shade=(i % 2 == 0))


# ??????????????????????????????????????????????????????????????????????????????
# MAIN
# ??????????????????????????????????????????????????????????????????????????????
def main():
    pdf = GuidePDF()
    print('Building Database Integration Guide PDF...')
    make_cover(pdf)
    make_overview(pdf)
    make_step1(pdf)
    make_step2(pdf)
    make_steps_3_to_6(pdf)
    make_troubleshooting(pdf)

    out = r'c:\Users\ADMIN\Documents\Army_ML_3_02_26\docs\DATABASE_INTEGRATION_GUIDE.pdf'
    pdf.output(out)
    sz = os.path.getsize(out) / 1024
    print(f'Saved: {out}')
    print(f'Pages: {pdf.page}   |   Size: {sz:.1f} KB')


if __name__ == '__main__':
    main()
