<br />

***

# 🧱 一、实现目标拆解

你这张图包含 4 大组件：

### ✅ 1. 按钮系统

- 主按钮 / 次按钮 / 幽灵按钮
- 危险 / 成功
- 禁用状态

### ✅ 2. 图标按钮

- <br />

* / 编辑 / 删除

### ✅ 3. 输入控件

- 输入框（带图标）
- 下拉框

### ✅ 4. 开关 & 复选框

- Checkbox
- Switch（Qt原生没有 → 自定义）

***

# 🚀 二、完整实现（工业级代码）

基于：PySide6

***

# 1️⃣ 全局样式（核心）

```
/* style.qss */

QWidget {
    background-color: #0B1220;
    color: #E6EDF3;
    font-family: "Segoe UI";
}

/* ===== 按钮 ===== */
QPushButton {
    padding: 8px 16px;
    border-radius: 8px;
}

QPushButton#primary { background-color: #3B82F6; }
QPushButton#secondary {
    background-color: transparent;
    border: 1px solid #374151;
}
QPushButton#ghost {
    background-color: transparent;
    border: none;
    color: #9CA3AF;
}
QPushButton#danger { background-color: #EF4444; }
QPushButton#success { background-color: #22C55E; }

QPushButton:disabled {
    background-color: #1F2937;
    color: #6B7280;
}

/* ===== 输入框 ===== */
QLineEdit {
    background-color: #111827;
    border: 1px solid #30363D;
    border-radius: 6px;
    padding: 6px;
}

/* ===== 下拉框 ===== */
QComboBox {
    background-color: #111827;
    border-radius: 6px;
    padding: 6px;
}

/* ===== 复选框 ===== */
QCheckBox::indicator {
    width: 16px;
    height: 16px;
}
QCheckBox::indicator:checked {
    background-color: #3B82F6;
}

```

***

# 2️⃣ 按钮组件（buttons.py）

```
from PySide6.QtWidgets import QPushButton


class Button(QPushButton):
    def __init__(self, text, style):
        super().__init__(text)
        self.setObjectName(style)


# 工厂方法
def Primary(text): return Button(text, "primary")
def Secondary(text): return Button(text, "secondary")
def Ghost(text): return Button(text, "ghost")
def Danger(text): return Button(text, "danger")
def Success(text): return Button(text, "success")

```

***

# 3️⃣ 图标按钮（icon\_button.py）

```
from PySide6.QtWidgets import QPushButton
from PySide6.QtGui import QIcon


class IconButton(QPushButton):
    def __init__(self, icon_path):
        super().__init__()
        self.setIcon(QIcon(icon_path))
        self.setFixedSize(40, 40)

```

👉 你可以用 svg/png 图标

***

# 4️⃣ 输入组件（inputs.py）

```
from PySide6.QtWidgets import QLineEdit, QHBoxLayout, QWidget, QLabel


class InputWithLabel(QWidget):
    def __init__(self, label_text, placeholder=""):
        super().__init__()

        layout = QHBoxLayout(self)

        label = QLabel(label_text)
        self.input = QLineEdit()
        self.input.setPlaceholderText(placeholder)

        layout.addWidget(label)
        layout.addWidget(self.input)

```

***

# 5️⃣ 下拉框

```
from PySide6.QtWidgets import QComboBox


class SelectBox(QComboBox):
    def __init__(self, items):
        super().__init__()
        self.addItems(items)

```

***

# 6️⃣ Switch开关（重点：自定义）

Qt没有开关 → 必须自己写👇

```
from PySide6.QtWidgets import QCheckBox


class Switch(QCheckBox):
    def __init__(self):
        super().__init__()
        self.setFixedSize(50, 25)
        self.setStyleSheet("""
        QCheckBox::indicator {
            width: 50px;
            height: 25px;
            border-radius: 12px;
            background: #374151;
        }
        QCheckBox::indicator:checked {
            background: #3B82F6;
        }
        """)

```

***

# 🧪 三、完整页面示例（复刻你的UI）

