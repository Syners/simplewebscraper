import json
from xml.dom.minidom import parse, parseString


def ToJSON(data):
    try:
        json_object = json.loads(data)
        return json_object
    except ValueError, e:
        return data


def ToXML(data):
    """https://wiki.python.org/moin/MiniDom"""
    dom = parseString(data)
    return dom.toxml()
