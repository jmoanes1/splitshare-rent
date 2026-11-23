"""ShareSplit Rent template helpers: inline SVG icons, peso formatting, email subject block."""

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


ICONS = {
    'home': '<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/><path d="M9 21v-6h6v6"/>',
    'search': '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
    'pin': '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/>',
    'bed': '<path d="M2 9V5"/><path d="M2 13h20v6"/><path d="M2 17v2"/><path d="M22 17v2"/><path d="M2 13V9a2 2 0 0 1 2-2h6v6"/><path d="M10 9h8a4 4 0 0 1 4 4"/>',
    'ruler': '<path d="M3 17 17 3l4 4L7 21l-4-4Z"/><path d="m8 12 2 2"/><path d="m11 9 2 2"/><path d="m14 6 2 2"/>',
    'users': '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/><path d="M16 4.6a3.5 3.5 0 0 1 0 6.8"/><path d="M17.5 14.4a6.5 6.5 0 0 1 4 5.6"/>',
    'user': '<circle cx="12" cy="8" r="4"/><path d="M4.5 21a7.5 7.5 0 0 1 15 0"/>',
    'bath': '<path d="M4 12h16v3a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4v-3Z"/><path d="M6 12V5a2 2 0 0 1 4 0"/><path d="M7 19l-1 2"/><path d="M17 19l1 2"/>',
    'wifi': '<path d="M2.5 9a15 15 0 0 1 19 0"/><path d="M5.5 12.5a10.5 10.5 0 0 1 13 0"/><path d="M8.5 16a6 6 0 0 1 7 0"/><circle cx="12" cy="19" r="1" fill="currentColor" stroke="none"/>',
    'check': '<path d="m4.5 12.5 5 5 10-11"/>',
    'check-circle': '<circle cx="12" cy="12" r="9"/><path d="m8 12.5 2.8 2.8L16.5 9"/>',
    'shield': '<path d="M12 2.5 20 6v6c0 5-3.5 8.5-8 9.5C7.5 20.5 4 17 4 12V6l8-3.5Z"/><path d="m8.8 12 2.3 2.3 4.2-4.6"/>',
    'heart': '<path d="M12 20.5s-8-4.7-8-10.4A4.6 4.6 0 0 1 12 6.7a4.6 4.6 0 0 1 8 3.4c0 5.7-8 10.4-8 10.4Z"/>',
    'star': '<path d="m12 3 2.7 5.6 6.1.8-4.5 4.3 1.1 6.1L12 17l-5.4 2.8 1.1-6.1L3.2 9.4l6.1-.8L12 3Z"/>',
    'key': '<circle cx="8" cy="15" r="4.5"/><path d="m11.2 11.8 8.3-8.3"/><path d="m17 6 2.5 2.5"/><path d="m14 9 2 2"/>',
    'calendar': '<rect x="3" y="5" width="18" height="16" rx="2.5"/><path d="M3 10h18"/><path d="M8 3v4"/><path d="M16 3v4"/>',
    'x': '<path d="M6 6l12 12"/><path d="M18 6 6 18"/>',
    'menu': '<path d="M4 7h16"/><path d="M4 12h16"/><path d="M4 17h16"/>',
    'chevron-down': '<path d="m6 9 6 6 6-6"/>',
    'chevron-left': '<path d="m14 6-6 6 6 6"/>',
    'chevron-right': '<path d="m10 6 6 6-6 6"/>',
    'eye': '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z"/><circle cx="12" cy="12" r="3"/>',
    'eye-off': '<path d="M4 4l16 16"/><path d="M9.9 5.9A9.4 9.4 0 0 1 12 5.5c6 0 9.5 6.5 9.5 6.5a17 17 0 0 1-3.3 4"/><path d="M6.1 8.3A16.6 16.6 0 0 0 2.5 12S6 18.5 12 18.5a9.3 9.3 0 0 0 3.9-.9"/><path d="M9.9 9.9a3 3 0 0 0 4.2 4.2"/>',
    'logout': '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5"/><path d="M21 12H9"/>',
    'settings': '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.9.3h.1a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5h.1a1.7 1.7 0 0 0 1.9-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.9v.1a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z"/>',
    'doc': '<path d="M14 2.5H6a2 2 0 0 0-2 2v15a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8.5l-6-6Z"/><path d="M14 2.5v6h6"/><path d="M9 13h6"/><path d="M9 17h6"/>',
    'mail': '<rect x="2.5" y="5" width="19" height="14" rx="2.5"/><path d="m3.5 7 8.5 6 8.5-6"/>',
    'lock': '<rect x="4.5" y="10.5" width="15" height="10" rx="2.5"/><path d="M8 10.5V7.5a4 4 0 0 1 8 0v3"/>',
    'phone': '<path d="M21 16.9v2.6a2 2 0 0 1-2.2 2 19.6 19.6 0 0 1-8.5-3 19.3 19.3 0 0 1-6-6 19.6 19.6 0 0 1-3-8.6A2 2 0 0 1 3.3 2H6a2 2 0 0 1 2 1.7c.1 1 .4 2 .7 2.9a2 2 0 0 1-.5 2.1L7.1 9.9a16 16 0 0 0 6 6l1.2-1.2a2 2 0 0 1 2.1-.4c.9.3 1.9.5 2.9.7a2 2 0 0 1 1.7 2Z"/>',
    'arrow-right': '<path d="M4 12h16"/><path d="m14 6 6 6-6 6"/>',
    'briefcase': '<rect x="2.5" y="7" width="19" height="13" rx="2.5"/><path d="M8.5 7V5a2 2 0 0 1 2-2h3a2 2 0 0 1 2 2v2"/><path d="M2.5 12.5h19"/>',
    'building': '<rect x="4.5" y="2.5" width="15" height="19" rx="1.5"/><path d="M9 7h2"/><path d="M13 7h2"/><path d="M9 11h2"/><path d="M13 11h2"/><path d="M9 15h2"/><path d="M13 15h2"/><path d="M10 21.5v-3h4v3"/>',
    'sparkles': '<path d="m12 3 1.9 4.6L18.5 9.5l-4.6 1.9L12 16l-1.9-4.6L5.5 9.5l4.6-1.9L12 3Z"/><path d="m19 15 .9 2.1L22 18l-2.1.9L19 21l-.9-2.1L16 18l2.1-.9L19 15Z"/>',
    'alert': '<path d="M12 3 2.5 20h19L12 3Z"/><path d="M12 10v4"/><circle cx="12" cy="17" r="0.6" fill="currentColor" stroke="none"/>',
    'info': '<circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><circle cx="12" cy="8" r="0.6" fill="currentColor" stroke="none"/>',
    'grid': '<rect x="3.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="3.5" y="13.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="13.5" width="7" height="7" rx="1.5"/>',
    'bookmark': '<path d="M6 3.5h12a1 1 0 0 1 1 1V21l-7-4-7 4V4.5a1 1 0 0 1 1-1Z"/>',
    'filter': '<path d="M3 5h18l-7 8v6l-4 2v-8L3 5Z"/>',
    'clock': '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>',
    'edit': '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5Z"/>',
    'plus': '<path d="M12 5v14"/><path d="M5 12h14"/>',
    'trash': '<path d="M3.5 6h17"/><path d="M8 6V4a1.5 1.5 0 0 1 1.5-1.5h5A1.5 1.5 0 0 1 16 4v2"/><path d="M5.5 6l1 14a2 2 0 0 0 2 1.9h7a2 2 0 0 0 2-1.9l1-14"/>',
    'car': '<path d="M4 16v-4l2-5h12l2 5v4"/><path d="M4 16h16"/><circle cx="7.5" cy="17.5" r="1.8"/><circle cx="16.5" cy="17.5" r="1.8"/><path d="M6 12h12"/>',
    'wind': '<path d="M3 8h11a3 3 0 1 0-3-3"/><path d="M3 12h15a3 3 0 1 1-3 3"/><path d="M3 16h7a2.5 2.5 0 1 1-2.5 2.5"/>',
    'laptop': '<rect x="4.5" y="4.5" width="15" height="10.5" rx="1.5"/><path d="M2 19.5h20"/>',
    'sofa': '<path d="M5 11V8a3 3 0 0 1 3-3h8a3 3 0 0 1 3 3v3"/><path d="M3 13a2 2 0 0 1 4 0v2h10v-2a2 2 0 0 1 4 0v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4Z"/>',
    'peso': '<path d="M7 21V4h6a5 5 0 0 1 0 10H7"/><path d="M4 8.5h13"/><path d="M4 12h13"/>',
    'chart': '<path d="M4 20V4"/><path d="M4 20h16"/><path d="M8 16v-5"/><path d="M12 16V8"/><path d="M16 16v-3"/>',
    'sun': '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2"/><path d="M12 19.5v2"/><path d="m4.9 4.9 1.4 1.4"/><path d="m17.7 17.7 1.4 1.4"/><path d="M2.5 12h2"/><path d="M19.5 12h2"/><path d="m4.9 19.1 1.4-1.4"/><path d="m17.7 6.3 1.4-1.4"/>',
    'handshake': '<path d="m11 17 2 2a1.4 1.4 0 0 0 2-2"/><path d="m13 15 2.5 2.5a1.4 1.4 0 0 0 2-2L14 12"/><path d="M3 11 8 6l4 1 4-1 5 5"/><path d="M3 11v5l3 3"/><path d="M21 11v5l-3 3"/><path d="m8 12-2.5 2.5a1.4 1.4 0 0 0 2 2L10 14"/>',
}


