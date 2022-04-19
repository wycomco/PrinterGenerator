#!/usr/local/munki/munki-python
from __future__ import absolute_import, print_function

import argparse
import csv
import os
import re
import sys
from typing import Optional

from xml.parsers.expat import ExpatError

from plistlib import load as load_plist  # Python 3
from plistlib import dump as dump_plist


# Preference handling copied from Munki:
# https://github.com/munki/munki/blob/e8ccc5f53e8f69b59fbc153a783158a34ca6d1ea/code/client/munkilib/cliutils.py#L55

BUNDLE_ID = 'com.googlecode.munki.munkiimport'
PREFSNAME = BUNDLE_ID + '.plist'
PREFSPATH = os.path.expanduser(os.path.join('~/Library/Preferences', PREFSNAME))

FOUNDATION_SUPPORT = True
try:
    # PyLint cannot properly find names inside Cocoa libraries, so issues bogus
    # No name 'Foo' in module 'Bar' warnings. Disable them.
    # pylint: disable=E0611
    from Foundation import CFPreferencesCopyAppValue
    # pylint: enable=E0611
except ImportError:
    # CoreFoundation/Foundation isn't available
    FOUNDATION_SUPPORT = False

if FOUNDATION_SUPPORT:
    def pref(prefname, default=None):
        """Return a preference. Since this uses CFPreferencesCopyAppValue,
        Preferences can be defined in several places. Precedence is:
            - MCX/Configuration Profile
            - ~/Library/Preferences/ByHost/
                com.googlecode.munki.munkiimport.XX.plist
            - ~/Library/Preferences/com.googlecode.munki.munkiimport.plist
            - /Library/Preferences/com.googlecode.munki.munkiimport.plist
        """
        value = CFPreferencesCopyAppValue(prefname, BUNDLE_ID)
        if value is None:
            return default

        return value

else:
    def pref(prefname, default=None):
        """Returns a preference for prefname. This is a fallback mechanism if
        CoreFoundation functions are not available -- for example to allow the
        possible use of makecatalogs or manifestutil on Linux"""
        if not hasattr(pref, 'cache'):
            pref.cache = None
        if not pref.cache:
            try:
                f = open(os.path.join(pwd, PREFSPATH), 'rb')
                pref.cache = load_plist(f)
                f.close()
            except (IOError, OSError, ExpatError):
                pref.cache = {}
        if prefname in pref.cache:
            return pref.cache[prefname]
        # no pref found
        return default

def getOptionsString(optionList):
    # optionList should be a list item
    optionsString = ''
    for option in optionList:
        if option == optionList[-1]:
            optionsString += "\"%s\":\"%s\"" % (str(option.split('=')[0]), str(option.split('=')[1]))
        else:
            optionsString += "\"%s\":\"%s\"" % (str(option.split('=')[0]), str(option.split('=')[1])) + ', '
    return optionsString

parser = argparse.ArgumentParser(description='Generate a Munki nopkg-style pkginfo for printer installation.')
parser.add_argument('--printername', help='Name of printer queue. May not contain spaces, tabs, # or /. Required.')
parser.add_argument('--driver', help='Either the name of driver file in /Library/Printers/PPDs/Contents/Resources/ (relative or full path) or \'airprint-ppd\' for AirPrint printers. Required.')
parser.add_argument('--address', help='IP or DNS address of printer. If no protocol is specified, defaults to lpd://. Required.')
parser.add_argument('--location', help='Location name for printer. Optional. Defaults to printername.')
parser.add_argument('--displayname', help='Display name for printer (and Munki pkginfo). Optional. Defaults to printername.')
parser.add_argument('--desc', help='Description for Munki pkginfo only. Optional.')
parser.add_argument('--category', help='Category for Munki pgkinfo only. Optional. Defaults to \'Printers\'.')
parser.add_argument('--requires', help='Required packages in form of space-delimited \'CanonDriver1 CanonDriver2\'. Be sure to add a reference to airprint-ppd to setup your printer via AirPrint. Optional.')
parser.add_argument('--options', nargs='*', dest='options', help='Printer options in form of space-delimited \'Option1=Key Option2=Key Option3=Key\', etc. Optional.')
parser.add_argument('--version', help='Version number of Munki pkginfo. Optional. Defaults to 1.0.', default='1.0')
parser.add_argument('--icon', help='Specifies an existing icon in the Munki repo to display for the printer in Managed Software Center. Optional.')
parser.add_argument('--catalogs', help='Space delimited list of Munki catalogs. Defaults to \'testing\'. Optional.')
parser.add_argument('--munkiname', help='Name of Munki item. Defaults to printername. Optional.')
parser.add_argument('--subdirectory', help='Subdirectory of Munki\'s pkgsinfo directory. Optional.')
parser.add_argument('--repo', help='Path to Munki repo. If specified, we will try to write directly to its containing pkgsinfo directory. If not defined, we will write to current working directory. Optional.')
parser.add_argument('--csv', help='Path to CSV file containing printer info. If CSV is provided, all other options besides \'--repo\' are ignored.')
args = parser.parse_args()

