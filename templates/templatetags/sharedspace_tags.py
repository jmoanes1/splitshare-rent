from django import template

register = template.Library()


class BlockSubjectNode(template.Node):
    def __init__(self, nodelist, varname):
        self.nodelist = nodelist
        self.varname = varname

    def render(self, context):
        # Render the block into a string and store it in the context under
        # the variable name so the password reset views can use it.
        value = self.nodelist.render(context)
        context[self.varname] = value
        return ''


@register.tag
def blocksubject(parser, token):
    """Defines a subject line block that can be referenced as a variable.

    Usage::

        {% blocksubject %}Reset your password{% endblocksubject %}

    The content inside the block is stored in the template context under
    the name ``subject`` (the default), which Django's password reset
    views use as their subject line.
    """
    nodelist = parser.parse(('endblocksubject',))
    parser.delete_first_token()
    varname = 'subject'
    return BlockSubjectNode(nodelist, varname)
