# -*- coding: utf-8 -*-
"""Step 1: 解析 APK 基本信息、Manifest、文件结构"""
import os
import json
from androguard.core.apk import APK

APK_PATH = r"C:\Users\LHN20\Desktop\简约记账.apk"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
os.makedirs(OUT_DIR, exist_ok=True)

apk = APK(APK_PATH)

# 基本信息
info = {
    "package": apk.get_package(),
    "app_name": apk.get_app_name(),
    "version_name": apk.get_androidversion_name(),
    "version_code": apk.get_androidversion_code(),
    "min_sdk": apk.get_min_sdk_version(),
    "target_sdk": apk.get_target_sdk_version(),
    "permissions": apk.get_permissions(),
    "activities": apk.get_activities(),
    "main_activity": apk.get_main_activity(),
}
print("=" * 60)
print("包名:", info["package"])
print("应用名:", info["app_name"])
print("版本:", info["version_name"], "(", info["version_code"], ")")
print("SDK:", info["min_sdk"], "->", info["target_sdk"])
print("主 Activity:", info["main_activity"])
print("Activity 列表:")
for a in info["activities"]:
    print("   -", a)
print("权限:")
for p in info["permissions"]:
    print("   -", p)

with open(os.path.join(OUT_DIR, "info.json"), "w", encoding="utf-8") as f:
    json.dump(info, f, ensure_ascii=False, indent=2, default=str)

# Manifest XML
try:
    xml = apk.get_android_manifest_axml().get_xml()
    manifest_xml = xml.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")
    with open(os.path.join(OUT_DIR, "AndroidManifest.xml"), "w", encoding="utf-8") as f:
        f.write(manifest_xml)
    print("\nManifest 已保存 -> output/AndroidManifest.xml")
except Exception as e:
    print("Manifest 解码失败:", e)

# 文件结构统计
files = apk.get_files()
stats = {}
for fn in files:
    ext = os.path.splitext(fn)[1].lower() or "(none)"
    stats.setdefault(ext, []).append(fn)

print("\n文件类型统计:")
for ext, lst in sorted(stats.items(), key=lambda x: -len(x[1])):
    print(f"  {ext or '(无扩展名)'}: {len(lst)} 个")

# 保存 layout / drawable 相关文件列表
interesting = [f for f in files if any(k in f.lower() for k in ["res/layout", "res/drawable", "assets", "smali", "classes"])]
with open(os.path.join(OUT_DIR, "file_list.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(files))
with open(os.path.join(OUT_DIR, "interesting_files.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(interesting))

print("\n文件列表已保存 -> output/file_list.txt")
print("重点关注文件 -> output/interesting_files.txt")
