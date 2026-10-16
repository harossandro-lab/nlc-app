"""Colors and the global style sheet: dark navy #10233B with the orange #E2600C accent, like the web and Java apps."""
INK = "#10233B"
ORANGE = "#E2600C"
GRAY = "#5B6B7A"
LINE = "#C7D2DB"
GREEN = "#2F7A4D"
AMBER = "#B9790E"
RED = "#B23A2E"
WHITE = "#FFFFFF"

STYLE_SHEET = f"""
QWidget {{ font-family: "Segoe UI", "Inter", sans-serif; font-size: 13px; color: {INK}; }}
QMainWindow, QWidget#page {{ background: {WHITE}; }}
QFrame#topbar, QFrame#bottomnav {{ background: {INK}; }}
QLabel#brand {{ color: {WHITE}; font-size: 16px; font-weight: bold; }}
QLabel#backlink {{ color: rgba(255,255,255,210); font-size: 12px; font-weight: bold; padding-left: 24px; }}
QPushButton#navbutton {{ background: {INK}; color: {WHITE}; border: none; padding: 10px 4px; font-weight: bold; font-size: 12px; }}
QPushButton#navbutton:hover {{ background: #1B3556; }}
QLabel#heading {{ font-size: 22px; font-weight: bold; color: {INK}; }}
QLabel#subtitle {{ color: {GRAY}; font-size: 12px; }}
QLabel#tilelabel {{ font-size: 11.5px; font-weight: bold; color: {INK}; }}
QLabel#hint {{ color: {GRAY}; }}
QPushButton#accent {{ background: {ORANGE}; color: {WHITE}; border: none; padding: 7px 14px; font-weight: bold; border-radius: 3px; }}
QPushButton#accent:hover {{ background: #C95410; }}
QPushButton {{ padding: 6px 12px; }}
QLineEdit {{ border: 1px solid {LINE}; padding: 5px; border-radius: 3px; }}
QLineEdit:focus {{ border: 1px solid {ORANGE}; }}
"""