def throwError(message='Unknown error',exitcode=1,show_usage=True):
    print(os.path.basename(sys.argv[0]) + ': Error: ' + message, file=sys.stderr)

    if show_usage:
        parser.print_usage()

    sys.exit(exitcode)

pkgsinfoPath = ''

if args.repo:
    args.repo = os.path.realpath(os.path.expanduser(args.repo))
    pkgsinfoPath = os.path.realpath(args.repo + '/pkgsinfo')
    if not os.access(pkgsinfoPath, os.W_OK):
        throwError('The pkgsinfo directory in given munki repo is not writable.')

pwd = os.path.dirname(os.path.realpath(__file__))
f = open(os.path.join(pwd, 'AddPrinter-Template.plist'), 'rb')
templatePlist = load_plist(f)
f.close()

# Identify the delimiter of a given CSV file, props to https://stackoverflow.com/questions/69817054/python-detection-of-delimiter-separator-in-a-csv-file
def find_delimiter(filename):
    sniffer = csv.Sniffer()
    with open(filename) as fp:
        delimiter = sniffer.sniff(fp.read(5000)).delimiter
    return delimiter

def createPlist(
    printer_name: str,
    address: str,
    driver: str,
    display_name: Optional[str] = '',
    location: Optional[str] = '',
    description: Optional[str] = '',
    category: Optional[str] = 'Printers',
    options: Optional[str] = '',
    version: Optional[str] = '1.0',
    requires: Optional[str] = '',
    icon: Optional[str] = '',
    catalogs: Optional[str] = 'testing',
    subdirectory: Optional[str] = '',
    munki_name: Optional[str] = ''
):
    newPlist = dict(templatePlist)

    # Options in the form of "Option=Value Option2=Value Option3=Value"
    # Requires in the form of "package1 package2" Note: the space seperator
    theOptionString = ''
    if options:
        theOptionString = getOptionsString(options.split(" "))

    # First, change the plist keys in the pkginfo itself
    newPlist['display_name'] = display_name
    newPlist['description'] = description
    newPlist['category'] = category

    if munki_name:
        newPlist['name'] = munki_name
    else:
        newPlist['name'] = "AddPrinter_" + str(printer_name) # set to printer name

    # Set Icon
    if icon:
        newPlist['icon_name'] = icon

    # Check for a version number
    newPlist['version'] = version

    # Check for a protocol listed in the address
    if '://' in address:
        # Assume the user passed in a full address and protocol
        address = address
    else:
        # Assume the user wants to use the default, lpd://
        address = 'lpd://' + address

    if driver == 'airprint-ppd':
        # This printer should use airprint-ppd so retrieve a PPD on the fly
        newPlist['preinstall_script'] = newPlist['preinstall_script'].replace("PRINTERNAME", printer_name)
        newPlist['preinstall_script'] = newPlist['preinstall_script'].replace("ADDRESS", address)
        driver = '/Library/Printers/PPDs/Contents/Resources/%s.ppd' % printer_name
    else:
        newPlist.pop('preinstall_script', None)

    if driver.startswith('/Library'):
        # Assume the user passed in a full path rather than a relative filename
        driver_path = driver
    else:
        # Assume only a relative filename
        driver_path = '/Library/Printers/PPDs/Contents/Resources/%s' % driver

    # Now change the variables in the installcheck_script
    newPlist['installcheck_script'] = newPlist['installcheck_script'].replace("PRINTERNAME", printer_name)
    newPlist['installcheck_script'] = newPlist['installcheck_script'].replace("OPTIONS", theOptionString)
    newPlist['installcheck_script'] = newPlist['installcheck_script'].replace("LOCATION", location.replace('"', ''))
    newPlist['installcheck_script'] = newPlist['installcheck_script'].replace("DISPLAY_NAME", display_name.replace('"', ''))
    newPlist['installcheck_script'] = newPlist['installcheck_script'].replace("ADDRESS", address)
    newPlist['installcheck_script'] = newPlist['installcheck_script'].replace("DRIVER", driver_path)

    # Now change the variables in the postinstall_script
    newPlist['postinstall_script'] = newPlist['postinstall_script'].replace("PRINTERNAME", printer_name)
    newPlist['postinstall_script'] = newPlist['postinstall_script'].replace("OPTIONS", theOptionString)
    newPlist['postinstall_script'] = newPlist['postinstall_script'].replace("LOCATION", location.replace('"', ''))
    newPlist['postinstall_script'] = newPlist['postinstall_script'].replace("DISPLAY_NAME", display_name.replace('"', ''))
    newPlist['postinstall_script'] = newPlist['postinstall_script'].replace("ADDRESS", address)
    newPlist['postinstall_script'] = newPlist['postinstall_script'].replace("DRIVER", driver_path)

    # Now change the one variable in the uninstall_script
    newPlist['uninstall_script'] = newPlist['uninstall_script'].replace("PRINTERNAME", printer_name)

    # Add required packages if passed in the csv
    if requires:
        newPlist['requires'] = requires.split(' ')

    # Define catalogs for this package
    if catalogs:
        newPlist['catalogs'] = catalogs.split(' ')

    # Write out the file
    newFileName = newPlist['name'] + "-" + newPlist['version'] + pref('pkginfo_extension', default='.pkginfo')

    if pkgsinfoPath:
        if subdirectory:
            os.makedirs(pkgsinfoPath + os.path.sep + subdirectory, exist_ok=True)
            newFileName = os.path.realpath(pkgsinfoPath + os.path.sep + subdirectory + os.path.sep + newFileName)
        else:
            newFileName = os.path.realpath(pkgsinfoPath + os.path.sep + newFileName)

    print('Writing pkginfo file to %s' % newFileName)

    f = open(newFileName, 'wb')
    dump_plist(newPlist, f)
    f.close()
    return True

