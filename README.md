# 雨中冒险2 存档解锁器

一个用于解锁 Risk of Rain 2 游戏存档内容的 Web 工具。

## 功能

- 解锁/锁定所有幸存者角色及技能
- 解锁/锁定所有物品和神器
- 解锁/锁定所有成就
- 解锁/锁定物品图鉴
- 设置月球币数量
- 一键全解锁/全锁定

## 使用方法

### 方式一：直接运行 exe（推荐）

1. 从 [Releases](../../releases) 下载 `unlock.exe`
2. 双击运行，浏览器会自动打开
3. 在下拉框中选择你的存档进行操作

### 方式二：从源码运行

1. 确保已安装 Python 3.7+
2. 安装依赖：
```bash
pip install flask
```
3. 运行程序：
```bash
python app.py
```
4. 打开浏览器访问：http://127.0.0.1:5000

## 存档位置

程序会自动检测以下路径的存档：
- `C:\Program Files (x86)\Steam\userdata\{SteamID}\632360\remote\UserProfiles\`

## 注意事项

- 修改存档前会自动创建 `.bak` 备份文件
- 游戏运行时请勿修改存档
- Commando（指挥官）为默认角色，无法锁定

## 项目结构

```
/
├── unlock.exe   # 独立可执行文件（从 Releases 下载）
├── app.py             # Flask 后端
├── requirements.txt   # Python 依赖
├── static/
│   └── logo.png       # Logo 图片
 |    └──data.json      # 游戏数据
└── templates/
    └── index.html     # Web 界面
```

## 许可证

MIT License
