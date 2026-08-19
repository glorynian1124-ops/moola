# -*- coding: utf-8 -*-
"""解析选项设置页各行图标名"""
import logging, re, json
logging.disable(logging.CRITICAL)
try:
    from loguru import logger
    logger.remove()
except Exception:
    pass
from androguard.core.apk import APK
from androguard.core.axml import ARSCParser, AXMLPrinter

apk = APK(r"C:\Users\LHN20\Desktop\简约记账.apk")
arsc = ARSCParser(apk.get_file("resources.arsc"))
pkg = arsc.get_packages_names()[0]

xml = AXMLPrinter(apk.get_file("res/sH.xml")).get_xml().decode("utf-8", errors="ignore")
refs = re.findall(r'android:src="(@7F08[0-9A-F]+)"', xml)
seen = []
for r in refs:
    if r not in seen:
        seen.append(r)
        rid = int(r[1:], 16)
        t, n, _ = arsc.get_id(pkg, rid)
        vals = arsc.get_resolved_res_configs(rid)
        fn = None
        for cfg, v in vals:
            if isinstance(v, str) and "res/" in v:
                fn = v
                break
        print(r, "->", n, "->", fn)
