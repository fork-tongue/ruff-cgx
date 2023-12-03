from collagraph.cgx import cgx


# The following definitions are needed to monkey-patch the CGXParser
# When https://github.com/fork-tongue/collagraph/pull/115 is merged (and released)
# this monkey-patch can be removed
class TextElement:
    def __init__(self, content, location=None):
        self.content = content


class Comment:
    def __init__(self, content, location=None):
        self.content = content


def handle_data(self, data):
    if data.strip():
        # Add item as child to the last on the stack
        self.stack[-1].children.append(
            TextElement(content=data, location=self.getpos())
        )


def handle_comment(self, comment):
    if comment.strip():
        # Add item as child to the last on the stack
        self.stack[-1].children.append(Comment(content=comment, location=self.getpos()))


# Monkey-patch the CGXParser to also handle comments
cgx.CGXParser.handle_comment = handle_comment
cgx.CGXParser.handle_data = handle_data


INDENT = "  "
SORTING = [
    # DEFINITION
    {"v-is"},
    # LIST_RENDERING
    {"v-for"},
    # CONDITIONALS
    {"v-if", "v-else-if", "v-else"},
    # UNIQUE
    {"id", "ref", "key"},
    # SLOT
    {"v-slot", "#"},
    # "v-model",
    # OTHER_ATTR
    {"v-bind", ":"},
    # EVENTS
    {"v-on", "@"},
]
OTHER_ATTR = SORTING.index({"v-bind", ":"})
UNIQUE_ATTR = SORTING.index({"id", "ref", "key"})


def format_template(template_node, lines, parser):
    # Find beginning and end of script block
    start, end = template_node.location[0] - 1, template_node.end[0]

    result = format_node(template_node, depth=0, parser=parser)
    # Replace all tabs with the default indent and add line breaks
    tab = "\t"
    result = [f"{line.replace(tab, INDENT)}\n" for line in result]
    return result, (start, end)


def sort_attr(attr):
    """
    This rule aims to enforce ordering of component attributes. The default order is
    specified in the Vue.js Style Guide and is:

    * DEFINITION e.g. 'is', 'v-is'
    * LIST_RENDERING e.g. 'v-for item in items'
    * CONDITIONALS e.g. 'v-if', 'v-else-if', 'v-else', 'v-show', 'v-cloak'
    * RENDER_MODIFIERS e.g. 'v-once', 'v-pre'
    * GLOBAL e.g. 'id'
    * UNIQUE e.g. 'ref', 'key'
    * SLOT e.g. 'v-slot', 'slot'.
    * TWO_WAY_BINDING e.g. 'v-model'
    * OTHER_DIRECTIVES e.g. 'v-custom-directive'
    * OTHER_ATTR alias for [ATTR_DYNAMIC, ATTR_STATIC, ATTR_SHORTHAND_BOOL]:
        * ATTR_DYNAMIC e.g. 'v-bind:prop="foo"', ':prop="foo"'
        * ATTR_STATIC e.g. 'prop="foo"', 'custom-prop="foo"'
        * ATTR_SHORTHAND_BOOL e.g. 'boolean-prop'
    * EVENTS e.g. '@click="functionCall"', 'v-on="event"'
    * CONTENT e.g. 'v-text', 'v-html'
    """

    for idx, prefixes in enumerate(SORTING):
        for prefix in prefixes:
            if idx != UNIQUE_ATTR:
                if attr.startswith(prefix):
                    return f"{idx}{attr.lstrip(prefix)}"
            else:
                if attr == prefix:
                    return f"{idx}{attr}"
    else:
        if not attr.startswith(("v-")):
            return f"{OTHER_ATTR}{attr}"

    return f"{len(SORTING)}{attr}"


def format_attribute(key, value):
    if not key.startswith((":", "@")):
        if value is True:
            return key
    return f'{key}="{value}"'


def format_node(node, depth, parser):
    result = []
    indent = depth * INDENT

    if not isinstance(node, (TextElement, Comment)):
        start = f"{indent}<{node.tag}"
        if node.attrs:
            if len(node.attrs) == 1:
                key, val = list(node.attrs.items())[0]
                attr = format_attribute(key, val)
                start = f"{start} {attr}"
            else:
                attrs = []
                for key in sorted(node.attrs, key=sort_attr):
                    attr = format_attribute(key, node.attrs[key])
                    attrs.append(f"{indent}{INDENT}{attr}")

                start = "\n".join([start] + attrs)

        if not node.children:
            if not node.attrs or len(node.attrs) <= 1:
                start = f"{start} />"
            else:
                start = f"{start}\n{depth * INDENT}/>"
        else:
            if not node.attrs or len(node.attrs) <= 1:
                start = f"{start}>"
            else:
                start = f"{start}\n{depth * INDENT}>"

        result.append(start)
    elif isinstance(node, Comment):
        result.append(f"{indent}<!--{node.content}-->")
    elif isinstance(node, TextElement):
        result.append(f"{indent}{node.content.strip()}")

    if hasattr(node, "children"):
        for child in node.children:
            result.extend(format_node(child, depth + 1, parser))

        if node.children:
            result.append(f"{indent}</{node.tag}>")

    return result
