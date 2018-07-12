import sys
from PyQt5.QtWidgets import *
from PyQt5 import QtCore
from PyQt5.QtGui import QBrush,QPainter,QPainterPath,QColor,QFont,QPen,QFontMetrics,QIcon,QPixmap,QIntValidator
from PyQt5.QtCore import QPropertyAnimation,QTimer,Qt
import win32gui
import win32con
from ws4py.client.threadedclient import WebSocketClient
import threading
import qrc_resources
import json

class Danmu(QLabel):
	def __init__(self,parent,dmtext,dmcolor,dmstartx,dmstarty,dmfont="Microsoft YaHei"):
		super(Danmu,self).__init__(parent)
		self.dmQfont = QFont(dmfont, 25, 75) #字体、大小、粗细
		self.setStyleSheet("color:"+dmcolor)
		self.dmtext = dmtext
		self.setText(self.dmtext)
		self.metrics = QFontMetrics(self.dmQfont)
		self.height = self.metrics.height()+5
		self.setFixedHeight(self.height)
		self.width = self.metrics.width(dmtext)+4
		self.setFixedWidth(self.width)
		self.setFont(self.dmQfont)

		self.fly = QPropertyAnimation(self,b'pos') #弹幕飞行动画
		self.fly.setDuration(10000) #飞行10秒
		self.fly.setStartValue(QtCore.QPoint(dmstartx,dmstarty))
		self.fly.setEndValue(QtCore.QPoint(0-self.width,dmstarty))
		self.fly.start()
		self.fly.finished.connect(self.deleteLater)

	#为文字添加描边
	def paintEvent(self,event):
		painter = QPainter(self)
		painter.save()
		path = QPainterPath()
		pen = QPen(QColor(0,0,0,230))
		painter.setRenderHint(QPainter.Antialiasing) #反走样
		pen.setWidth(4)
		length = self.metrics.width(self.dmtext)
		w = self.width
		px = (length-w)/2
		if px<0:
			px = -px
		py = (self.height-self.metrics.height())/2+self.metrics.ascent()
		if py<0:
			py = -py
		path.addText(px-2,py,self.dmQfont,self.dmtext)
		painter.strokePath(path,pen)
		painter.drawPath(path)
		painter.fillPath(path,QBrush(QColor(255,255,255)))
		painter.restore()
		QLabel.paintEvent(self,event)

class DanmuWindow(QWidget):
	def __init__(self,parent):
		super(DanmuWindow,self).__init__(parent)
		self.initUI()
		self.qw = QWidget(self)
		self.qw.setFixedSize(self.width,self.height)
		self.qb = QHBoxLayout(self.qw)

	def addDanmu(self,message,color,height):
		dm = Danmu(self,message,color,self.width,height)
		self.qb.addWidget(dm)

	def initUI(self):
		desktopWidget = QDesktopWidget() #获取屏幕信息
		self.width = desktopWidget.screenGeometry().width() #获取屏幕宽度
		self.height = desktopWidget.screenGeometry().height()+2000 #获取屏幕高度
		self.setFixedSize(self.width,self.height) #将窗口最大化
		self.setWindowTitle('YFdanmu') #窗口名称
		self.setAttribute(Qt.WA_TranslucentBackground, True) #窗口透明
		self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool) #窗口始终保持最前且不显示边框且任务栏不显示 

