from django import template

register = template.Library()

@register.filter(name='absolute')
def absolute(value):
    """Return the absolute value of the given number."""
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return value

@register.filter(name='mul')
def mul(value, arg):
    """Multiply the value by the argument."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter(name='div')
def div(value, arg):
    """Divide the value by the argument."""
    try:
        if float(arg) == 0:
            return 0
        return float(value) / float(arg)
    except (ValueError, TypeError):
        return 0
