import sys
import math
import re
import itertools

import matplotlib
import matplotlib.pyplot as plt
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QMessageBox
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure


matplotlib.use('Qt5Agg')  # 或者 'Qt5Agg' 等其他可用后端
plt.rcParams['font.sans-serif'] = ['SimHei']  # 如果 SimHei 可用
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号


def get_nearest_points(points):
    """分析相近点"""
    combinations = list(itertools.product(*points))

    min_dist = 1e100
    min_points = None
    for combo in combinations:
        dist = 0
        for p1, p2 in itertools.combinations(combo, 2):
            dist += math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)
        if dist < min_dist:
            min_dist = dist
            min_points = combo

    if not min_points:
        return None

    center_x = sum([p[0] for p in min_points]) / len(min_points)
    center_y = sum([p[1] for p in min_points]) / len(min_points)
    alpha = math.atan2(center_y, center_x) / math.pi * 180
    amp = math.sqrt(center_x ** 2 + center_y ** 2)
    return {
        'points': min_points,
        'center': (center_x, center_y),
        'alpha': alpha,
        'amp': amp,
    }


def cal_intersection(a0, a1, a2, theta1, theta2):
    """计算交点"""
    theta = (theta2 - theta1)
    theta1 = theta1
    k = (a1 * a1 - a2 * a2) / (2 * a0)
    a = 2 / (1 + math.cos(theta))
    b = a * k - 2 * a0
    c = k * k / (math.sin(theta)) ** 2 - a1 * a1 + a0 * a0
    delta = b * b - 4 * a * c

    if 0 <= delta < 1e-7:
        x1 = (-b) / (a * 2)
        y1 = (k + (1 - math.cos(theta)) * x1) / math.sin(theta)
    elif delta < 0:  # 无交点时，按圆心连线按比例取中点
        s = a0 * math.sin(theta / 2) + (a1 - a2) / 2
        x1 = s * math.cos(math.pi / 2 + theta / 2) + a0
        y1 = s * math.sin(math.pi / 2 + theta / 2)
    else:
        x1 = (-b - math.sqrt(delta)) / (a * 2)
        y1 = (k + (1 - math.cos(theta)) * x1) / math.sin(theta)

    # 通过旋转变换将基于设定第一次加重在x轴的坐标系变化到实际坐标系
    x1_ = x1 * math.cos(theta1) - y1 * math.sin(theta1)
    y1_ = x1 * math.sin(theta1) + y1 * math.cos(theta1)

    if delta >= 1e-7:
        x2 = (-b + math.sqrt(delta)) / (a * 2)
        y2 = (k + (1 - math.cos(theta)) * x2) / math.sin(theta)
        x2_ = x2 * math.cos(theta1) - y2 * math.sin(theta1)
        y2_ = x2 * math.sin(theta1) + y2 * math.cos(theta1)
        return (x1_, y1_), (x2_, y2_)
    else:
        return (x1_, y1_),


def get_all_intersection(a0, vibrations):
    """计算所有交点"""
    points = []
    for vib_pair in itertools.combinations(vibrations, 2):
        ps = cal_intersection(a0, vib_pair[0][0], vib_pair[1][0], vib_pair[0][1], vib_pair[1][1])
        points.append(ps)
    return points


def plot_three_points(ax, a0, vibrations, intersections, points):
    """三点法作图"""
    a0_circle = plt.Circle((0, 0), a0, fill=False, linestyle='--')
    ax.add_patch(a0_circle)

    vib_circles = []
    for vib in vibrations:
        vib_x = a0 * math.cos(vib[1])
        vib_y = a0 * math.sin(vib[1])
        ax.plot([0, vib_x], [0, vib_y], color='k', linestyle='--')
        vib_circles.append(plt.Circle((vib_x, vib_y), vib[0], fill=False))
        ax.add_patch(vib_circles[-1])

    for point_pair in intersections:
        for point in point_pair:
            ax.plot(point[0], point[1], marker='o', color='red')

    for i, point in enumerate(points['points']):
        if i == 0:
            ax.plot(point[0], point[1], marker='o', color='blue', label='相近点')
        ax.plot(point[0], point[1], marker='o', color='blue')

    center = points['center']

    ax.plot([0, center[0]], [0, center[1]], color='green', label='加重方向')
    ax.scatter([center[0]], [center[1]], marker='*', color='green', label='几何中心')

    ax.set_aspect('equal')
    ax.legend(loc='upper right')

    plt.tight_layout()


