# Solar Website Analysis Tools
# Contains three main functions: get_insights, get_data_layers, generate_report

from .solar_insights import get_insights
from .solar_data_layers import get_data_layers  
from .solar_report import generate_report

__all__ = ['get_insights', 'get_data_layers', 'generate_report']