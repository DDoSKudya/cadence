STYLE = """
* {
  font-family: Inter, Cantarell, Ubuntu, sans-serif;
}
QMainWindow, QWidget#ShellRoot {
  background-color: #e8ebf1;
}
QFrame[panel="true"] {
  background-color: #ffffff;
  border: 1px solid #d0d6e0;
  border-radius: 10px;
}
QLabel[role="title"] {
  color: #161b26;
  font-size: 16px;
  font-weight: 700;
}
QLabel[role="status"] {
  color: #5c6478;
  font-size: 12px;
}
QLabel[role="status"][running="true"] {
  color: #2563eb;
}
QPushButton {
  border-radius: 8px;
  padding: 10px 16px;
  font-size: 13px;
  font-weight: 600;
  min-height: 0;
  border: none;
}
QPushButton[variant="start"] {
  background-color: #5b6ee8;
  color: #ffffff;
}
QPushButton[variant="stop"] {
  background-color: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}
QPushButton[variant="open"] {
  background-color: #eef0ff;
  color: #5b6ee8;
}
QPushButton[pulse="true"] {
  border: 2px solid #5b6ee8;
}
QPushButton[variant="lang"] {
  background-color: #f4f6f9;
  color: #5c6478;
  padding: 4px 8px;
  font-size: 11px;
  font-weight: 700;
  min-width: 28px;
}
QPushButton[variant="lang"][active="true"] {
  background-color: #eef0ff;
  color: #5b6ee8;
}
QScrollArea#ServicesScroller > QWidget > QWidget {
  background-color: transparent;
}
QPushButton:disabled {
  opacity: 0.45;
}
QLabel[role="servicesHead"] {
  color: #8b95a8;
  font-size: 10px;
  font-weight: 700;
  padding: 10px 14px 6px 14px;
}
QWidget#ServicesBody, QScrollArea#ServicesScroller {
  background-color: transparent;
  border: none;
}
QWidget#ServicesContainer {
  background-color: transparent;
}
QFrame[service="true"] {
  background-color: #f4f6f9;
  border: 1px solid #e8ebf0;
  border-radius: 8px;
  margin-bottom: 6px;
}
QFrame[service="true"][pulse="true"] {
  background-color: #eef0ff;
  border-color: #c5ccf7;
}
QLabel[role="serviceName"] {
  color: #161b26;
  font-size: 12px;
  font-weight: 600;
}
QLabel[role="badge"] {
  border-radius: 999px;
  min-width: 22px;
  padding: 1px 0;
  font-size: 14px;
  font-weight: 700;
}
QLabel[role="badge"][state="healthy"],
QLabel[role="badge"][state="running"] {
  background-color: #eef4ff;
  color: #2563eb;
}
QLabel[role="badge"][state="starting"],
QLabel[role="badge"][state="stopped"],
QLabel[role="badge"][state="unknown"] {
  background-color: #eceef2;
  color: #9ca3af;
}
QLabel[role="badge"][state="unhealthy"],
QLabel[role="badge"][state="exited"] {
  background-color: #fef2f2;
  color: #dc2626;
}
QLabel[role="badge"][flash="true"] {
  background-color: #dce2ff;
}
QFrame[activity="true"] {
  background-color: #ffffff;
  border: 1px solid #d0d6e0;
  border-radius: 10px;
}
QWidget[role="activitySpinnerWrap"] {
  background-color: #eef0ff;
  border-radius: 16px;
  min-width: 32px;
  min-height: 32px;
  max-width: 32px;
  max-height: 32px;
}
QLabel[role="activityTitle"] {
  color: #161b26;
  font-size: 13px;
  font-weight: 600;
}
QLabel[role="activityDetail"] {
  color: #8b95a8;
  font-size: 11px;
}
QLabel[role="activityElapsed"] {
  color: #8b95a8;
  font-size: 10px;
}
QLabel[role="activityPercent"] {
  color: #5b6ee8;
  font-size: 13px;
  font-weight: 700;
  min-width: 36px;
}
QProgressBar {
  border: none;
  border-radius: 999px;
  background-color: #e8ebf0;
  min-height: 8px;
  max-height: 8px;
}
QProgressBar::chunk {
  border-radius: 999px;
  background-color: #5b6ee8;
}
QWidget#LoadingOverlay {
  background-color: rgba(232, 235, 241, 0.55);
}
QFrame[overlayCard="true"] {
  background-color: #ffffff;
  border: 1px solid #d0d6e0;
  border-radius: 12px;
}
QLabel[role="overlayTitle"] {
  color: #161b26;
  font-size: 14px;
  font-weight: 600;
}
QLabel[role="overlaySubtitle"] {
  color: #8b95a8;
  font-size: 12px;
}
"""