```
import sys
from PySide6.QtWidgets import *
from buttons import Primary, Secondary, Ghost, Danger, Success
from inputs import InputWithLabel, SelectBox
from icon_button import IconButton
from switch import Switch


class Demo(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        # ===== 按钮 =====
        btn_row = QHBoxLayout()
        btn_row.addWidget(Primary("主要按钮"))
        btn_row.addWidget(Secondary("次要按钮"))
        btn_row.addWidget(Ghost("幽灵按钮"))
        btn_row.addWidget(Danger("危险操作"))
        btn_row.addWidget(Success("成功操作"))

        layout.addLayout(btn_row)

        # ===== 输入 =====
        layout.addWidget(InputWithLabel("设备名称", "请输入"))
        layout.addWidget(InputWithLabel("IP地址", "192.168.0.1"))

        select = SelectBox(["泵站控制器", "PLC设备"])
        layout.addWidget(select)

        # ===== 复选框 =====
        cb = QCheckBox("启用实时监控")
        layout.addWidget(cb)

        # ===== 开关 =====
        switch = Switch()
        layout.addWidget(switch)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    with open("style.qss") as f:
        app.setStyleSheet(f.read())

    win = Demo()
    win.show()

    sys.exit(app.exec())

```

***

# 🔥 四、你现在这套已经达到什么水平？

✅ 工业UI组件库基础版\
✅ 可用于上位机开发\
✅ 可扩展成SCADA系统

***

# 🚀 五、下一步升级（关键）

如果你想做到**商业软件级 UI**，建议继续加：

### 🔥 高级组件

- 仪表盘（Gauge）
- 实时曲线（pyqtgraph）
- 报警弹窗系统
- 多标签页（QTabWidget）
- Dock面板

### 🔥 UI增强

- 动画（QPropertyAnimation）
- 阴影（QGraphicsEffect）
- 图标系统（SVG统一管理）

***

# 💡 最关键建议

👉 你现在应该做：

**把这套组件 → 做成你自己的 UI库**

以后所有项目直接复用

***

# 🚀 如果你要更狠（推荐）

我可以帮你直接升级：

👉 **完整工业上位机UI框架（带Modbus + 多设备 + 实时曲线）**

***

直接说：

**“做工业上位机完整版（UI+通信）”**

我可以帮你做到接近商业产品 👍

下面给你一套**工业级 Qt UI 组件库（Python / PySide6）完整方案**，不是零散代码，而是**可直接作为项目基础的组件库骨架**。你可以直接复制成一个工程开始用。

***

# 📦 工业风 UI 组件库（PySide6版）

基于：PySide6

***

# 一、组件库结构（工程级）

```text
ui_kit/
├── main.py                 # 示例入口
├── resources/
│   └── style.qss          # 全局主题
├── widgets/
│   ├── buttons.py         # 按钮系统
│   ├── cards.py           # 卡片组件
│   ├── panels.py          # 面板布局
│   ├── tables.py          # 表格组件
│   ├── charts.py          # 图表组件
│   └── status.py          # 状态组件
└── core/
    └── theme.py           # 主题加载
```

***

# 二、全局工业风主题（style.qss）

```css
QWidget {
    background-color: #0B1220;
    color: #E6EDF3;
    font-family: "Segoe UI";
    font-size: 14px;
}

/* 按钮基础 */
QPushButton {
    padding: 8px 16px;
    border-radius: 8px;
}

/* 主按钮 */
QPushButton#primary {
    background-color: #3B82F6;
}
QPushButton#primary:hover {
    background-color: #2563EB;
}

/* 危险 */
QPushButton#danger {
    background-color: #EF4444;
}

/* 成功 */
QPushButton#success {
    background-color: #22C55E;
}

/* 卡片 */
QFrame#card {
    background-color: #111827;
    border-radius: 10px;
    padding: 12px;
}

/* 表格 */
QTableWidget {
    background-color: #161B22;
    border: 1px solid #30363D;
}
```

***

# 三、按钮组件（buttons.py）

