#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Risk of Rain 2 Unlocker - Web Version
Flask 后端服务
"""

import os
import sys
import json
import shutil
import string
import subprocess
import webbrowser
from threading import Timer
from ctypes import windll
import xml.etree.ElementTree as ET

from flask import Flask, render_template, jsonify, request, send_from_directory

app = Flask(__name__, static_folder='static', static_url_path='/static')

# 全局配置
CONFIG = {
    "steam64_folder": os.path.join("Program Files (x86)", "Steam"),
    "steam32_folder": os.path.join("Program Files", "Steam"),
    "settings_path": os.path.join("632360", "remote", "UserProfiles"),
    "xml_header": '<?xml version="1.0" encoding="utf-8"?>'
}

# 全局数据
DATA = {}
PROFILES = {}


def get_resource_path(relative_path):
    """获取资源文件路径"""
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(base_path, relative_path)


def load_game_data():
    """加载游戏数据"""
    global DATA
    json_path = get_resource_path(os.path.join("static", "data.json"))
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                DATA = json.load(f)
        except Exception as e:
            print(f"加载数据失败: {e}")


def get_drives():
    """获取所有驱动器"""
    drives = []
    bitmask = windll.kernel32.GetLogicalDrives()
    for letter in string.ascii_uppercase:
        if bitmask & 1:
            drives.append(letter)
        bitmask >>= 1
    return drives


def get_game_directory():
    """获取游戏安装目录"""
    steam_paths = get_steam_paths()

    for steam_path in steam_paths:
        # 检查 appmanifest 确认游戏在这个库
        manifest = os.path.join(steam_path, "steamapps", "appmanifest_632360.acf")
        if os.path.isfile(manifest):
            game_path = os.path.join(steam_path, "steamapps", "common", "Risk of Rain 2")
            if os.path.isdir(game_path):
                return game_path

    # 备选：直接检查常见路径
    for steam_path in steam_paths:
        game_path = os.path.join(steam_path, "steamapps", "common", "Risk of Rain 2")
        if os.path.isdir(game_path):
            return game_path

    return None


def get_steam_paths():
    """获取 Steam 路径"""
    paths = []
    for reg_path in ("HKLM\\SOFTWARE\\WOW6432Node\\Valve\\Steam", "HKLM\\SOFTWARE\\Valve\\Steam"):
        try:
            p = subprocess.Popen(["reg.exe", "query", reg_path, "/v", "InstallPath"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            o, e = p.communicate()
            o = o.decode("utf-8").replace("\r", "")
            for line in o.split("\n"):
                line = line.lstrip()
                if line.lower().startswith("installpath"):
                    try:
                        s_path = line[line.index("REG_SZ") + len("REG_SZ"):].lstrip()
                        if os.path.isdir(s_path):
                            paths.append(s_path)
                            # 检查 Steam 库
                            lib_file = os.path.join(s_path, "steamapps", "libraryfolders.vdf")
                            if os.path.isfile(lib_file):
                                with open(lib_file, "rb") as f:
                                    content = f.read().decode("utf-8")
                                for lib_line in content.split("\n"):
                                    lib_line = lib_line.lstrip()
                                    if lib_line.startswith('"path"'):
                                        try:
                                            lib_path = lib_line.split('"')[3].replace("\\\\", "\\")
                                            paths.append(lib_path)
                                        except:
                                            pass
                    except:
                        pass
        except:
            pass
    return list(set(paths))


def scan_profiles():
    """扫描所有存档"""
    global PROFILES
    PROFILES = {}

    check_paths = get_steam_paths()
    for folder in (CONFIG["steam32_folder"], CONFIG["steam64_folder"]):
        check_paths.extend([os.path.join(drive + ":\\", folder) for drive in get_drives()])

    check_paths = list(set(check_paths))

    for check_folder in check_paths:
        user_folder = os.path.join(check_folder, "userdata")
        if not os.path.isdir(user_folder):
            continue

        for steam_id in os.listdir(user_folder):
            profile_path = os.path.join(user_folder, steam_id, CONFIG["settings_path"])
            if not os.path.exists(profile_path):
                continue

            for xml_file in os.listdir(profile_path):
                if xml_file.startswith(".") or not xml_file.lower().endswith(".xml"):
                    continue

                try:
                    full_path = os.path.join(profile_path, xml_file)
                    tree = ET.parse(full_path)
                    root = tree.getroot()
                    name = root.find("name").text

                    profile_id = f"{steam_id}_{xml_file}"
                    PROFILES[profile_id] = {
                        "steam_id": steam_id,
                        "file": xml_file,
                        "name": name,
                        "full_path": full_path,
                        "root": root
                    }
                except Exception as e:
                    print(f"加载存档失败: {xml_file}, {e}")

    return PROFILES


def get_profile(profile_id):
    """获取指定存档"""
    if profile_id not in PROFILES:
        # 重新加载
        full_path = PROFILES.get(profile_id, {}).get("full_path")
        if full_path and os.path.exists(full_path):
            tree = ET.parse(full_path)
            PROFILES[profile_id]["root"] = tree.getroot()
    return PROFILES.get(profile_id)


def save_profile(profile_id):
    """保存存档"""
    profile = PROFILES.get(profile_id)
    if not profile:
        return False

    target_file = profile["full_path"]
    backup_file = target_file + ".bak"

    if not os.path.exists(backup_file):
        shutil.copyfile(target_file, backup_file)

    output_xml = ET.tostring(profile["root"], encoding="unicode")
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(CONFIG["xml_header"] + output_xml)

    return True


# ==================== 路由 ====================

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/api/profiles')
def api_profiles():
    """获取所有存档"""
    scan_profiles()
    result = []
    for pid, profile in PROFILES.items():
        result.append({
            "id": pid,
            "steam_id": profile["steam_id"],
            "name": profile["name"],
            "file": profile["file"]
        })
    return jsonify(result)


@app.route('/api/profile/<profile_id>')
def api_profile_detail(profile_id):
    """获取存档详情"""
    profile = get_profile(profile_id)
    if not profile:
        return jsonify({"error": "存档不存在"}), 404

    root = profile["root"]

    # 收集数据
    characters = ["Characters.Commando"]
    skills_skins = []
    items = []

    for unlock in root.iter("unlock"):
        if not unlock.text:
            continue
        text = unlock.text
        if text.startswith("Characters.") and text not in characters:
            characters.append(text)
        elif text.startswith(("Skills.", "Skins.")):
            skills_skins.append(text)
        elif text.startswith(("Items.", "Artifacts.")):
            items.append(text)

    # 成就
    achi_elem = root.find("achievementsList")
    achievements = achi_elem.text.split() if achi_elem is not None and achi_elem.text else []

    # 图鉴
    discovered = root.find("discoveredPickups")
    logbook = discovered.text.split() if discovered is not None and discovered.text else []

    # 月球币
    coins_elem = root.find("coins")
    coins = int(coins_elem.text) if coins_elem is not None and coins_elem.text else 0

    return jsonify({
        "name": profile["name"],
        "coins": coins,
        "characters": sorted(characters),
        "skills_skins": sorted(skills_skins),
        "items": sorted(items),
        "achievements": sorted(achievements),
        "logbook": {
            "items": sorted([x for x in logbook if x.startswith("ItemIndex.")]),
            "equipment": sorted([x for x in logbook if x.startswith("EquipmentIndex.")]),
            "artifacts": sorted([x for x in logbook if x.startswith("ArtifactIndex.")]),
            "drones": sorted([x for x in logbook if x.startswith("DroneIndex.")])
        },
        "logbook_total": len(logbook)
    })


@app.route('/api/game-data')
def api_game_data():
    """获取游戏数据（可解锁内容列表）"""
    return jsonify(DATA)


@app.route('/api/profile/<profile_id>/coins', methods=['POST'])
def api_set_coins(profile_id):
    """设置月球币"""
    profile = get_profile(profile_id)
    if not profile:
        return jsonify({"error": "存档不存在"}), 404

    data = request.json
    coins = min(max(0, int(data.get("coins", 0))), 2147483647)

    root = profile["root"]
    coins_elem = root.find("coins")
    if coins_elem is not None:
        coins_elem.text = str(coins)

    total_coins = root.find("totalCollectedCoins")
    if total_coins is not None:
        total_coins.text = str(coins)

    save_profile(profile_id)
    return jsonify({"success": True, "coins": coins})


@app.route('/api/profile/<profile_id>/unlock', methods=['POST'])
def api_unlock(profile_id):
    """解锁内容"""
    profile = get_profile(profile_id)
    if not profile:
        return jsonify({"error": "存档不存在"}), 404

    data = request.json
    element = data.get("element", "")

    if not element or element.lower() == "characters.commando":
        return jsonify({"success": False, "message": "无效的解锁项"})

    root = profile["root"]

    # 检查是否已存在
    for unlock in root.iter("unlock"):
        if unlock.text and unlock.text.lower() == element.lower():
            return jsonify({"success": False, "message": "已经解锁"})

    # 添加解锁
    stats = root.find("stats")
    if stats is not None:
        new_unlock = ET.SubElement(stats, "unlock")
        new_unlock.text = element
        save_profile(profile_id)
        return jsonify({"success": True})

    return jsonify({"success": False, "message": "无法解锁"})


@app.route('/api/profile/<profile_id>/lock', methods=['POST'])
def api_lock(profile_id):
    """锁定内容"""
    profile = get_profile(profile_id)
    if not profile:
        return jsonify({"error": "存档不存在"}), 404

    data = request.json
    element = data.get("element", "")

    if element.lower() == "characters.commando":
        return jsonify({"success": False, "message": "Commando 无法锁定"})

    root = profile["root"]
    stats = root.find("stats")

    if stats is not None:
        for unlock in list(root.iter("unlock")):
            if unlock.text and unlock.text.lower() == element.lower():
                stats.remove(unlock)
                save_profile(profile_id)
                return jsonify({"success": True})

    return jsonify({"success": False, "message": "未找到该项"})


@app.route('/api/profile/<profile_id>/unlock-achievement', methods=['POST'])
def api_unlock_achievement(profile_id):
    """解锁成就"""
    profile = get_profile(profile_id)
    if not profile:
        return jsonify({"error": "存档不存在"}), 404

    data = request.json
    achievement = data.get("achievement", "")

    root = profile["root"]
    achi_elem = root.find("achievementsList")

    if achi_elem is None:
        return jsonify({"success": False, "message": "找不到成就列表"})

    current = achi_elem.text.split() if achi_elem.text else []
    if achievement.lower() in [a.lower() for a in current]:
        return jsonify({"success": False, "message": "成就已解锁"})

    current.append(achievement)
    achi_elem.text = " ".join(current)
    save_profile(profile_id)

    return jsonify({"success": True})


@app.route('/api/profile/<profile_id>/lock-achievement', methods=['POST'])
def api_lock_achievement(profile_id):
    """锁定成就"""
    profile = get_profile(profile_id)
    if not profile:
        return jsonify({"error": "存档不存在"}), 404

    data = request.json
    achievement = data.get("achievement", "")

    root = profile["root"]
    achi_elem = root.find("achievementsList")

    if achi_elem is None or not achi_elem.text:
        return jsonify({"success": False, "message": "没有成就"})

    current = achi_elem.text.split()
    new_list = [a for a in current if a.lower() != achievement.lower()]

    if len(new_list) == len(current):
        return jsonify({"success": False, "message": "未找到该成就"})

    achi_elem.text = " ".join(new_list)
    save_profile(profile_id)

    return jsonify({"success": True})


@app.route('/api/profile/<profile_id>/unlock-logbook', methods=['POST'])
def api_unlock_logbook(profile_id):
    """解锁图鉴（单个或全部）"""
    profile = get_profile(profile_id)
    if not profile:
        return jsonify({"error": "存档不存在"}), 404

    data = request.json or {}
    item = data.get("item", "")  # 单个物品

    root = profile["root"]
    discovered = root.find("discoveredPickups")

    if discovered is None:
        discovered = ET.SubElement(root, "discoveredPickups")

    current = set(discovered.text.split() if discovered.text else [])

    if item:
        # 解锁单个物品
        if item in current:
            return jsonify({"success": False, "message": "已经解锁"})
        current.add(item)
        discovered.text = " ".join(sorted(current))
        save_profile(profile_id)
        return jsonify({"success": True, "count": 1})
    else:
        # 解锁全部
        count = 0
        logbook = DATA.get("Logbook", {})
        for category in ["Items", "Equipment", "Artifacts", "Drones"]:
            for lb_item in logbook.get(category, []):
                if lb_item not in current:
                    current.add(lb_item)
                    count += 1

        discovered.text = " ".join(sorted(current))
        save_profile(profile_id)
        return jsonify({"success": True, "count": count})


@app.route('/api/profile/<profile_id>/lock-logbook', methods=['POST'])
def api_lock_logbook(profile_id):
    """锁定图鉴物品"""
    profile = get_profile(profile_id)
    if not profile:
        return jsonify({"error": "存档不存在"}), 404

    data = request.json or {}
    item = data.get("item", "")

    root = profile["root"]
    discovered = root.find("discoveredPickups")

    if discovered is None or not discovered.text:
        return jsonify({"success": False, "message": "图鉴为空"})

    current = set(discovered.text.split())
    if item not in current:
        return jsonify({"success": False, "message": "该物品未解锁"})

    current.remove(item)
    discovered.text = " ".join(sorted(current))
    save_profile(profile_id)
    return jsonify({"success": True})


@app.route('/api/profile/<profile_id>/clear-logbook', methods=['POST'])
def api_clear_logbook(profile_id):
    """清空图鉴"""
    profile = get_profile(profile_id)
    if not profile:
        return jsonify({"error": "存档不存在"}), 404

    root = profile["root"]
    discovered = root.find("discoveredPickups")

    if discovered is not None:
        discovered.text = ""

    save_profile(profile_id)
    return jsonify({"success": True})


@app.route('/api/profile/<profile_id>/unlock-all', methods=['POST'])
def api_unlock_all(profile_id):
    """解锁所有内容"""
    profile = get_profile(profile_id)
    if not profile:
        return jsonify({"error": "存档不存在"}), 404

    root = profile["root"]
    stats = root.find("stats")
    total = 0

    # 获取已有的解锁
    existing = set()
    for unlock in root.iter("unlock"):
        if unlock.text:
            existing.add(unlock.text.lower())

    # 解锁角色和技能
    for char_name, char_info in DATA.get("Characters", {}).items():
        char_key = f"Characters.{char_name}"
        if char_key.lower() not in existing:
            new_unlock = ET.SubElement(stats, "unlock")
            new_unlock.text = char_key
            total += 1

        for skill in char_info.get("unlocks", []):
            if skill.lower() not in existing:
                new_unlock = ET.SubElement(stats, "unlock")
                new_unlock.text = skill
                total += 1

    # 解锁物品
    for item in DATA.get("Items", []):
        if item.lower() not in existing:
            new_unlock = ET.SubElement(stats, "unlock")
            new_unlock.text = item
            total += 1

    # 解锁成就
    achi_elem = root.find("achievementsList")
    if achi_elem is not None:
        current = set(achi_elem.text.split() if achi_elem.text else [])
        for achi in DATA.get("Achievements", []):
            if achi not in current:
                current.add(achi)
                total += 1
        achi_elem.text = " ".join(sorted(current))

    # 解锁图鉴
    discovered = root.find("discoveredPickups")
    if discovered is None:
        discovered = ET.SubElement(root, "discoveredPickups")

    current_logbook = set(discovered.text.split() if discovered.text else [])
    for category in DATA.get("Logbook", {}).values():
        for item in category:
            if item not in current_logbook:
                current_logbook.add(item)
                total += 1
    discovered.text = " ".join(sorted(current_logbook))

    save_profile(profile_id)
    return jsonify({"success": True, "count": total})


@app.route('/api/profile/<profile_id>/lock-all', methods=['POST'])
def api_lock_all(profile_id):
    """锁定所有内容"""
    profile = get_profile(profile_id)
    if not profile:
        return jsonify({"error": "存档不存在"}), 404

    root = profile["root"]
    stats = root.find("stats")

    # 清除解锁（保留 Commando）
    if stats is not None:
        for unlock in list(root.iter("unlock")):
            if unlock.text and unlock.text.lower() != "characters.commando":
                stats.remove(unlock)

    # 清空成就
    achi_elem = root.find("achievementsList")
    if achi_elem is not None:
        achi_elem.text = ""

    # 清空图鉴
    discovered = root.find("discoveredPickups")
    if discovered is not None:
        discovered.text = ""

    save_profile(profile_id)
    return jsonify({"success": True})


@app.route('/api/game-path')
def api_game_path():
    """获取游戏安装目录"""
    game_path = get_game_directory()
    if game_path:
        dll_exists = os.path.isfile(os.path.join(game_path, "version.dll"))
        return jsonify({"path": game_path, "dll_installed": dll_exists})
    return jsonify({"path": None, "dll_installed": False})


@app.route('/api/dlc/install', methods=['POST'])
def api_install_dlc():
    """安装 DLC 补丁（复制 version.dll 到游戏目录）"""
    data = request.json or {}
    manual_path = data.get("path", "")

    # 优先使用手动输入的路径
    if manual_path:
        if os.path.isdir(manual_path):
            game_path = manual_path
        else:
            return jsonify({"success": False, "message": "输入的路径不存在", "need_path": True})
    else:
        game_path = get_game_directory()

    if not game_path:
        return jsonify({"success": False, "message": "未找到游戏目录，请手动输入路径", "need_path": True})

    # 获取 version.dll 源文件路径
    source_dll = get_resource_path("version.dll")
    if not os.path.isfile(source_dll):
        return jsonify({"success": False, "message": "未找到 version.dll 文件"})

    target_dll = os.path.join(game_path, "version.dll")

    try:
        shutil.copyfile(source_dll, target_dll)
        return jsonify({"success": True, "message": "DLC 补丁已安装", "path": target_dll})
    except Exception as e:
        return jsonify({"success": False, "message": f"安装失败: {str(e)}"})


@app.route('/api/dlc/uninstall', methods=['POST'])
def api_uninstall_dlc():
    """卸载 DLC 补丁（删除游戏目录的 version.dll）"""
    data = request.json or {}
    manual_path = data.get("path", "")

    # 优先使用手动输入的路径
    if manual_path:
        if os.path.isdir(manual_path):
            game_path = manual_path
        else:
            return jsonify({"success": False, "message": "输入的路径不存在", "need_path": True})
    else:
        game_path = get_game_directory()

    if not game_path:
        return jsonify({"success": False, "message": "未找到游戏目录，请手动输入路径", "need_path": True})

    target_dll = os.path.join(game_path, "version.dll")

    if not os.path.isfile(target_dll):
        return jsonify({"success": False, "message": "请确认目录下有 DLC 补丁文件 (version.dll)"})

    try:
        os.remove(target_dll)
        return jsonify({"success": True, "message": "DLC 补丁已移除"})
    except Exception as e:
        return jsonify({"success": False, "message": f"移除失败: {str(e)}"})


def open_browser():
    """打开浏览器"""
    webbrowser.open('http://127.0.0.1:5000')


if __name__ == '__main__':
    load_game_data()
    scan_profiles()

    # 延迟打开浏览器
    Timer(1.5, open_browser).start()

    print("=" * 50)
    print("  Risk of Rain 2 Unlocker - Web Version")
    print("  访问: http://127.0.0.1:5000")
    print("  按 Ctrl+C 停止服务")
    print("=" * 50)

    app.run(debug=False, port=5000)
