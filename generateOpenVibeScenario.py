import xml.etree.cElementTree as et
from xml.dom import minidom
import os
from shutil import copyfile
import bcipipeline_settings as settings


def prettify(elem):
    """Return a pretty-printed XML string for the Element.
    """
    rough_string = et.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")


def generateScenarios(scenarioName, parameterList):

    print("-- ", scenarioName, " // with parameters : ")
    for i in range(len(parameterList)):
        print(parameterList[i])

    sep = "/"
    # Windows
    if os.name == 'nt':
        sep = "\\"

    cwd = os.getcwd()
    print('-- Working in', cwd)

    # Get scenarii templates depending on the user's choice
    # Copy them to cwd/generated-scenarii
    templatesDir = cwd
    generatedDir = cwd + sep + "generated" + sep

    if scenarioName == settings.options[1]:
        templatesDir += sep + settings.optionsTemplatesDir[1] + sep
    elif scenarioName == settings.options[2]:
        templatesDir += sep + settings.optionsTemplatesDir[2] + sep

    if not os.path.exists(generatedDir):
        os.mkdir(generatedDir)

    for file in settings.templateScenFilenames:
        src = templatesDir + file
        dest = generatedDir + file
        copyfile(src, dest)
        print('---- Copied ', src, ' to ', dest, ' ... ')

    # Modify the scenarii depending on the user's options
    # ...
    # ...
    # ...

    root = et.Element("OpenViBE-Scenario")
    boxes = et.SubElement(root, "Boxes")

    prettyXml = prettify(root)
    f = open("scenario.xml", 'w')
    f.write(prettyXml)
    f.close()

    # box1 = et.SubElement(boxes, "Box")
    # et.SubElement(box1, "Identifier").text = "(0x244d9869, 0x1fade44a)"
    # et.SubElement(box1, "Name").text = "Sinus"
    # et.SubElement(box1, "AlgorithmClassIdentifier").text = "(0x0055be5f, 0x087bdd12)"
    # inputs1 = et.SubElement(box1, "Inputs")
    # inputs1_1 = et.SubElement(inputs1, "Input")
    # et.SubElement(inputs1_1, "TypeIdentifier").text = "(0x544a003e, 0x6dcba5f6)"
    # et.SubElement(inputs1_1, "Name").text = "Signal"
    # input1_2 = et.SubElement(inputs1, "Input")
    # et.SubElement(input1_2, "TypeIdentifier").text = "(0x6f752dd0, 0x082a321e)"
    # et.SubElement(input1_2, "Name").text = "Stimulations"
    #
    # settings1 = et.SubElement(box1, "Settings")
    # setting1_1 = et.SubElement(settings1, "Setting")
    # et.SubElement(setting1_1, "TypeIdentifier").text = "(0x512a166f, 0x5c3ef83f)"
    # et.SubElement(setting1_1, "Name").text = "TimeScale"
    # et.SubElement(setting1_1, "DefaultValue").text = "10"
    # et.SubElement(setting1_1, "Value").text = "10"
    #
    # setting1_2 = et.SubElement(settings1, "Setting")
    # et.SubElement(setting1_2, "TypeIdentifier").text = "(0x5de046a6, 0x086340aa)"
    # et.SubElement(setting1_2, "Name").text = "Display Mode"
    # et.SubElement(setting1_2, "DefaultValue").text = "Scan"
    # et.SubElement(setting1_2, "Value").text = "Scan"
    #
    # setting1_3 = et.SubElement(settings1, "Setting")
    # et.SubElement(setting1_3, "TypeIdentifier").text = "(0x2cdb2f0b, 0x12f231ea)"
    # et.SubElement(setting1_3, "Name").text = "Manual Vertical Scale"
    # et.SubElement(setting1_3, "DefaultValue").text = "false"
    # et.SubElement(setting1_3, "Value").text = "false"
    #
    # setting1_4 = et.SubElement(settings1, "Setting")
    # et.SubElement(setting1_4, "TypeIdentifier").text = "(0x512a166f, 0x5c3ef83f)"
    # et.SubElement(setting1_4, "Name").text = "Vertical Scale"
    # et.SubElement(setting1_4, "DefaultValue").text = "100"
    # et.SubElement(setting1_4, "Value").text = "100"
    #
    # attributes1 = et.SubElement(box1, "Attributes")
    # attribute1_1 = et.SubElement(attributes1, "Attribute")
    # et.SubElement(attribute1_1, "Identifier").text = "(0x1fa7a38f, 0x54edbe0b)"
    # et.SubElement(attribute1_1, "Value").text = "448"
    #
    # attribute1_2 = et.SubElement(attributes1, "Attribute")
    # et.SubElement(attribute1_2, "Identifier").text = "(0x1fa963f5, 0x1a638cd4)"
    # et.SubElement(attribute1_2, "Value").text = "42"
    #
    # attribute1_3 = et.SubElement(attributes1, "Attribute")
    # et.SubElement(attribute1_3, "Identifier").text = "(0x207c9054, 0x3c841b63)"
    # et.SubElement(attribute1_3, "Value").text = "240"
    #
    # attribute1_4 = et.SubElement(attributes1, "Attribute")
    # et.SubElement(attribute1_4, "Identifier").text = "(0x4e7b798a, 0x183beafb)"
    # et.SubElement(attribute1_4, "Value").text = "(0xb5fb4d3d, 0x1d7080db)"
    #
    # attribute1_5 = et.SubElement(attributes1, "Attribute")
    # et.SubElement(attribute1_5, "Identifier").text = "(0xad100179, 0xa3c984ab)"
    # et.SubElement(attribute1_5, "Value").text = "84"
    #
    # attribute1_6 = et.SubElement(attributes1, "Attribute")
    # et.SubElement(attribute1_6, "Identifier").text = "(0xce18836a, 0x9c0eb403)"
    # et.SubElement(attribute1_6, "Value").text = "4"
    #
    # attribute1_7 = et.SubElement(attributes1, "Attribute")
    # et.SubElement(attribute1_7, "Identifier").text = "(0xcfad85b0, 0x7c6d841c)"
    # et.SubElement(attribute1_7, "Value").text = "2"


