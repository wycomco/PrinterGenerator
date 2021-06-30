# PrinterGenerator

This script will generate a ["nopkg"](https://groups.google.com/d/msg/munki-dev/hmfPZ7sgW6k/q6vIkPIPepoJ) style pkginfo file for [Munki](https://github.com/munki/munki/wiki) to install a printer.

See [Managing Printers with Munki](https://github.com/munki/munki/wiki/Managing-Printers-With-Munki) for more details.

This is a fork of [nmcspadden/PrinterGenerator](https://github.com/nmcspadden/PrinterGenerator), initiated by [jutonium](https://github.com/jutonium).

## Enhancements

This updated version implements some cool new things:

* Support for macOS 10.14, 10.15 and 11
* Usage of the Munki-included Python3
* Enables usage of Microsoft Excel to edit the CSV file – **this required switching the separator from comma to semicolon**, you may need to update your files accordingly
* The order of the csv columns do not have to be preserved, but **keep the names of the 1st row**.
* Sanity checks for the csv fields
* Option to define a path to Munki repo and an optional subdirectory
* Option to define a separate name for the Munki pkginfo item
* Besides switching to semicolons as csv separator: **This script should preserve backward compatibility!**

## Caveats

It might show an error on systems not using English or German on the command line but still successfully install all printers.

## Usage

The script can either take arguments on the command line, or a CSV file containing a list of printers with all the necessary information.  

The script will generate a pkginfo file.  This pkginfo file is a "nopkg" style, and thus has three separate scripts:  

* installcheck_script
* postinstall_script
* uninstall_script

The installcheck_script looks for an existing print queue named PRINTERNAME.  If it does not find one, it will exit 0 and trigger an installation request.  If it does find one, it will compare all of the options provided (DRIVER, ADDRESS, DISPLAYNAME, LOCATION, and OPTIONS) for differences.  If there are any differences, it will trigger an installation request.

The postinstall_script will attempt to delete the existing print queue named PRINTERNAME first, and then will reinstall the queue with the specified options.  
*Note that it does not check to see if the printer queue is in use at the time, so it is possible that existing print jobs will be cancelled if a user is printing when a Munki reinstall occurs.*

The uninstall_script will delete the printer queue named PRINTERNAME if uninstallation is triggered.

### Using a CSV file:

A template CSV file is provided to make it easy to generate multiple pkginfos in one run. Pass the path to the csv file with `--csv`:

```
./print_generator.py --csv /path/to/printers.csv
```
*Note: if a CSV file is provided, all other command line arguments – besides the optional `--repo` – are ignored.*

The CSV file's columns should be pretty self-explanatory:

* Printer name: Name of the print queue
* Location: The "location" of the printer as displayed in System Preferences
* Display name: The visual name that shows up in the Printers & Scanners pane of the System Preferences, and in the print dialogue boxes. Also used in the Munki pkginfo.
* Address: The IP or DNS address of the printer. If no protocol is specified, we expect `lpd://`
* Driver: Name of the driver file in /Library/Printers/PPDs/Contents/Resources/ or an absolute path to a ppd file.
* Description: Used only in the Munki pkginfo.
* Options: Any printer options that should be specified. These **must** be space-delimited key=value pairs, such as "HPOptionDuplexer=True OutputMode=normal".  **Do not use commas to separate the options.**
* Version: Used only in the Munki pkginfo, defaults to `1.0`
* Requires: Required packages for Munki pkginfo. These **must** be space-delimited, such as "CanonDriver1 CanonDriver2".
* Icon: Optionally specify an existing icon in the Munki repo to display for the printer in Managed Software Center.
* Catalogs: Space separated list of Munki catalogs in which this pkginfo should be listed
* Subdirectory: Subdirectory inside Munki's pkgsinfo directory, only used if `--repo` is defined.
* Munki Name: A specific name for this pkgsinfo item. This defaults to `AddPrinter_Printer Name`

### Command-line options:

A full description of usage is available with:

```
./print_generator.py -h
usage: print_generator.py [-h] [--printername PRINTERNAME] [--driver DRIVER] [--address ADDRESS] [--location LOCATION] [--displayname DISPLAYNAME] [--desc DESC] [--requires REQUIRES] [--options [OPTIONS ...]] [--version VERSION] [--icon ICON] [--catalogs CATALOGS] [--munkiname MUNKINAME] [--repo REPO]
                          [--subdirectory SUBDIRECTORY] [--csv CSV]

Generate a Munki nopkg-style pkginfo for printer installation.

optional arguments:
  -h, --help            show this help message and exit
  --printername PRINTERNAME
                        Name of printer queue. May not contain spaces, tabs, # or /. Required.
  --driver DRIVER       Name of driver file in /Library/Printers/PPDs/Contents/Resources/. Can be relative or full path. Required.
  --address ADDRESS     IP or DNS address of printer. If no protocol is specified, defaults to lpd://. Required.
  --location LOCATION   Location name for printer. Optional. Defaults to printername.
  --displayname DISPLAYNAME
                        Display name for printer (and Munki pkginfo). Optional. Defaults to printername.
  --desc DESC           Description for Munki pkginfo only. Optional.
  --requires REQUIRES   Required packages in form of space-delimited 'CanonDriver1 CanonDriver2'. Optional.
  --options [OPTIONS ...]
                        Printer options in form of space-delimited 'Option1=Key Option2=Key Option3=Key', etc. Optional.
  --version VERSION     Version number of Munki pkginfo. Optional. Defaults to 1.0.
  --icon ICON           Specifies an existing icon in the Munki repo to display for the printer in Managed Software Center. Optional.
  --catalogs CATALOGS   Space delimited list of Munki catalogs. Defaults to 'testing'. Optional.
  --munkiname MUNKINAME
                        Name of Munki item. Defaults to printername. Optional.
  --repo REPO           Path to Munki repo. If specified, we will try to write directly to its containing pkgsinfo directory. If not defined, we will write to current working directory. Optional.
  --subdirectory SUBDIRECTORY
                        Subdirectory of Munki's pkgsinfo directory. Optional.
  --csv CSV             Path to CSV file containing printer info. If CSV is provided, all other options besides '--repo' are ignored.
```

As in the above CSV section, the arguments are all the same:

* `--printername`: Name of the print queue. May not contain spaces, tabs, "#" or "/" characters. **Required.**
* `--driver`: Name of the driver file in /Library/Printers/PPDs/Contents/Resources/. This can be either a relative path (i.e. the filename in the path above), or a full path (starting with "/Library"). **Required.**
* `--address`: The IP or DNS address of the printer. If no protocol is specified, `lpd://ADDRESS` will be used.  **Required.**
* `--location`: The "location" of the printer. If not provided, this will default to the value of `--printername`.
* `--displayname`: The visual name that shows up in the Printers & Scanners pane of the System Preferences, and in the print dialogue boxes.  Also used in the Munki pkginfo.  If not provided, this will default to the value of `--printername`.
* `--desc`: Used only in the Munki pkginfo. If not provided, will default to an empty string ("").
* `--requires`: Add required packages in the Munki pkginfo. If not provided, no packages will be required.
* `--options`: Any number of printer options that should be specified. These should be space-delimited key=value pairs, such as "HPOptionDuplexer=True OutputMode=normal".
* `--version`: The version number of the Munki pkginfo. Defaults to "1.0".
* `--icon`: Used only in the Munki pkginfo. If not provided, will default to an empty string ("").
* `--catalogs`: Space delimited list of Munki catalogs. Defaults to 'testing'. Optional.
* `--munkiname`: Name of Munki item. Defaults to printername. Optional.
* `--repo`: Path to Munki repo. If specified, we will try to write directly to its containing pkgsinfo directory. If not defined, we will write to current working directory. Optional.
* `--subdirectory`: Subdirectory of Munki's pkgsinfo directory. Optional.

### Figuring out options

Printer options can be determined by using `lpoptions` on an existing printer queue:  
`/usr/bin/lpoptions -p YourPrinterQueueName -l`  

Here's a snip of output:

```
OutputMode/Quality: high-speed-draft fast-normal *normal best highest
HPColorMode/Color: *colorsmart colorsync grayscale
ColorModel/Color Model: *RGB RGBW
HPPaperSource/Source: *Tray1
Resolution/Resolution: *300x300dpi 600x600dpi 1200x1200dpi
```

Options typically have the actual PPD option name on the left side of the /, and a display name (which is likely to show up in the printer settings dialogue boxes) on the right of the /.  The possible values for the printer are listed after the colon.  The current option is marked with an "*".  

Despite `lpoptions` using a "Name/Nice Name: Value *Value Value" format, the option must be specified more strictly:  
"HPColorMode=grayscale"

This is the format you must use when passing options to `--options`, or specifying them in the CSV file.  

*Note that `/usr/bin/lpoptions -l` without specifying a printer will list options for the default printer.*
