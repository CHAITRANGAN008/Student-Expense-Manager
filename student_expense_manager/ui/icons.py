from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap


def _prepare(painter: QPainter, rect: QRectF, color: QColor, width: float = 1.8) -> None:
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    scale = min(rect.width(), rect.height()) / 24.0
    painter.translate(
        rect.x() + (rect.width() - 24 * scale) / 2,
        rect.y() + (rect.height() - 24 * scale) / 2,
    )
    painter.scale(scale, scale)
    pen = QPen(color, width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)


def paint_icon(painter: QPainter, rect: QRectF, kind: str, color: QColor, width: float = 1.8) -> None:
    painter.save()
    _prepare(painter, rect, color, width)
    filled = QColor(color)

    if kind == "dashboard":
        painter.drawRoundedRect(QRectF(3.2, 3.2, 7.6, 7.6), 2.2, 2.2)
        painter.drawRoundedRect(QRectF(13.2, 3.2, 7.6, 4.8), 2.2, 2.2)
        painter.drawRoundedRect(QRectF(13.2, 10.2, 7.6, 10.6), 2.2, 2.2)
        painter.drawRoundedRect(QRectF(3.2, 13.2, 7.6, 7.6), 2.2, 2.2)
    elif kind == "transactions":
        painter.drawLine(QPointF(4, 8), QPointF(19.2, 8))
        painter.drawLine(QPointF(15.6, 4.8), QPointF(19.2, 8))
        painter.drawLine(QPointF(15.6, 11.2), QPointF(19.2, 8))
        painter.drawLine(QPointF(20, 16), QPointF(4.8, 16))
        painter.drawLine(QPointF(8.4, 12.8), QPointF(4.8, 16))
        painter.drawLine(QPointF(8.4, 19.2), QPointF(4.8, 16))
    elif kind == "wallet":
        painter.drawRoundedRect(QRectF(3, 5.6, 18, 13.4), 3, 3)
        path = QPainterPath()
        path.moveTo(3, 9.6)
        path.lineTo(21, 9.6)
        painter.drawPath(path)
        painter.setBrush(filled)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(16.6, 14.2), 1.6, 1.6)
    elif kind == "analytics":
        painter.drawLine(QPointF(4, 20), QPointF(20, 20))
        painter.drawRoundedRect(QRectF(5, 12, 3.4, 5.4), 1.4, 1.4)
        painter.drawRoundedRect(QRectF(10.3, 7.4, 3.4, 10), 1.4, 1.4)
        painter.drawRoundedRect(QRectF(15.6, 3.8, 3.4, 13.6), 1.4, 1.4)
    elif kind == "reports":
        painter.drawRoundedRect(QRectF(4.6, 3, 14.8, 18), 2.4, 2.4)
        painter.drawLine(QPointF(8.2, 8), QPointF(15.8, 8))
        painter.drawLine(QPointF(8.2, 12), QPointF(15.8, 12))
        painter.drawLine(QPointF(8.2, 16), QPointF(13.2, 16))
    elif kind == "settings":
        for y, knob in ((6.4, 9.2), (12, 15), (17.6, 7.6)):
            painter.drawLine(QPointF(4, y), QPointF(20, y))
            painter.setBrush(filled)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(knob, y), 2.1, 2.1)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    elif kind == "plus":
        painter.drawLine(QPointF(12, 5), QPointF(12, 19))
        painter.drawLine(QPointF(5, 12), QPointF(19, 12))
    elif kind == "edit":
        path = QPainterPath()
        path.moveTo(5, 19)
        path.lineTo(6, 14.6)
        path.lineTo(15.8, 4.8)
        path.lineTo(19.2, 8.2)
        path.lineTo(9.4, 18)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawLine(QPointF(14.2, 6.4), QPointF(17.6, 9.8))
    elif kind == "trash":
        painter.drawLine(QPointF(4.5, 6.6), QPointF(19.5, 6.6))
        painter.drawLine(QPointF(9.4, 3.8), QPointF(14.6, 3.8))
        path = QPainterPath()
        path.moveTo(6.4, 6.6)
        path.lineTo(7.5, 20)
        path.lineTo(16.5, 20)
        path.lineTo(17.6, 6.6)
        painter.drawPath(path)
        painter.drawLine(QPointF(10.2, 10), QPointF(10.6, 16.6))
        painter.drawLine(QPointF(13.8, 10), QPointF(13.4, 16.6))
    elif kind == "download":
        painter.drawLine(QPointF(12, 4), QPointF(12, 15.4))
        painter.drawLine(QPointF(7.4, 11), QPointF(12, 15.6))
        painter.drawLine(QPointF(16.6, 11), QPointF(12, 15.6))
        painter.drawLine(QPointF(4.5, 19.5), QPointF(19.5, 19.5))
    elif kind == "upload":
        painter.drawLine(QPointF(12, 16), QPointF(12, 4.6))
        painter.drawLine(QPointF(7.4, 9), QPointF(12, 4.4))
        painter.drawLine(QPointF(16.6, 9), QPointF(12, 4.4))
        painter.drawLine(QPointF(4.5, 19.5), QPointF(19.5, 19.5))
    elif kind == "print":
        painter.drawRoundedRect(QRectF(6.5, 3.5, 11, 5), 1.2, 1.2)
        painter.drawRoundedRect(QRectF(3.5, 8.5, 17, 8), 2, 2)
        painter.drawRoundedRect(QRectF(6.5, 14, 11, 6.5), 1.2, 1.2)
        painter.setBrush(filled)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(17.2, 11.2), 1, 1)
    elif kind == "search":
        painter.drawEllipse(QPointF(10.6, 10.6), 6.2, 6.2)
        painter.drawLine(QPointF(15.4, 15.4), QPointF(20, 20))
    elif kind == "chevron-left":
        painter.drawPolyline([QPointF(14.5, 5.5), QPointF(8, 12), QPointF(14.5, 18.5)])
    elif kind == "chevron-right":
        painter.drawPolyline([QPointF(9.5, 5.5), QPointF(16, 12), QPointF(9.5, 18.5)])
    elif kind == "chevron-down":
        painter.drawPolyline([QPointF(5.5, 9.5), QPointF(12, 16), QPointF(18.5, 9.5)])
    elif kind == "chevron-up":
        painter.drawPolyline([QPointF(5.5, 14.5), QPointF(12, 8), QPointF(18.5, 14.5)])
    elif kind == "close":
        painter.drawLine(QPointF(6.5, 6.5), QPointF(17.5, 17.5))
        painter.drawLine(QPointF(17.5, 6.5), QPointF(6.5, 17.5))
    elif kind == "check":
        painter.drawPolyline([QPointF(5, 12.5), QPointF(10, 17.5), QPointF(19, 6.5)])
    elif kind == "sparkles":
        path = QPainterPath()
        path.moveTo(11, 3.5)
        path.lineTo(12.8, 8.8)
        path.lineTo(18, 10.6)
        path.lineTo(12.8, 12.4)
        path.lineTo(11, 17.7)
        path.lineTo(9.2, 12.4)
        path.lineTo(4, 10.6)
        path.lineTo(9.2, 8.8)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawLine(QPointF(18.4, 15.4), QPointF(18.4, 20.4))
        painter.drawLine(QPointF(15.9, 17.9), QPointF(20.9, 17.9))
    elif kind == "calendar":
        painter.drawRoundedRect(QRectF(3.5, 5, 17, 15.5), 2.4, 2.4)
        painter.drawLine(QPointF(3.5, 9.6), QPointF(20.5, 9.6))
        painter.drawLine(QPointF(8, 3), QPointF(8, 6))
        painter.drawLine(QPointF(16, 3), QPointF(16, 6))
        painter.setBrush(filled)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(8.2, 13.6), 1.1, 1.1)
        painter.drawEllipse(QPointF(12, 13.6), 1.1, 1.1)
        painter.drawEllipse(QPointF(15.8, 13.6), 1.1, 1.1)
        painter.drawEllipse(QPointF(8.2, 17.2), 1.1, 1.1)
        painter.drawEllipse(QPointF(12, 17.2), 1.1, 1.1)
    elif kind == "arrow-up-right":
        painter.drawLine(QPointF(6, 18), QPointF(18, 6))
        painter.drawPolyline([QPointF(9.5, 6), QPointF(18, 6), QPointF(18, 14.5)])
    elif kind == "arrow-down-left":
        painter.drawLine(QPointF(18, 6), QPointF(6, 18))
        painter.drawPolyline([QPointF(14.5, 18), QPointF(6, 18), QPointF(6, 9.5)])
    elif kind == "database":
        painter.drawEllipse(QRectF(4, 3.2, 16, 4.6))
        path = QPainterPath()
        path.moveTo(4, 5.5)
        path.lineTo(4, 18.5)
        path.cubicTo(4, 21.5, 20, 21.5, 20, 18.5)
        path.lineTo(20, 5.5)
        painter.drawPath(path)
        path2 = QPainterPath()
        path2.moveTo(4, 12)
        path2.cubicTo(4, 15, 20, 15, 20, 12)
        painter.drawPath(path2)
    elif kind == "shield":
        path = QPainterPath()
        path.moveTo(12, 2.8)
        path.lineTo(19.6, 5.8)
        path.lineTo(19.6, 11.4)
        path.cubicTo(19.6, 16.6, 15.8, 20, 12, 21.4)
        path.cubicTo(8.2, 20, 4.4, 16.6, 4.4, 11.4)
        path.lineTo(4.4, 5.8)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawPolyline([QPointF(8.6, 12), QPointF(11.2, 14.4), QPointF(15.6, 9.4)])
    elif kind == "info":
        painter.drawEllipse(QRectF(3.5, 3.5, 17, 17))
        painter.drawLine(QPointF(12, 10.6), QPointF(12, 17.4))
        painter.setBrush(filled)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(12, 7.4), 1.15, 1.15)
    elif kind == "sun":
        painter.drawEllipse(QPointF(12, 12), 4.2, 4.2)
        painter.setPen(QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for a, b in ((12, 3), (12, 21), (3, 12), (21, 12), (5.6, 5.6), (18.4, 18.4), (18.4, 5.6), (5.6, 18.4)):
            painter.drawLine(QPointF(12, 12), QPointF(12, 12))
        painter.drawLine(QPointF(12, 2.5), QPointF(12, 4.6))
        painter.drawLine(QPointF(12, 19.4), QPointF(12, 21.5))
        painter.drawLine(QPointF(2.5, 12), QPointF(4.6, 12))
        painter.drawLine(QPointF(19.4, 12), QPointF(21.5, 12))
        painter.drawLine(QPointF(5.3, 5.3), QPointF(6.8, 6.8))
        painter.drawLine(QPointF(17.2, 17.2), QPointF(18.7, 18.7))
        painter.drawLine(QPointF(18.7, 5.3), QPointF(17.2, 6.8))
        painter.drawLine(QPointF(6.8, 17.2), QPointF(5.3, 18.7))
    elif kind == "moon":
        path = QPainterPath()
        path.moveTo(17.8, 15.6)
        path.cubicTo(12.4, 17.2, 7.6, 12.4, 9.3, 7)
        path.cubicTo(4.6, 9.6, 4.8, 16.4, 9.6, 19)
        path.cubicTo(12.8, 20.6, 16.4, 19.2, 17.8, 15.6)
        path.closeSubpath()
        painter.drawPath(path)
    elif kind == "bell":
        path = QPainterPath()
        path.moveTo(5.4, 16.6)
        path.lineTo(6.6, 10.4)
        path.cubicTo(7.2, 6.4, 9.2, 4.4, 12, 4.4)
        path.cubicTo(14.8, 4.4, 16.8, 6.4, 17.4, 10.4)
        path.lineTo(18.6, 16.6)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawLine(QPointF(10.4, 19.4), QPointF(13.6, 19.4))
    elif kind == "filter":
        painter.drawPolyline([QPointF(4, 5.5), QPointF(20, 5.5), QPointF(13.6, 12.6), QPointF(13.6, 19.6), QPointF(10.4, 18), QPointF(10.4, 12.6), QPointF(4, 5.5)])
    elif kind == "trend-up":
        painter.drawPolyline([QPointF(3.5, 17), QPointF(9, 11.4), QPointF(13, 14.6), QPointF(20.5, 6.6)])
        painter.drawPolyline([QPointF(15.6, 6.6), QPointF(20.5, 6.6), QPointF(20.5, 11.5)])
    elif kind == "trend-down":
        painter.drawPolyline([QPointF(3.5, 7), QPointF(9, 12.6), QPointF(13, 9.4), QPointF(20.5, 17.4)])
        painter.drawPolyline([QPointF(15.6, 17.4), QPointF(20.5, 17.4), QPointF(20.5, 12.5)])
    elif kind == "dot":
        painter.setBrush(filled)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(12, 12), 3.2, 3.2)
    elif kind == "bell-ring":
        path = QPainterPath()
        path.moveTo(5, 16.6)
        path.lineTo(6.2, 10.4)
        path.cubicTo(6.8, 6.4, 8.8, 4.4, 11.6, 4.4)
        path.cubicTo(14.4, 4.4, 16.4, 6.4, 17, 10.4)
        path.lineTo(18.2, 16.6)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawLine(QPointF(9.8, 19.4), QPointF(13.4, 19.4))
        painter.drawLine(QPointF(20.4, 4.6), QPointF(20.4, 7.4))
        painter.drawLine(QPointF(18, 6), QPointF(20.8, 6))
        painter.drawLine(QPointF(3.6, 8), QPointF(3.6, 10.8))
        painter.drawLine(QPointF(2.2, 9.4), QPointF(5, 9.4))
    elif kind == "bell-off":
        path = QPainterPath()
        path.moveTo(5, 16.6)
        path.lineTo(6.2, 10.4)
        path.cubicTo(6.8, 6.4, 8.8, 4.4, 11.6, 4.4)
        path.cubicTo(14.4, 4.4, 16.4, 6.4, 17, 10.4)
        path.lineTo(18.2, 16.6)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawLine(QPointF(9.8, 19.4), QPointF(13.4, 19.4))
        painter.drawLine(QPointF(4, 4), QPointF(20, 20))
    elif kind == "check-circle":
        painter.drawEllipse(QRectF(3.2, 3.2, 17.6, 17.6))
        painter.drawPolyline([QPointF(7.6, 12.2), QPointF(10.6, 15.2), QPointF(16.6, 8.8)])
    elif kind == "alert":
        painter.drawPolyline([QPointF(12, 3.4), QPointF(21, 19.4), QPointF(3, 19.4), QPointF(12, 3.4)])
        painter.drawLine(QPointF(12, 9), QPointF(12, 14))
        painter.setBrush(filled)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(12, 16.8), 1, 1)
    elif kind == "clock":
        painter.drawEllipse(QRectF(3.4, 3.4, 17.2, 17.2))
        painter.drawPolyline([QPointF(12, 7.2), QPointF(12, 12.2), QPointF(16, 14.4)])
    elif kind == "repeat":
        painter.drawPolyline([QPointF(4.5, 9), QPointF(17, 9), QPointF(14, 6)])
        painter.drawPolyline([QPointF(19.5, 15), QPointF(7, 15), QPointF(10, 18)])
    elif kind == "list":
        for y in (6, 12, 18):
            painter.setBrush(filled)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(4.5, y), 1.1, 1.1)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(QPointF(8.5, y), QPointF(20, y))
    elif kind == "grid":
        for x in (4, 13.5):
            for y in (4, 13.5):
                painter.drawRoundedRect(QRectF(x, y, 6.5, 6.5), 1.4, 1.4)
    else:
        painter.drawEllipse(QRectF(4, 4, 16, 16))

    painter.restore()


def make_icon(kind: str, color: str = "#A8A2CE", size: int = 18) -> QIcon:
    pm = QPixmap(size * 2, size * 2)
    pm.setDevicePixelRatio(2.0)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    paint_icon(painter, QRectF(0, 0, size, size), kind, QColor(color), width=1.7)
    painter.end()
    return QIcon(pm)
