a small library for converting to and from Aperture Science apf files.

usage: 

```
import apftool
apfString = apftool.encodeapf(pngObject) # turns image bytes object into apf string
pngObject = apftool.decodeapf(apfString) # turns apf string object into image bytes
```

included is a simple cli tool.

usage:

```
python apfcli.py maricom.png # creates maricom.apf
python apfcli.py maricom.apf # creates maricom.png
```

dependancies: `PIL, io` (apftool)

dependancies: `sys, os, io` (apfcli)

most of these a builtins but you may need to install PIL seporately