class MainWindow(QMainWindow):

	dmSignal = QtCore.pyqtSignal(str)
	room = ''

	def handle(self,content):
		content = json.loads(content)
		if content['type']=='danmu':
			color = content['color']
			message = content['text']
			for i in range(0,len(self.danmuLineFlag)):
				if self.danmuLineFlag[i]==0:
					self.danmuWindow.addDanmu(message,color,20+80*i)
					self.danmuLineFlag[i] = 1;
					break
		elif content['type']=='informn':
			self.statusBar().showMessage('已连接: '+content['n'])
		elif content['type']=='room':
			if content['n']!='err':
				self.room = str(content['n'])
				self.connectStatusLabel.setText('房间号: '+self.room)
				self.testButton.setEnabled(True)
				self.createRoomButton.setEnabled(False)
				self.joinRoomButton.setEnabled(False)
				self.testText.setEnabled(True)
			else:
				self.connectStatusLabel.setText('不存在该房间')
				self.testButton.setEnabled(False)
				self.createRoomButton.setEnabled(True)
				self.joinRoomButton.setEnabled(True)

	def __init__(self):
		super().__init__()
		self.initUI()
		self.danmuWindow = DanmuWindow(self) #创建弹幕窗口
		self.dmSignal.connect(self.handle)
		self.danmuColor = 'white'
		#弹幕冷却
		self.danmuLineFlag = [0]*13
		self.danmuCoolTime = [0]*13
		self.coolTimer = QTimer()
		self.coolTimer.timeout.connect(self.coolDownCount)
		self.coolTimer.start(500)

	def coolDownCount(self):
		for i in range(0,len(self.danmuLineFlag)):
			if self.danmuLineFlag[i]==1:
				if self.danmuCoolTime[i]==4:
					self.danmuCoolTime[i] = 0
					self.danmuLineFlag[i] = 0
				self.danmuCoolTime[i] += 1


	def initUI(self):
		self.setWindowTitle('桌面弹幕')
		self.setWindowIcon(QIcon(':/logo.png'))
		self.setFixedSize(600,360) #设置窗口大小
		self.statusBar().showMessage('未连接')
		self.setWindowFlags(self.windowFlags()& ~Qt.WindowMinimizeButtonHint)

		#qss加载
		with open('./src/style.qss') as f:
			style = f.read()
		self.setStyleSheet(style)

		self.createButton()    	#按钮
		self.createLabel()	  	#标签
		self.createText()       #文本框
		self.createSlider()     #滑动条
		self.show()

	#创建按钮
	def createButton(self):
		self.connectButton = QPushButton('连接服务器',self)
		self.connectButton.setFont(QFont("Microsoft YaHei",15))
		self.connectButton.move(50,50)
		self.connectButton.setFixedSize(200,75)
		self.connectButton.clicked.connect(self.connectServer)

		self.testButton = QPushButton('发送',self)
		self.testButton.setFont(QFont("Microsoft YaHei",10))
		self.testButton.move(350,227)
		self.testButton.setFixedSize(50,30)
		self.testButton.setEnabled(False)
		self.testButton.clicked.connect(self.sendDanmu)

		self.createRoomButton = QPushButton('创建',self)
		self.createRoomButton.setFont(QFont("Microsoft YaHei",10))
		self.createRoomButton.move(250,200)
		self.createRoomButton.setFixedSize(50,30)
		self.createRoomButton.setEnabled(False)
		self.createRoomButton.clicked.connect(self.createRoom)

		self.joinRoomButton = QPushButton('加入',self)
		self.joinRoomButton.setFont(QFont("Microsoft YaHei",10))
		self.joinRoomButton.move(320,200)
		self.joinRoomButton.setFixedSize(50,30)
		self.joinRoomButton.setEnabled(False)
		self.joinRoomButton.clicked.connect(self.joinRoom)

		self.miniButton = QPushButton('最小化到托盘',self)
		self.miniButton.clicked.connect(self.miniWindow)

		self.colorButtonGroup = QButtonGroup(self)

		self.colorButtonWhite = QRadioButton('白',self)
		self.colorButtonWhite.setFont(QFont("Microsoft YaHei",10))
		self.colorButtonWhite.move(50,260)
		self.colorButtonWhite.setChecked(True)
		self.colorButtonGroup.addButton(self.colorButtonWhite,0)
		self.colorButtonWhite.clicked.connect(self.changeColor)

		self.colorButtonRed = QRadioButton('红',self)
		self.colorButtonRed.setFont(QFont("Microsoft YaHei",10))
		self.colorButtonRed.move(100,260)
		self.colorButtonGroup.addButton(self.colorButtonRed,1)
		self.colorButtonRed.clicked.connect(self.changeColor)

		self.colorButtonYellow = QRadioButton('黄',self)
		self.colorButtonYellow.setFont(QFont("Microsoft YaHei",10))
		self.colorButtonYellow.move(150,260)
		self.colorButtonGroup.addButton(self.colorButtonYellow,2)
		self.colorButtonYellow.clicked.connect(self.changeColor)

		self.colorButtonGreen = QRadioButton('绿',self)
		self.colorButtonGreen.setFont(QFont("Microsoft YaHei",10))
		self.colorButtonGreen.move(200,260)
		self.colorButtonGroup.addButton(self.colorButtonGreen,3)
		self.colorButtonGreen.clicked.connect(self.changeColor)

		self.colorButtonBlue = QRadioButton('蓝',self)
		self.colorButtonBlue.setFont(QFont("Microsoft YaHei",10))
		self.colorButtonBlue.move(250,260)
		self.colorButtonGroup.addButton(self.colorButtonBlue,4)
		self.colorButtonBlue.clicked.connect(self.changeColor)

		self.colorButtonPink = QRadioButton('粉',self)
		self.colorButtonPink.setFont(QFont("Microsoft YaHei",10))
		self.colorButtonPink.move(300,260)
		self.colorButtonGroup.addButton(self.colorButtonPink,5)
		self.colorButtonPink.clicked.connect(self.changeColor)

	def changeColor(self):
		colorId = self.colorButtonGroup.checkedId()
		if colorId==0:
			self.danmuColor = 'white'
		elif colorId==1:
			self.danmuColor = 'red'
		elif colorId==2:
			self.danmuColor = 'yellow'
		elif colorId==3:
			self.danmuColor = 'green'
		elif colorId==4:
			self.danmuColor = 'blue'
		elif colorId==5:
			self.danmuColor = 'pink'

	#创建标签
	def createLabel(self):
		self.connectStatusLabel = QLabel('当前状态: 未连接',self)
		self.connectStatusLabel.setFont(QFont("Microsoft YaHei",10))
		self.connectStatusLabel.move(85,120)
		self.connectStatusLabel.setFixedSize(250,50)

		self.tranLabel = QLabel('弹幕透明度',self)
		self.tranLabel.setFont(QFont("Microsoft YaHei",12))
		self.tranLabel.move(300,30)

		self.tranMin = QLabel('全透明',self)
		self.tranMin.setFont(QFont("Microsoft YaHei",8))
		self.tranMin.move(300,57)

		self.tranMax = QLabel('不透明',self)
		self.tranMax.setFont(QFont("Microsoft YaHei",8))
		self.tranMax.move(507,57)

		self.testLabel = QLabel('弹幕:',self)
		self.testLabel.setFont(QFont("Microsoft YaHei",10))
		self.testLabel.setFixedSize(100,25)
		self.testLabel.move(50,230)

		self.wxLabel = QLabel(self)
		self.wxLabel.setFixedSize(160,160)
		self.wxLabel.move(440,200)
		wxEwm = QPixmap(':/wx.jpg')
		self.wxLabel.setPixmap(wxEwm)
		self.wxLabel.setScaledContents(True)

	#创建文本框
	def createText(self):
		self.testText = QLineEdit(self)
		self.testText.setFont(QFont("Microsoft YaHei",10))
		self.testText.setFixedSize(200,25)
		self.testText.move(140,230)
		self.testText.setEnabled(False)
		self.testText.returnPressed.connect(self.sendDanmu)

	#创建滑动条
	def createSlider(self):
		self.tranSlider = QSlider(Qt.Horizontal,self)
		self.tranSlider.move(350,63)
		self.tranSlider.setFixedSize(150,20)
		self.tranSlider.setRange(0,100)
		self.tranSlider.setValue(100)
		self.tranSlider.valueChanged.connect(self.tranChange)

	#透明度改变事件
	def tranChange(self,event):
		self.danmuWindow.setWindowOpacity(self.tranSlider.value()/100)

	#连接服务器
	def connectServer(self):
		try:
			self.threading = threading.Thread(target=self.connectingServer)
			self.threading.setDaemon(True)
			self.threading.start()
		except Exception as err:
			print(err)
			
		
	def connectingServer(self):
		try:
			self.ws = WebSocket('ws://127.0.0.1:8000/connect',self)
			self.ws.connect()
			self.connectStatusLabel.setText('当前状态:已连接')
			self.connectButton.setEnabled(False)
			self.createRoomButton.setEnabled(True)
			self.joinRoomButton.setEnabled(True)
			self.ws.run_forever()
		except Exception as err:
			print(err)
			self.connectStatusLabel.setText('连接失败')
			self.connectButton.setEnabled(True)

	def on_activedSysTrayIcon(self,reason):
		if reason == QSystemTrayIcon.ActivationReason(QSystemTrayIcon.Trigger):
			self.show()
			self.sysIcon.hide()


	def sendDanmu(self):
		try:
			message = {
				'type': 'danmu',
				'room': str(self.room),
				'color': str(self.danmuColor),
				'text': str(self.testText.text()),
			}
			message = json.dumps(message)
			self.ws.send(message)
			self.testText.setText('')
		except Exception as err:
			self.connectStatusLabel.setText('连接失败')
			self.connectButton.setEnabled(True)
			print(err)

	def createRoom(self):
		try:
			message = {
				'type': 'createroom',
			}
			message = json.dumps(message)
			self.ws.send(message)
		except Exception as err:
			self.connectStatusLabel.setText('连接失败')
			self.connectButton.setEnabled(True)
			print(err)

	def joinRoom(self):
		n, ok = QInputDialog.getInt(self, "加入房间", "请输入房间号:", 1, 1, 99999, 1)
		if ok:
			try:
				message = {
					'type': 'joinroom',
					'n': str(n),
				}
				message = json.dumps(message)
				self.ws.send(message)
			except Exception as err:
				self.connectStatusLabel.setText('连接失败')
				self.connectButton.setEnabled(True)
				print(err)

	def miniWindow(self):
		self.hide()
		self.sysIcon = QSystemTrayIcon(self)
		icon = QIcon(":/logo.png")
		self.sysIcon.setIcon(icon)
		self.sysIcon.setToolTip('桌面弹幕')
		self.sysIcon.activated.connect(self.on_activedSysTrayIcon)
		self.sysIcon.show()

class WebSocket(WebSocketClient):
	def __init__(self,url,parent):
		super().__init__(url)
		self.parent = parent
	def opened(self):
		print('websocked opened')
	def received_message(self,message):
		self.parent.dmSignal.emit(str(message))
	def on_closed(self):
		self.connectStatusLabel.setText('已断开服务器连接')

#将窗口置顶
def toTop():
	hwnd = win32gui.FindWindow(None, 'YFdanmu')
	win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, 0,0,0,0, win32con.SWP_NOMOVE|win32con.SWP_NOOWNERZORDER|win32con.SWP_NOACTIVATE|win32con.SWP_SHOWWINDOW|win32con.SWP_NOSIZE)


app = QApplication(sys.argv)

#每100毫秒将窗口置顶一次
timer = QTimer()
timer.timeout.connect(toTop)
timer.start(100)
mainWindow = MainWindow()
mainWindow.show()
mainWindow.danmuWindow.show()
sys.exit(app.exec_())