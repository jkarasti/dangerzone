#!/usr/bin/env python3
import os
import uuid
import xml.etree.ElementTree as ET


def build_data(dirname, dir_prefix, id_, name):
    data = {
        "id": id_,
        "name": name,
        "files": [],
        "dirs": [],
    }

    for basename in os.listdir(dirname):
        filename = os.path.join(dirname, basename)
        if os.path.isfile(filename):
            data["files"].append(os.path.join(dir_prefix, basename))
        elif os.path.isdir(filename):
            if id_ == "INSTALLFOLDER":
                id_prefix = "Folder"
            else:
                id_prefix = id_

            # Skip lib/PySide6/examples folder due to ilegal file names
            if "\\build\\exe.win-amd64-3.12\\lib\\PySide6\\examples" in dirname:
                continue

            # Skip lib/PySide6/qml/QtQuick folder due to ilegal file names
            # XXX Since we're not using Qml it should be no problem
            if "\\build\\exe.win-amd64-3.12\\lib\\PySide6\\qml\\QtQuick" in dirname:
                continue

            id_value = f"{id_prefix}{basename.capitalize().replace('-', '_')}"
            data["dirs"].append(
                build_data(
                    os.path.join(dirname, basename),
                    os.path.join(dir_prefix, basename),
                    id_value,
                    basename,
                )
            )

    if len(data["files"]) > 0:
        if id_ == "INSTALLFOLDER":
            data["component_id"] = "ApplicationFiles"
        else:
            data["component_id"] = "FolderComponent" + id_[len("Folder") :]
        data["component_guid"] = str(uuid.uuid4())

    return data


def build_dir_xml(root, data):
    attrs = {}
    if "id" in data:
        attrs["Id"] = data["id"]
    if "name" in data:
        attrs["Name"] = data["name"]
    el = ET.SubElement(root, "Directory", attrs)
    for subdata in data["dirs"]:
        build_dir_xml(el, subdata)

    # If this is the ProgramMenuFolder, add the menu component
    if "id" in data and data["id"] == "ProgramMenuFolder":
        component_el = ET.SubElement(
            el,
            "Component",
            Id="ApplicationShortcuts",
            Guid="539e7de8-a124-4c09-aa55-0dd516aad7bc",
        )
        ET.SubElement(
            component_el,
            "Shortcut",
            Id="ApplicationShortcut1",
            Name="Dangerzone",
            Description="Dangerzone",
            Target="[INSTALLFOLDER]dangerzone.exe",
            WorkingDirectory="INSTALLFOLDER",
        )
        ET.SubElement(
            component_el,
            "RegistryValue",
            Root="HKCU",
            Key="Software\\Freedom of the Press Foundation\\Dangerzone",
            Name="installed",
            Type="integer",
            Value="1",
            KeyPath="yes",
        )


def build_components_xml(root, data):
    component_ids = []
    if "component_id" in data:
        component_ids.append(data["component_id"])

    for subdata in data["dirs"]:
        if "component_guid" in subdata:
            dir_ref_el = ET.SubElement(root, "DirectoryRef", Id=subdata["id"])
            component_el = ET.SubElement(
                dir_ref_el,
                "Component",
                Id=subdata["component_id"],
                Guid=subdata["component_guid"],
            )
            for filename in subdata["files"]:
                file_el = ET.SubElement(
                    component_el, "File", Source=filename, Id="file_" + uuid.uuid4().hex
                )

        component_ids += build_components_xml(root, subdata)

    return component_ids


def main():
    version_filename = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "share",
        "version.txt",
    )
    with open(version_filename) as f:
        # Read the Dangerzone version from share/version.txt, and remove any potential
        # -rc markers.
        version = f.read().strip().split("-")[0]

    dist_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "build",
        "exe.win-amd64-3.12",
    )
    if not os.path.exists(dist_dir):
        print("You must build the dangerzone binary before running this")
        return

    data = {
        "id": "TARGETDIR",
        "name": "SourceDir",
        "dirs": [
            {
                "id": "ProgramFilesFolder",
                "dirs": [],
            },
            {
                "id": "ProgramMenuFolder",
                "dirs": [],
            },
        ],
    }

    data["dirs"][0]["dirs"].append(
        build_data(
            dist_dir,
            "exe.win-amd64-3.12",
            "INSTALLFOLDER",
            "Dangerzone",
        )
    )

    # Add the Wix root element
    wix_el = ET.Element("Wix", xmlns="http://wixtoolset.org/schemas/v4/wxs")

    # Add the Package element
    package_el = ET.SubElement(
        wix_el,
        "Package",
        Name="Dangerzone",
        Manufacturer="Freedom of the Press Foundation",
        UpgradeCode="$(var.ProductUpgradeCode)",
        Language="1033",
        Compressed="yes",
        Codepage="1252",
        Version=dangerzone_version,
    )
    ET.SubElement(
        package_el,
        "SummaryInformation",
        Keywords="Installer",
        Description="Dangerzone $(var.ProductVersion) Installer",
        Codepage="1252",
    )
    ET.SubElement(package_el, "Media", Id="1", Cabinet="product.cab", EmbedCab="yes")
    ET.SubElement(
        package_el, "Icon", Id="ProductIcon", SourceFile="..\\share\\dangerzone.ico"
    )
    ET.SubElement(package_el, "Property", Id="ARPPRODUCTICON", Value="ProductIcon")
    ET.SubElement(
        package_el,
        "Property",
        Id="ARPHELPLINK",
        Value="https://dangerzone.rocks",
    )
    ET.SubElement(
        package_el,
        "Property",
        Id="ARPURLINFOABOUT",
        Value="https://freedom.press",
    )
    ET.SubElement(
        package_el,
        "Property",
        Id="WIXUI_INSTALLDIR",
        Value="INSTALLFOLDER",
    )
    ET.SubElement(package_el, "UIRef", Id="WixUI_InstallDir")
    ET.SubElement(package_el, "UIRef", Id="WixUI_ErrorProgressText")
    ET.SubElement(
        package_el,
        "WixVariable",
        Id="WixUILicenseRtf",
        Value="..\\install\\windows\\license.rtf",
    )
    ET.SubElement(
        package_el,
        "WixVariable",
        Id="WixUIDialogBmp",
        Value="..\\install\\windows\\dialog.bmp",
    )
    ET.SubElement(
        package_el,
        "MajorUpgrade",
        AllowSameVersionUpgrades="yes",
        DowngradeErrorMessage="A newer version of [ProductName] is already installed. If you are sure you want to downgrade, remove the existing installation via Programs and Features.",
    )

    build_dir_xml(package_el, data)
    component_ids = build_components_xml(package_el, data)

    feature_el = ET.SubElement(package_el, "Feature", Id="DefaultFeature", Level="1")
    for component_id in component_ids:
        ET.SubElement(feature_el, "ComponentRef", Id=component_id)
    ET.SubElement(feature_el, "ComponentRef", Id="ApplicationShortcuts")

    print(f'<?define ProductVersion = "{version}"?>')
    print('<?define ProductUpgradeCode = "12b9695c-965b-4be0-bc33-21274e809576"?>')
    ET.indent(wix_el, space="    ")
    print(ET.tostring(wix_el).decode())


if __name__ == "__main__":
    main()
