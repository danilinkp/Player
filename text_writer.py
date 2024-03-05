import sqlite3

from text_writer_design import Ui_Form
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QWidget


class TextWriter(QWidget, Ui_Form):
    def __init__(self, *args):
        super().__init__()
        self.setupUi(self)
        self.con = sqlite3.connect('music.db')
        self.cur = self.con.cursor()
        self.save_btn.clicked.connect(self.save_text)
        self.update_txt_btn.clicked.connect(self.update_text)
        self.songs_box.activated.connect(self.line_update)

    def save_text(self):
        """ сохраняем наш текст в БД к соответствующей песне """
        if self.songs_box.currentText():
            if self.writer_line.toPlainText():
                self.cur.execute(f"""UPDATE Media
SET text = '{self.writer_line.toPlainText()}'
WHERE Media.title = '{self.songs_box.currentText()}'""")
                self.con.commit()
                self.close()
            else:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Critical)
                msg.setText("Error")
                msg.setInformativeText('Введите текст')
                msg.setWindowTitle("Error")
                msg.exec_()

    def update_text(self):
        """ Обновляем текст в БД """
        valid = QMessageBox.question(
            self, '', "Действительно хотите изменить текст?",
            QMessageBox.Yes, QMessageBox.No)
        if valid == QMessageBox.Yes:
            titles = [i[0] for i in self.cur.execute(f"""SELECT title FROM Media""").fetchall()]
            if self.title_line and self.title_line.text() not in titles:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Critical)
                msg.setText("Error")
                msg.setInformativeText('Такой песни не найдено')
                msg.setWindowTitle("Error")
                msg.exec_()
            else:
                self.cur.execute(f"""UPDATE Media
SET text = '{self.writer_line.toPlainText()}'
WHERE Media.title = '{self.songs_box.currentText()}'""")
                self.con.commit()

    def line_update(self):
        text_of_song = self.cur.execute(
            f"""select text from Media where title = '{self.songs_box.currentText()}'""").fetchall()[
            0][0]
        if text_of_song:
            self.writer_line.setPlainText(text_of_song)
        else:
            self.writer_line.setPlainText('')

    def close_db(self):
        if self.close():
            self.con.close()