class ThreeBalancing(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(ThreeBalancing, self).__init__(parent)
        self.set_ui()
        self.button.clicked.connect(self.plot)

    def set_ui(self):
        self.setWindowTitle('三点法动平衡')  # 设置标题栏
        self.resize(800, 800)
        self.setWindowModality(QtCore.Qt.ApplicationModal)  # 应用程序模态

        self.figure = Figure()  # 创建一个空的Figure对象
        self.canvas = FigureCanvas(self.figure)

        # 创建一个工具栏实例
        self.toolbar = NavigationToolbar(self.canvas, self)

        self.gridLayout = QtWidgets.QGridLayout()

        self.label_a0 = QtWidgets.QLabel(parent=self, text="原始振幅：")
        self.label_try = QtWidgets.QLabel(parent=self, text="试加重：")
        self.label_angle = QtWidgets.QLabel(parent=self, text="加重振幅及角度：")

        self.input_a0 = QtWidgets.QLineEdit(self)
        self.input_try = QtWidgets.QSpinBox(self)
        self.input_try.setRange(0, 9999)
        self.input_try.setSuffix("g")
        self.input_angle = QtWidgets.QLineEdit(self)
        self.input_angle.setPlaceholderText(
            "按{振幅}∠{角度}的形式输入，英文逗号间隔，∠符可用/代替，例100/0,200/120,300/-120")

        self.label_result = QtWidgets.QLabel(parent=self, text='加重方案：')
        self.result_line = QtWidgets.QLineEdit(self)
        self.button = QtWidgets.QPushButton(self, text='计算')

        self.gridLayout.addWidget(self.label_a0, 0, 0)
        self.gridLayout.addWidget(self.label_try, 1, 0)
        self.gridLayout.addWidget(self.label_angle, 2, 0)
        self.gridLayout.addWidget(self.input_a0, 0, 1)
        self.gridLayout.addWidget(self.input_try, 1, 1)
        self.gridLayout.addWidget(self.input_angle, 2, 1)
        self.gridLayout.addWidget(self.label_result, 3, 0)
        self.gridLayout.addWidget(self.result_line, 3, 1)
        self.gridLayout.addWidget(self.button, 3, 2)

        self.layout = QVBoxLayout()
        self.layout.addLayout(self.gridLayout)  # 添加工具栏到布局中
        self.layout.addWidget(self.toolbar)  # 添加工具栏到布局中
        self.layout.addWidget(self.canvas)  # 添加工具栏到布局中

        self.setLayout(self.layout)

    def show_warning(self, text):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle('警告')

        msg_box.setText(text)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.setDefaultButton(QMessageBox.Ok)

        msg_box.exec_()

    def plot(self):
        try:
            original_amp = int(self.input_a0.text().strip())
        except Exception:
            self.show_warning('振幅输入错误！')
            return
        if original_amp <= 0:
            self.show_warning('振幅不能小于0！')

        p_try = self.input_try.value()

        vibs_string = self.input_angle.text().strip()
        vibs_string_list = vibs_string.split(',')
        if len(vibs_string_list) < 2:
            self.show_warning('加重振幅及角度输入错误！')
            return
        try:
            vibs = [tuple([float(v) for v in re.split(r'[/∠]', vib)]) for vib in vibs_string_list]
        except Exception:
            self.show_warning('加重振幅及角度输入错误！')
            return

        vibs = [(vib[0], vib[1] * math.pi / 180) for vib in vibs]

        intersections = get_all_intersection(original_amp, vibs)
        nearest_points = get_nearest_points(intersections)
        p_balance = p_try * original_amp / nearest_points['amp']

        text = f"{p_balance:0.1f}g∠{nearest_points['alpha']:0.1f}°"
        self.result_line.setText(text)

        self.canvas.figure.clf()
        fig = self.canvas.figure
        ax = fig.add_subplot()
        plot_three_points(ax, original_amp, vibs, intersections, nearest_points)
        fig.tight_layout()
        self.canvas.draw()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWin = ThreeBalancing()
    mainWin.show()
    sys.exit(app.exec_())
