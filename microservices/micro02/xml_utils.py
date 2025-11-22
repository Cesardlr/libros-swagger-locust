from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

def books_to_xml(rows):
    """Convert database rows to XML format."""
    root = Element("libros")
    
    for row in rows:
        libro = SubElement(root, "libro")
        
        # Add all fields from the row
        for key, value in row.items():
            if value is not None:
                field = SubElement(libro, key)
                field.text = str(value)
    
    # Pretty print the XML
    rough_string = tostring(root, encoding='unicode')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def create_error_xml(message):
    """Create an error XML response."""
    root = Element("error")
    root.text = message
    rough_string = tostring(root, encoding='unicode')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def create_success_xml(message):
    """Create a success XML response."""
    root = Element("success")
    root.text = message
    rough_string = tostring(root, encoding='unicode')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")