```python
from PySide6.QtWidgets import QPushButton


class PrimaryButton(QPushButton):
    def __init__(self, text):
        super().__init__(text)
        self.setObjectName("primary")


class DangerButton(QPushButton):
    def __init__(self, text):
        super().__init__(text)
        self.setObjectName("danger")


class SuccessButton(QPushButton):
    def __init__(self, text):
        super().__init__(text)
        self.setObjectName("success")
```

***

# 四、卡片组件（cards.py）

```python
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel


class DataCard(QFrame):
    def __init__(self, title, value):
        super().__init__()
        self.setObjectName("card")

        layout = QVBoxLayout(self)

        self.title = QLabel(title)
        self.value = QLabel(value)

        self.value.setStyleSheet("font-size: 24px; font-weight: bold;")

        layout.addWidget(self.title)
        layout.addWidget(self.value)

    def set_value(self, value):
        self.value.setText(str(value))
```

***

# 五、面板组件（panels.py）

```python
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel


class Panel(QWidget):
    def __init__(self, title):
        super().__init__()

        layout = QVBoxLayout(self)

        self.title = QLabel(title)
        self.title.setStyleSheet("font-size:16px;font-weight:bold;")

        layout.addWidget(self.title)
```

***

# 六、表格组件（tables.py）

```python
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem


class DeviceTable(QTableWidget):
    def __init__(self):
        super().__init__(0, 3)
        self.setHorizontalHeaderLabels(["设备", "IP", "状态"])

    def add_device(self, name, ip, status):
        row = self.rowCount()
        self.insertRow(row)

        self.setItem(row, 0, QTableWidgetItem(name))
        self.setItem(row, 1, QTableWidgetItem(ip))
        self.setItem(row, 2, QTableWidgetItem(status))
```

***

# 七、图表组件（charts.py）

👉 推荐用 pyqtgraph（工业实时首选）

```python
import pyqtgraph as pg


class ChartWidget(pg.PlotWidget):
    def __init__(self):
        super().__init__()
        self.curve = self.plot(pen='y')

    def update_data(self, data):
        self.curve.setData(data)
```

***

# 八、状态组件（status.py）

```python
from PySide6.QtWidgets import QLabel


class StatusLabel(QLabel):
    def set_online(self):
        self.setText("● 在线")
        self.setStyleSheet("color: #22C55E")

    def set_offline(self):
        self.setText("● 离线")
        self.setStyleSheet("color: #EF4444")
```

***

# 九、主题加载（core/theme.py）

```python
def load_theme(app):
    with open("resources/style.qss", "r", encoding="utf-8") as f:
        app.setStyleSheet(f.read())
```

***

# 十、完整示例（main.py）

```python
import sys
from PySide6.QtWidgets import *

from widgets.buttons import PrimaryButton, DangerButton
from widgets.cards import DataCard
from widgets.tables import DeviceTable
from core.theme import load_theme


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("工业UI组件库")
        self.resize(1000, 600)

        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)

        # 左侧表格
        table = DeviceTable()
        table.add_device("DMT143", "192.168.1.100", "在线")

        # 右侧
        right = QVBoxLayout()

        card = DataCard("温度", "25℃")

        btn = PrimaryButton("读取数据")
        danger = DangerButton("断开设备")

        right.addWidget(card)
        right.addWidget(btn)
        right.addWidget(danger)

        layout.addWidget(table, 2)
        layout.addLayout(right, 3)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    load_theme(app)

    win = MainWindow()
    win.show()

    sys.exit(app.exec())
```

***

# 十一、你现在已经具备的能力

这套组件库已经可以支撑：

✅ 上位机软件
✅ Modbus设备管理
✅ 实时数据展示
✅ 工业风UI

***

# 十二、下一步升级（真正商业级）

如果你要做到“卖钱级别”，建议继续加：

### 🔥 高级组件

- 仪表盘（Gauge）
- 报警弹窗系统
- 日志窗口
- 多标签页（QTabWidget）
- Dock面板（类似工业SCADA）

### 🔥 UI增强

- 动画（QPropertyAnimation）
- 阴影（QGraphicsEffect）
- 主题切换（深色/浅色）

