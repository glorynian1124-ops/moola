# -*- coding: utf-8 -*-
"""Step 12: 提取分类/菜单/tab 图标到 prototype/assets/icons，并检测颜色"""
import os
import json
import logging
logging.disable(logging.CRITICAL)
try:
    from loguru import logger
    logger.remove()
except Exception:
    pass

from androguard.core.apk import APK
from androguard.core.axml import ARSCParser
from PIL import Image
import io

APK_PATH = r"C:\Users\LHN20\Desktop\简约记账.apk"
ICONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "prototype", "assets", "icons")
os.makedirs(ICONS_DIR, exist_ok=True)

apk = APK(APK_PATH)
arsc = ARSCParser(apk.get_file("resources.arsc"))
pkg = arsc.get_packages_names()[0]
arsc.get_color_resources(pkg)

# 从 drawable_map_full.json 读映射
MAP_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", "drawable_map_full.json")
with open(MAP_FILE, "r", encoding="utf-8") as f:
    drawables = json.load(f)
file_by_name = {d["name"]: d["file"] for d in drawables if d["file"] and d["file"].endswith(".png")}

# 需要的图标：APK名 -> 目标名
WANT = {
    # 分类（支出）
    "restaurant": "cate_restaurant.png", "bus": "cate_bus.png", "shopping": "cate_shopping.png",
    "home": "cate_home.png", "game": "cate_game.png", "medical": "cate_medical.png",
    "study": "cate_study.png", "redirect": "cate_redirect.png", "carrot": "cate_fruit.png",
    "cookie": "cate_snack.png", "cloth": "cate_cloth.png", "repair0": "cate_daily.png",
    "phone": "cate_phone.png", "more": "cate_more.png",
    # 分类（收入）
    "salary": "cate_salary.png", "reward": "cate_reward.png", "redbag": "cate_redbag.png",
    "refund": "cate_refund.png", "reimburse": "cate_reimburse.png", "investment": "cate_invest.png",
    "partjob": "cate_partjob.png", "moneybag": "cate_moneybag.png",
    # 菜单
    "vip": "menu_vip.png", "sync": "menu_sync.png", "types": "menu_types.png",
    "moresetting": "menu_setting.png", "widget": "menu_widget.png", "remind": "menu_remind.png",
    "export": "menu_export.png", "fingerprint": "menu_finger.png", "secret": "menu_gesture.png",
    "theme": "menu_theme.png", "about": "menu_about.png",
    # Tab
    "list": "tab_list.png", "statistics": "tab_stat.png", "image": "tab_pic.png", "profile": "tab_profile.png",
    # 其他界面
    "user": "ic_user.png", "wechat": "ic_wechat.png", "alipay": "ic_alipay.png",
    "camera": "ic_camera.png", "lock": "ic_lock.png", "money": "ic_money.png",
}

ok, miss = [], []
for apk_name, target in WANT.items():
    src = file_by_name.get(apk_name)
    if not src:
        miss.append(apk_name)
        continue
    try:
        data = apk.get_file(src)
        out_path = os.path.join(ICONS_DIR, target)
        with open(out_path, "wb") as f:
            f.write(data)
        ok.append((apk_name, target, len(data)))
    except Exception as e:
        miss.append(f"{apk_name}({e})")

print(f"提取成功: {len(ok)}")
for n, t, size in ok:
    print(f"  {n} -> {t} ({size}B)")
print(f"\n缺失: {miss}")

# 检查颜色（分类图标可能是彩色）
print("\n=== 图标颜色分析 ===")
for _, target, _ in ok:
    p = os.path.join(ICONS_DIR, target)
    try:
        im = Image.open(p).convert("RGBA")
        px = [pix for pix in im.getdata() if pix[3] > 128]
        if px:
            r = sum(c[0] for c in px) // len(px)
            g = sum(c[1] for c in px) // len(px)
            b = sum(c[2] for c in px) // len(px)
            kind = "彩色" if (max(r,g,b) - min(r,g,b)) > 40 else ("白色" if r > 200 else "深色")
            print(f"  {target}: 均值RGB({r},{g},{b}) {kind}")
    except Exception:
        pass
