# PB33: iAP control reports

The advertised HID report sizes reached 768 bytes, but the control buffer accepted only 256. The iAP configuration now allocates 768 bytes while other configurations keep 256. Tests cover advertised sizes and oversize rejection with ASan/UBSan. Native build and installed firmware verification passed; larger Lexus control reports were accepted. Audio and metadata were not fixed.