if args.csv:
    # A CSV was found, use that for all data.
    with open(args.csv, mode='r') as infile:
        reader = csv.DictReader(infile, delimiter=find_delimiter(args.csv))

        for row in reader:
            # In earlier versions, each row contains up to 10 elements:
            # Printer Name, Location, Display Name, Address, Driver, Description, Options, Version, Requires, Icon
            # To preserve backward compatibility, define all possible elements with default values and check for
            # required values
            if 'Printer Name' not in row:
                throwError('Printer Name is required')
            if 'Location' not in row:
                row['Location'] = ''
            if 'Display Name' not in row:
                row['Display Name'] = row['Printer Name']
            if 'Address' not in row:
                throwError('Address is required')
            if 'Driver' not in row:
                throwError('Driver is required')
            if 'Description' not in row:
                row['Description'] = ''
            if 'Category' not in row:
                row['Category'] = 'Printers'
            if 'Options' not in row:
                row['Options'] = ''
            if 'Version' not in row:
                row['Version'] = '1.0'
            if 'Requires' not in row:
                row['Requires'] = ''
            if 'Icon' not in row:
                row['Icon'] = ''
            if 'Catalogs' not in row:
                row['Catalogs'] = pref('default_catalog', default='testing')
            if 'Subdirectory' not in row:
                row['Subdirectory'] = ''
            if 'Munki Name' not in row:
                row['Munki Name'] = ''

            createPlist(
                printer_name=row['Printer Name'],
                address=row['Address'],
                driver=row['Driver'],
                display_name=row['Display Name'],
                location=row['Location'],
                description=row['Description'],
                options=row['Options'],
                version=row['Version'],
                requires=row['Requires'],
                icon=row['Icon'],
                catalogs=row['Catalogs'],
                category=row['Category'],
                subdirectory=row['Subdirectory'],
                munki_name=row['Munki Name'])

else:
    if not args.printername:
        throwError('Argument --printername is required')
    else:
        printer_name = args.printername

    if re.search(r"[\s#/]", printer_name):
        # printernames can't contain spaces, tabs, # or /.  See lpadmin manpage for details.
        throwError("Printernames can't contain spaces, tabs, # or /.", show_usage=False)

    if not args.driver:
        throwError('Argument --driver is required')
    else:
        driver = args.driver

    if not args.address:
        throwError('Argument --address is required')
    else:
        address = args.address

    if args.desc:
        description = args.desc
    else:
        description = ""

    if args.category:
        description = args.category
    else:
        category = "Printers"

    if args.displayname:
        display_name = args.displayname
    else:
        display_name = str(args.printername)

    if args.location:
        location = args.location
    else:
        location = args.printername

    if args.version:
        version = str(args.version)
    else:
        version = "1.0"

    if args.requires:
        requires = args.requires
    else:
        requires = ""

    if args.icon:
        icon = args.icon
    else:
        icon = ""

    if args.options:
        options = args.options
    else:
        options = ''

    if args.catalogs:
        catalogs = args.catalogs
    else:
        catalogs = ""

    if args.munkiname:
        munki_name = args.munkiname
    else:
        munki_name = ""

    if args.subdirectory:
        subdirectory = args.subdirectory
    else:
        subdirectory = ""

    createPlist(
        printer_name=printer_name,
        address=address,
        driver=driver,
        display_name=display_name,
        location=location,
        description=description,
        category=category,
        options=options,
        version=version,
        requires=requires,
        icon=icon,
        catalogs=catalogs,
        subdirectory=subdirectory,
        munki_name=munki_name)

exit(0)
