import sys
import sqlite3
from datetime import timedelta

from PyQt5.QtCore import QUrl, QDirIterator, QDir, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QPixmap, QCloseEvent
from PyQt5.QtMultimedia import QMediaPlayer, QMediaPlaylist, QMediaContent
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QAbstractItemView, QWidget, QMessageBox

from PIL import Image
from tinytag import TinyTag

from playlist_input_design import Ui_Form1
from playlists_design import Ui_Form
from player_design import Ui_MainWindow
from text_writer import TextWriter


class Player(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        # создания курсора с помощью которого будем добалять путь файла в БД
        self.con = sqlite3.connect('music.db')
        self.cur = self.con.cursor()

        # открытие формы с добавлением текста
        self.text_writer_form = TextWriter(self)

        # открытие форм связанных с плейлистами
        self.playlist_form = Playlists(self)
        self.playlist_form.signalExit.connect(self.open_playlist_tracks)
        self.input_form = PlaylistNameInput(self)

        self.value = 60
        self.count_mix = 0
        self.count_repeat = 0  # для тогочто отключать повторение треков
        self.count_off_sound = 0  # для тогоч чтобы включать звук

        self.file_act.setShortcut('Ctrl+O')  # конектимся к открытию файлов
        self.file_act.triggered.connect(self.files_load)

        self.folder_act.setShortcut('Ctrl+D')  # конектимся к открытию папки
        self.folder_act.triggered.connect(self.folder_load)

        # Изображение
        self.pixmap = QPixmap('images/standart _img.png')
        self.image_lbl.setPixmap(self.pixmap)

        # настраиваем модель и внешний вид плейлиста
        self.playlist_model = QStandardItemModel(self)
        self.playlistview.setModel(self.playlist_model)  # устанавливаем модель таблицы
        self.playlist_model.setHorizontalHeaderLabels(['Audio Track', 'File Path'])  # Устанавливаем заголовки таблицы
        self.playlistview.hideColumn(1)  # скрываем колонку с путем файла
        self.playlistview.verticalHeader().setVisible(False)  # отключаем нумерацию
        self.playlistview.setSelectionBehavior(QAbstractItemView.SelectRows)  # включаем выделение строк
        self.playlistview.setEditTriggers(QAbstractItemView.NoEditTriggers)  # отключаем редактирование таблицы
        self.playlistview.setSelectionMode(
            QAbstractItemView.SingleSelection)  # Делаем возможным выделять только одну строку
        self.playlistview.resizeColumnsToContents()
        self.playlistview.horizontalHeader().setStretchLastSection(True)

        # инициализация плеера и плэйлиста
        self.player = QMediaPlayer(self)  # инициализируем плеер
        self.playlist = QMediaPlaylist(self.player)  # инициализируем плэйлист
        self.player.setPlaylist(self.playlist)  # устанавливаем плейлист в плеер
        self.player.setVolume(60)  # устанавливаем громкость по умолчанию
        self.volume_slider.setValue(60)
        self.playlist.setPlaybackMode(QMediaPlaylist.Sequential)  # устанавливаем последовательный режим

        # подключаем кнопки пауза, следующий и т.д
        self.play_btn.clicked.connect(self.play_song)
        self.pause_btn.clicked.connect(self.pause_song)
        self.back_btn.clicked.connect(self.previous_song)
        self.next_btn.clicked.connect(self.next_song)
        self.mix_btn.clicked.connect(self.mix_playlist)
        self.repeat_btn.clicked.connect(self.reapeat_song)

        self.playlistview.doubleClicked.connect(self.index_row)
        self.playlist.currentMediaChanged.connect(self.song_changed)

        self.volume_slider.valueChanged[int].connect(self.change_volume)
        self.rewind_slider.sliderMoved.connect(self.set_position)
        self.player.positionChanged.connect(self.position_changed)
        self.player.durationChanged.connect(self.duration_changed)
        self.off_sound_btn.clicked.connect(self.sound_off)
        self.add_text_btn.clicked.connect(self.open_text_writer)
        self.playlist_open_btn.clicked.connect(self.open_playlist)
        self.plus_btn.clicked.connect(self.open_input_form)

        self.text_view.setReadOnly(True)

    def song_changed(self, media):
        """ переключает трек при двойном нажатии по треку """
        if not media.isNull():
            url = media.canonicalUrl()
            path = str(url)[27:-2]
            tag = TinyTag.get(path, image=True)
            artist = tag.artist
            title = tag.title
            album = tag.album
            self.duration = tag.duration
            image = tag.get_image()
            if image:
                with open(file='image.txt', mode='wb') as image_file:
                    image_file.write(image)
                image_jpg = 'image.txt'.replace('.txt', '.jpg')
                with open(image_jpg, 'wb') as image_file:
                    image_file.write(image)
                im = Image.open(image_jpg)
                im2 = im.resize((200, 200))
                im2.save(image_jpg)
                self.pixmap = QPixmap(image_jpg)
                self.image_lbl.setPixmap(self.pixmap)
            if title is not None:
                self.current_track_lbl. \
                    setText(f"{artist} - {title}\n{album}"
                            f"\n{str(timedelta(seconds=self.duration))[2:7]}")
            else:
                self.current_track_lbl.setText(f"{QDir(path).dirName()}\n"
                                               f"{str(timedelta(seconds=self.duration))[2:7]}")
            self.duration_lbl.setText(str(timedelta(seconds=self.duration))[2:7])
            text_of_song = self.cur.execute(
                f"""select text from Media where link_id = (select id from link where path = '{path}')""").fetchall()[
                0][0]
            if text_of_song:
                self.text_view.setPlainText(text_of_song)
            else:
                self.text_view.setPlainText('')

    def index_row(self):
        """ добавляем выбранный трек в playlist на проигрывание при дабл клике """
        for idx in self.playlistview.selectedIndexes():
            self.ind = idx.row()
        self.playlist.setCurrentIndex(self.ind)
        self.player.play()

    def files_load(self):
        """ Загрузка файлов в плейлист и в базу данных """
        paths_in_bd = [i[0] for i in self.con.execute(f"""select path from link""").fetchall()]
        try:
            last_id = int(self.con.execute(f"""select id from Media""").fetchall()[-1][0])
        except IndexError:
            last_id = 0
        except Exception as e:
            print(e)
        files = \
            QFileDialog.getOpenFileNames(self, 'Выбрать музыку', '', 'Музыка (*.mp3);;Музыка (*.wav);;Все файлы (*)')[0]
        for path in files:
            items = []
            tag = TinyTag.get(path, image=True)
            artist = tag.artist
            title = tag.title
            image = tag.get_image()
            if image:
                with open(file='image.txt', mode='wb') as image_file:
                    image_file.write(image)
                image_jpg = 'image.txt'.replace('.txt', '.jpg')
                with open(image_jpg, 'wb') as image_file:
                    image_file.write(image)
                im = Image.open(image_jpg)
                im2 = im.resize((200, 200))
                im2.save(image_jpg)
                self.pixmap = QPixmap(image_jpg)
                self.image_lbl.setPixmap(self.pixmap)
            if title is not None:
                self.text_writer_form.songs_box.addItem(title)
                if path not in paths_in_bd:
                    last_id += 1
                    self.cur.execute(f"""INSERT INTO link(id, path) VALUES({last_id}, '{path}');""")
                    self.cur.execute(
                        f"""INSERT INTO Media(id, link_id, title) VALUES({last_id}, {last_id}, '{title}');""")
                    self.con.commit()
                    items.append(QStandardItem(f"{artist} - {title}"))
                else:
                    items.append(QStandardItem(f"{artist} - {title}"))
            else:
                self.text_writer_form.songs_box.addItem(str(QDir(path).dirName()))
                if path not in paths_in_bd:
                    last_id += 1
                    self.cur.execute(f"""INSERT INTO link(id, path) VALUES('{last_id}', '{path}');""")
                    self.cur.execute(
                        f"""INSERT INTO Media(id, link_id, title) VALUES({last_id}, {last_id}, 
                        '{QDir(path).dirName()}');""")
                    self.con.commit()
                    items.append(QStandardItem(QDir(path).dirName()))
                else:
                    items.append(QStandardItem(QDir(path).dirName()))
            items.append(QStandardItem(path))
            self.playlist_model.appendRow(items)
            self.playlist.addMedia(QMediaContent(QUrl.fromLocalFile(path)))

    def folder_load(self):
        """ Открыть папку с музыкой и поставить изображение в соответствуюшем виджете"""
        paths_in_bd = [i[0] for i in self.con.execute(f"""select path from link""").fetchall()]
        try:
            last_id = int(self.con.execute(f"""select id from Media""").fetchall()[-1][0])
        except IndexError:
            last_id = 0
        except Exception as e:
            print(e)
        folder = QFileDialog.getExistingDirectory(self, 'Open Music Folder', '~')
        if folder is not None:
            it = QDirIterator(folder)
            it.next()
            while it.hasNext():
                if it.fileInfo().isDir() == False and it.filePath() != '.':
                    finfo = it.fileInfo()
                    fpath = it.filePath()
                    if finfo.suffix() in ('mp3', 'ogg', 'wav', 'm4a'):
                        tag = TinyTag.get(str(fpath), image=True)
                        artist = tag.artist
                        title = tag.title
                        self.text_writer_form.songs_box.addItem(title)
                        image = tag.get_image()
                        if image:
                            with open(file='image.txt', mode='wb') as image_file:
                                image_file.write(image)
                            image_jpg = 'image.txt'.replace('.txt', '.jpg')
                            with open(image_jpg, 'wb') as image_file:
                                image_file.write(image)
                            im = Image.open(image_jpg)
                            im2 = im.resize((200, 200))
                            im2.save(image_jpg)
                            self.pixmap = QPixmap(image_jpg)
                            self.image_lbl.setPixmap(self.pixmap)
                        self.playlist.addMedia(QMediaContent(QUrl.fromLocalFile(fpath)))
                        if title is not None:
                            self.text_writer_form.songs_box.addItem(title)
                            if fpath not in paths_in_bd:
                                last_id += 1
                                self.cur.execute(f"""INSERT INTO link(id, path) VALUES({last_id}, '{fpath}');""")
                                self.cur.execute(
                                    f"""INSERT INTO Media(id, link_id, title) VALUES({last_id}, {last_id}, 
                                    '{title}');""")
                                self.con.commit()
                                self.playlist_model.appendRow(
                                    [QStandardItem(f"{artist} - {title}"), QStandardItem(fpath)])
                            else:
                                self.playlist_model.appendRow(
                                    [QStandardItem(f"{artist} - {title}"), QStandardItem(fpath)])
                        else:
                            self.text_writer_form.songs_box.addItem(str(QDir(fpath).dirName()))
                            if fpath not in paths_in_bd:
                                last_id += 1
                                self.cur.execute(f"""INSERT INTO link(id, path) VALUES('{last_id}', '{fpath}');""")
                                self.cur.execute(
                                    f"""INSERT INTO Media(id, link_id, title) VALUES({last_id}, {last_id}, 
                                    '{QDir(fpath).dirName()}');""")
                                self.con.commit()
                                self.playlist_model.appendRow(
                                    [QStandardItem(f"{QStandardItem(QDir(fpath).dirName())}"), QStandardItem(fpath)])
                            else:
                                self.playlist_model.appendRow(
                                    [QStandardItem(f"{QStandardItem(QDir(fpath).dirName())}"), QStandardItem(fpath)])
                it.next()
            if it.fileInfo().isDir() == False and it.filePath() != '.':
                finfo = it.fileInfo()
                fpath = it.filePath()
                if finfo.suffix() in ('mp3', 'ogg', 'wav', 'm4a'):
                    tag = TinyTag.get(fpath, image=True)
                    artist = tag.artist
                    title = tag.title
                    self.text_writer_form.songs_box.addItem(title)
                    image = tag.get_image()
                    if image:
                        with open(file='image.txt', mode='wb') as image_file:
                            image_file.write(image)
                        image_jpg = 'image.txt'.replace('.txt', '.jpg')
                        with open(image_jpg, 'wb') as image_file:
                            image_file.write(image)
                        im = Image.open(image_jpg)
                        im2 = im.resize((200, 200))
                        im2.save(image_jpg)
                        self.pixmap = QPixmap(image_jpg)
                        self.image_lbl.setPixmap(self.pixmap)
                    self.playlist.addMedia(QMediaContent(QUrl.fromLocalFile(it.filePath())))
                    if title is not None:
                        if fpath not in paths_in_bd:
                            last_id += 1
                            self.cur.execute(f"""INSERT INTO link(id, path) VALUES({last_id}, '{fpath}');""")
                            self.cur.execute(
                                f"""INSERT INTO Media(id, link_id, title) VALUES({last_id}, {last_id}, 
                                '{title}');""")
                            self.con.commit()
                            self.playlist_model.appendRow(
                                [QStandardItem(f"{artist} - {title}"), QStandardItem(fpath)])
                        else:
                            self.playlist_model.appendRow(
                                [QStandardItem(f"{artist} - {title}"), QStandardItem(fpath)])
                    else:
                        if fpath not in self.paths_in_bd:
                            self.last_id += 1
                            self.cur.execute(f"""INSERT INTO link(id, path) VALUES('{last_id}', '{fpath}');""")
                            self.cur.execute(
                                f"""INSERT INTO Media(id, link_id, title) VALUES({last_id}, {last_id}, 
                                '{QDir(fpath).dirName()}');""")
                            self.con.commit()
                            self.playlist_model.appendRow(
                                [QStandardItem(f"{QStandardItem(QDir(fpath).dirName())}"), QStandardItem(fpath)])
                        else:
                            self.playlist_model.appendRow(
                                [QStandardItem(f"{QStandardItem(QDir(fpath).dirName())}"), QStandardItem(fpath)])

    def play_song(self):
        """ включаем воспроизведение музыки если она есть, иначе открываем файл"""
        if self.playlist.mediaCount() == 0:
            self.files_load()
        elif self.playlist.mediaCount() != 0:
            self.player.play()

    def pause_song(self):
        """ ставим на паузу """
        self.player.pause()

    def previous_song(self):
        """ переключаемся на предыдущий трек"""
        if self.playlist.mediaCount() == 0:
            self.files_load()
        elif self.playlist.mediaCount() != 0:
            self.playlist.previous()
            row = self.playlist.currentIndex()
            self.playlistview.selectRow(row)

    def next_song(self):
        """ переключаемся на следующий трек"""
        if self.playlist.mediaCount() == 0:
            self.files_load()
        elif self.playlist.mediaCount() != 0:
            self.playlist.next()
            row = self.playlist.currentIndex()
            self.playlistview.selectRow(row)

    def reapeat_song(self):
        """ повторяем текущий трек """
        self.count_repeat += 1
        if self.count_repeat % 2 != 0:
            self.repeat_btn.setStyleSheet("QToolButton{\n"
                                          "    image: url(images/repeat_btn_pressed.png);\n"
                                          "    icon-size: 28px;\n"
                                          "    border: none;\n"
                                          "}\n")
            self.playlist.setPlaybackMode(QMediaPlaylist.CurrentItemInLoop)
        else:
            self.repeat_btn.setStyleSheet("QToolButton{\n"
                                          "    image: url(images/repeat_btn.png);\n"
                                          "    icon-size: 28px;\n"
                                          "    border: none;\n"
                                          "}\n")
            self.playlist.setPlaybackMode(QMediaPlaylist.Sequential)

    def change_volume(self, value):
        """ изменяем громкость музыки"""
        self.player.setVolume(value)
        if value != 0:
            self.value = value

    def sound_off(self):
        """ кнопка выключения звука """
        self.volume_slider.setValue(0)
        self.count_off_sound += 1
        if self.count_off_sound % 2 != 0:
            self.player.setVolume(0)
        else:
            self.volume_slider.setValue(self.value)
            self.player.setVolume(self.value)

    def set_position(self, position):
        """ пермотка трека """
        self.player.setPosition(position)

    def position_changed(self, position):
        """ изменение положения handler у виджета slider """
        self.rewind_slider.setValue(position)
        self.duration_now_lbl.setText(str(timedelta(seconds=position // 1000))[2:7])

    def duration_changed(self, duration):
        """ изменение продолжительности на виджете slider """
        self.rewind_slider.setRange(0, duration)

    def mix_playlist(self):
        """ перемешивает плейлист"""
        self.count_mix += 1
        if self.count_mix % 2 != 0:
            self.mix_btn.setStyleSheet("QToolButton{\n"
                                       "    image: url(images/Mix_btn_pressed.png);\n"
                                       "    icon-size: 28px;\n"
                                       "    border: none;\n"
                                       "}\n")
            self.playlist.setPlaybackMode(QMediaPlaylist.Random)
        else:
            self.mix_btn.setStyleSheet("QToolButton{\n"
                                       "    image: url(images/Mix_btn.png);\n"
                                       "    icon-size: 28px;\n"
                                       "    border: none;\n"
                                       "}\n")
            self.playlist.setPlaybackMode(QMediaPlaylist.Sequential)

    def open_text_writer(self):
        """ открытие формы для записывания текста песни """
        self.text_writer_form.show()

    def open_playlist(self):
        """ открытие формы списка плейлистов"""
        self.playlist_form.your_playlists.clear()
        titles = [str(i[0]) for i in self.cur.execute(f"""SELECT title FROM playlists""").fetchall()]
        for i in titles:
            self.playlist_form.your_playlists.addItem(i)
        self.playlist_form.show()


    def open_input_form(self):
        """открытие формы для ввода названия плейлиста"""
        self.input_form.show()

    @pyqtSlot()
    def open_playlist_tracks(self):
        self.playlist.clear()
        self.playlist_model.clear()
        self.playlistview.setModel(self.playlist_model)  # устанавливаем модель таблицы
        self.playlist_model.setHorizontalHeaderLabels(
            ['Audio Track', 'File Path'])  # Устанавливаем заголовки таблицы
        self.playlistview.hideColumn(1)  # скрываем колонку с путем файла
        self.playlistview.verticalHeader().setVisible(False)  # отключаем нумерацию
        self.playlistview.setSelectionBehavior(QAbstractItemView.SelectRows)  # включаем выделение строк
        self.playlistview.setEditTriggers(QAbstractItemView.NoEditTriggers)  # отключаем редактирование таблицы
        self.playlistview.setSelectionMode(
            QAbstractItemView.SingleSelection)  # Делаем возможным выделять только одну строку
        self.playlistview.horizontalHeader().setStretchLastSection(True)
        self.text_writer_form.songs_box.clear()
        paths_in_bd = [i[0] for i in self.con.execute(f"""select path from link""").fetchall()]
        try:
            last_id = int(self.con.execute(f"""select id from Media""").fetchall()[-1][0])
        except IndexError:
            last_id = 0
        except Exception as e:
            print(e)
        if self.playlist_form.flag:
            for path in self.playlist_form.open_playlist():
                items = []
                tag = TinyTag.get(path, image=True)
                artist = tag.artist
                title = tag.title

                image = tag.get_image()
                if image:
                    with open(file='image.txt', mode='wb') as image_file:
                        image_file.write(image)
                    image_jpg = 'image.txt'.replace('.txt', '.jpg')
                    with open(image_jpg, 'wb') as image_file:
                        image_file.write(image)
                    im = Image.open(image_jpg)
                    im2 = im.resize((200, 200))
                    im2.save(image_jpg)
                    self.pixmap = QPixmap(image_jpg)
                    self.image_lbl.setPixmap(self.pixmap)
                if title is not None:
                    self.text_writer_form.songs_box.addItem(title)
                    if path not in paths_in_bd:
                        last_id += 1
                        self.cur.execute(f"""INSERT INTO link(id, path) VALUES({last_id}, '{path}');""")
                        self.cur.execute(
                            f"""INSERT INTO Media(id, link_id, title) VALUES({last_id}, {last_id}, '{title}');""")
                        self.con.commit()
                        items.append(QStandardItem(f"{artist} - {title}"))
                    else:
                        items.append(QStandardItem(f"{artist} - {title}"))
                else:
                    self.text_writer_form.songs_box.addItem(str(QDir(path).dirName()))
                    if path not in paths_in_bd:
                        last_id += 1
                        self.cur.execute(f"""INSERT INTO link(id, path) VALUES('{last_id}', '{path}');""")
                        self.cur.execute(
                            f"""INSERT INTO Media(id, link_id, title) VALUES({last_id}, {last_id}, 
                            '{QDir(path).dirName()}');""")
                        self.con.commit()
                        items.append(QStandardItem(QDir(path).dirName()))
                    else:
                        items.append(QStandardItem(QDir(path).dirName()))
                items.append(QStandardItem(path))
                self.playlist_model.appendRow(items)
                self.playlist.addMedia(QMediaContent(QUrl.fromLocalFile(path)))
        self.playlist_form.flag = True

    def close_db_player(self):
        """закрытие БД"""
        if self.close():
            self.con.close()


class PlaylistNameInput(QWidget, Ui_Form1):
    def __init__(self, *args):
        super().__init__()
        self.setupUi(self)
        self.playlists_form = Playlists(self)
        self.con = sqlite3.connect('music.db')
        self.cur = self.con.cursor()
        self.ok_btn.clicked.connect(self.make_playlist)

    def make_playlist(self):
        """ создаем плэйлист в базе данных """
        playlists_in_db = [i[0] for i in self.cur.execute(f"""select title from playlists""").fetchall()]
        count = len(playlists_in_db)
        if self.playlist_name_line.text():
            count += 1
            if self.playlist_name_line.text() not in playlists_in_db:
                self.cur.execute(
                f"""INSERT INTO playlists(id, title) VALUES({count}, '{self.playlist_name_line.text()}');""")
                self.playlist_name_line.setText('')
                self.con.commit()
                self.close()
            else:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Critical)
                msg.setText("Error")
                msg.setInformativeText('Такой плейлист уже есть')
                msg.setWindowTitle("Error")
                msg.exec_()
        else:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Error")
            msg.setInformativeText('Введите название')
            msg.setWindowTitle("Error")
            msg.exec_()

    def close_db_player_input(self):
        """закрытие БД"""
        if self.close():
            self.con.close()


class Playlists(QWidget, Ui_Form):
    signalExit = pyqtSignal()

    def __init__(self, *args):
        super().__init__()
        self.setupUi(self)
        self.con = sqlite3.connect('music.db')
        self.cur = self.con.cursor()
        self.flag = False
        titles = [str(i[0]) for i in self.cur.execute(f"""SELECT title FROM playlists""").fetchall()]
        for i in titles:
            self.your_playlists.addItem(i)
        self.update_btn.clicked.connect(self.update_playlists)
        self.files_add_btn.clicked.connect(self.files_add)
        self.open_playlist_btn.clicked.connect(self.open_playlist)
        self.del_playlist_btn.clicked.connect(self.del_playlist)
        self.your_playlists.doubleClicked.connect(self.open_playlist_doubleclick)

    def update_playlists(self):
        """обновляем список плейлистов"""
        self.your_playlists.clear()
        titles = [str(i[0]) for i in self.cur.execute(f"""SELECT title FROM playlists""").fetchall()]
        for i in titles:
            self.your_playlists.addItem(i)

    def files_add(self):
        """ добавляем файлы в выбранный плейлист """
        try:
            name = self.your_playlists.currentItem().text()
            files = \
                QFileDialog.getOpenFileNames(self, 'Выбрать музыку', '',
                                             'Музыка (*.mp3);;Музыка (*.wav);;Все файлы (*)')[0]
            for path in files:
                self.cur.execute(f"""INSERT INTO PlaylistTrack(path) VALUES('{path}')""")
                self.cur.execute(f"""UPDATE PlaylistTrack
SET PlaylistId = (SELECT id FROM playlists WHERE title = '{name}') 
WHERE path = '{path}'""")
                self.con.commit()
        except AttributeError:
            files = []

    def open_playlist(self) -> list:
        """ функция для получения треков и их дальнейшее открытие """
        self.flag = True
        try:
            name = self.your_playlists.currentItem().text()
            self.files = [i[0] for i in self.cur.execute(f"""SELECT path 
FROM PlaylistTrack
WHERE PlaylistId = (SELECT id FROM playlists WHERE title = '{name}')""").fetchall()]
            self.close()
            return self.files
        except AttributeError:
            return []

    def closeEvent(self, event: QCloseEvent) -> None:
        """ при закрытии окна посылаем сигнал в главное окно"""
        self.signalExit.emit()

    def del_playlist(self):
        """ удаление плейлиста из базы данных """
        row = self.your_playlists.currentRow()
        name = self.your_playlists.currentItem().text()
        self.your_playlists.takeItem(row)
        self.cur.execute(
            f"""DELETE FROM PlaylistTrack WHERE PlaylistId = (SELECT id from playlists WHERE title = '{name}')""")
        self.cur.execute(f"""DELETE FROM playlists WHERE title = '{name}'""")
        self.con.commit()

    def open_playlist_doubleclick(self):
        """ открытие плейлиста при двойном нажатии по нему """
        self.open_playlist()

    def close_db_playlist(self):
        """закрытие БД"""
        if self.close():
            self.con.close()


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = Player()
    ex.show()
    sys.excepthook = except_hook
    sys.exit(app.exec())
