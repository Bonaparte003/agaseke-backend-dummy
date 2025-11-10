from django import template
from django.template.defaultfilters import floatformat
from django.contrib.humanize.templatetags.humanize import intcomma

register = template.Library()

@register.filter
def currency(value, decimal_places=2):
    """
    Format a number as currency with thousands separators and specified decimal places.
    Usage: {{ value|currency }} or {{ value|currency:0 }}
    """
    if value is None:
        return "RWF 0"
    
    try:
        # Convert to float and format with thousands separators
        float_value = float(value)
        
        # Format with thousands separators
        formatted = intcomma(floatformat(float_value, decimal_places))
        
        return f"RWF {formatted}"
    except (ValueError, TypeError):
        return "RWF 0"

@register.filter
def currency_no_symbol(value, decimal_places=2):
    """
    Format a number with thousands separators and specified decimal places, without currency symbol.
    Usage: {{ value|currency_no_symbol }} or {{ value|currency_no_symbol:0 }}
    """
    if value is None:
        return "0"
    
    try:
        # Convert to float and format with thousands separators
        float_value = float(value)
        
        # Format with thousands separators
        formatted = intcomma(floatformat(float_value, decimal_places))
        
        return formatted
    except (ValueError, TypeError):
        return "0"

@register.filter
def thousands_separator(value, decimal_places=0):
    """
    Add thousands separators to a number with optional decimal places.
    Usage: {{ value|thousands_separator }} or {{ value|thousands_separator:2 }}
    """
    if value is None:
        return "0"
    
    try:
        # Convert to float and format with thousands separators
        float_value = float(value)
        
        # Format with thousands separators
        formatted = intcomma(floatformat(float_value, decimal_places))
        
        return formatted
    except (ValueError, TypeError):
        return "0" 