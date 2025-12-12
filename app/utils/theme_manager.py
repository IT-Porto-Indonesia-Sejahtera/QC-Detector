
import datetime

class ThemeManager:
    @staticmethod
    def is_dark_mode():
        """Returns True if current time is between 6 PM and 6 AM."""
        hour = datetime.datetime.now().hour
        # 6 PM (18) to 6 AM (6) is Dark
        # So if hour >= 18 OR hour < 6
        return hour >= 18 or hour < 6

    @staticmethod
    def get_colors():
        # Always return light theme, ignoring dark mode from OS
        return {
            "bg_main": "white",
            "bg_panel": "white",
            "bg_card": "#F5F5F5",
            "text_main": "#333333",
            "text_sub": "#666666",
            "border": "#E0E0E0",
            "input_bg": "white",
            "input_text": "#333333",
            "btn_bg": "#F5F5F5",
            "btn_text": "#333333",
            "overlay_dim": "rgba(0, 0, 0, 50)"
        }

    @staticmethod
    def apply_theme_to_widget(widget, theme=None):
        """Helper to set generic window style."""
        if not theme: theme = ThemeManager.get_colors()
        widget.setStyleSheet(f"""
            QWidget {{
                background-color: {theme['bg_main']};
                color: {theme['text_main']};
            }}
        """)