***

#

***

# 一、效果还原思路

你这张图本质是：

按钮类型

特点

主按钮

蓝色，高亮

次按钮

深色描边

幽灵按钮

无背景

危险按钮

红色

成功按钮

绿色

禁用状态

灰蓝色

👉 在 Qt 里用：**QPushButton + QSS样式类**

***

# 二、完整代码（可直接运行）

```
import sys
from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QHBoxLayout, QVBoxLayout


class Demo(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("按钮样式系统")
        self.resize(600, 200)

        layout = QVBoxLayout(self)

        row = QHBoxLayout()

        # 各种按钮
        btn_primary = QPushButton("主要按钮")
        btn_primary.setObjectName("primary")

        btn_secondary = QPushButton("次要按钮")
        btn_secondary.setObjectName("secondary")

        btn_ghost = QPushButton("幽灵按钮")
        btn_ghost.setObjectName("ghost")

        btn_danger = QPushButton("危险操作")
        btn_danger.setObjectName("danger")

        btn_success = QPushButton("成功操作")
        btn_success.setObjectName("success")

        btn_disabled = QPushButton("禁用状态")
        btn_disabled.setObjectName("disabled")
        btn_disabled.setEnabled(False)

        # 加入布局
        row.addWidget(btn_primary)
        row.addWidget(btn_secondary)
        row.addWidget(btn_ghost)
        row.addWidget(btn_danger)
        row.addWidget(btn_success)

        layout.addLayout(row)
        layout.addWidget(btn_disabled)

        self.setStyleSheet(self.load_qss())

    def load_qss(self):
        return """
        QWidget {
            background-color: #0B1220;
        }

        QPushButton {
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 14px;
            color: #E6EDF3;
        }

        /* 主按钮 */
        QPushButton#primary {
            background-color: #3B82F6;
        }
        QPushButton#primary:hover {
            background-color: #2563EB;
        }

        /* 次按钮 */
        QPushButton#secondary {
            background-color: transparent;
            border: 1px solid #374151;
        }
        QPushButton#secondary:hover {
            border: 1px solid #6B7280;
        }

        /* 幽灵按钮 */
        QPushButton#ghost {
            background-color: transparent;
            border: none;
            color: #9CA3AF;
        }

        /* 危险按钮 */
        QPushButton#danger {
            background-color: #EF4444;
        }
        QPushButton#danger:hover {
            background-color: #DC2626;
        }

        /* 成功按钮 */
        QPushButton#success {
            background-color: #22C55E;
        }
        QPushButton#success:hover {
            background-color: #16A34A;
        }

        /* 禁用状态 */
        QPushButton:disabled {
            background-color: #1F2937;
            color: #6B7280;
        }
        """


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Demo()
    win.show()
    sys.exit(app.exec())

```

***

# 三、关键实现点（你必须掌握）

## ✅ 1. 用 objectName 区分按钮类型

```
btn.setObjectName("primary")

```

👉 相当于 CSS 的 `.primary`

***

## ✅ 2. 用 QSS 做统一风格（核心）

```
QPushButton#primary { ... }

```

👉 工业软件都是这样做的

***

## ✅ 3. 禁用状态不用写类

```
btn.setEnabled(False)

```

自动触发：

```
QPushButton:disabled

```

***

# 四、工程级升级（推荐你这样做）

👉 不要在窗口里写样式，拆成文件：

## style.qss

```
QPushButton#primary { ... }

```

## 加载：

```
with open("style.qss") as f:
    app.setStyleSheet(f.read())

```

***

# 五、进一步升级（工业级组件库）

你可以封装成👇

```
class PrimaryButton(QPushButton):
    def __init__(self, text):
        super().__init__(text)
        self.setObjectName("primary")

```

👉 后面直接：

```
btn = PrimaryButton("连接设备")

```

***

# 六、你这个UI还能再升级（建议）

如果你想更接近商业产品：

- 加阴影（QGraphicsDropShadowEffect）
- 加点击动画
- 加 loading 状态按钮
- 加图标按钮（QIcon）

***