@register.simple_tag
def icon(name, css=''):
    paths = ICONS.get(name, ICONS['info'])
    classes = ('icon ' + css).strip()
    return mark_safe(
        f'<svg class="{classes}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{paths}</svg>'
    )


@register.filter
def peso(value):
    """Format a number as Philippine pesos: 8500.00 -> ₱8,500."""
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return value
    if amount == int(amount):
        return f'₱{int(amount):,}'
    return f'₱{amount:,.2f}'


@register.filter
def split_amenities(value):
    """Split a comma-separated amenity string into a clean list."""
    if not value:
        return []
    return [part.strip() for part in str(value).split(',') if part.strip()]


@register.simple_tag(takes_context=True)
def query_replace(context, **kwargs):
    """Return the current querystring with keys replaced (None removes a key)."""
    request = context.get('request')
    params = request.GET.copy() if request else {}
    for key, value in kwargs.items():
        if value is None or value == '':
            params.pop(key, None)
        else:
            params[key] = value
    if 'page' not in kwargs:
        params.pop('page', None)
    encoded = params.urlencode() if hasattr(params, 'urlencode') else ''
    return '?' + encoded if encoded else '?'


class BlockSubjectNode(template.Node):
    def __init__(self, nodelist, varname):
        self.nodelist = nodelist
        self.varname = varname

    def render(self, context):
        value = self.nodelist.render(context)
        context[self.varname] = value
        return ''


@register.tag
def blocksubject(parser, token):
    """Store a block's rendered content as the ``subject`` context variable."""
    nodelist = parser.parse(('endblocksubject',))
    parser.delete_first_token()
    return BlockSubjectNode(nodelist, 'subject')