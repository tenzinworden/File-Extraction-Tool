import errno
import multiprocessing
import os
import shutil
import tkinter as tk
from tkinter import NW, LEFT
import sys

import chardet
import dbf
import pyodbc
import pandas as pd
import pyfastcopy  # noqa
import queue
from tkcalendar import Calendar
import datetime

# from os import cpu_count
DB_TYPE = ['mssql', 'foxpro']
fields_foxpro = [
    ['Database Type', 'foxpro'],
    ['Client Media Path(.DBF)', None],
    ['Destination Path', None],
    ['Column', 'mpath'],
    ['File Date (yyyy-mm-dd)', '2000-01-01'],
]
fields_mssql = [
    ['Database Type', 'mssql'],
    ['Server Name', None],
    ['Column', 'mpath'],
    ['Database', None],
    ['User Name', None],
    ['Password', None],
    ['Table Name', None],
]

from tkinter import (
    Tk,
    BOTH,
    Text,
    E,
    W,
    S,
    N,
    END,
    NORMAL,
    DISABLED,
    StringVar,
    messagebox,
)
from tkinter.ttk import Frame, Label, Button, Progressbar, Entry

from multiprocessing import Process, Manager, Queue
from queue import Empty

DELAY1 = 80
DELAY2 = 20

# Queue must be global
queue = Queue()
message = None


def connect_db(db_type, db_server, database_name=None, username=None, pwd=None):
    if db_type == 'mssql':
        connection = pyodbc.connect(
            driver='{SQL Server}',
            host=db_server,
            database=database_name,
            trusted_connection='yes',
            user=username,
            password=pwd,
        )
        # cursor = connection.cursor()
        return connection
    elif db_type == 'foxpro':
        return db_server


def copy_tree(src, dst, symlinks=False, ignore=None):
    if os.path.isdir(src) and not os.path.isdir(
        dst + '/{}'.format(os.path.basename(src)), symlinks, ignore
    ):
        print("Copying directory: {}".format(src))
        shutil.copytree(
            src, dst + '/{}'.format(os.path.basename(src)), symlinks, ignore
        )
    elif os.path.isfile(src) and os.path.isfile('{0}/{1}'.format(dst)):
        print("Copying file: {}".format(src))
        shutil.copy2(src, dst)


def copy_data(paths, column, destination, queue):
    paths['Status'] = ''
    paths['Error'] = ''
    for index, row in paths.iterrows():
        print(row[column])
        try:
            # copy_tree(row[column], destination)
            src = row[column]
            dst = destination
            symlinks = None
            ignore = None
            if os.path.isdir(src):
                if not os.path.isdir(
                    dst + '//{}'.format(os.path.basename(src)), symlinks, ignore
                ):
                    message = "Copying: {}".format(row[column])
                    queue.put(message)
                    print("Copying directory: {}".format(src))
                    shutil.copytree(
                        src,
                        dst + '//{}'.format(os.path.basename(src)),
                        symlinks,
                        ignore,
                    )
                    paths.at[index, 'Status'] = 'Success'
                else:
                    message = "Directory: {} exist".format(src)
                    queue.put(message)
                    print("Directory: {} exist".format(src))
                    paths.at[index, 'Status'] = 'Already Exist'
            elif os.path.isfile(src):
                if not os.path.isfile('{0}//{1}'.format(dst, os.path.basename(src))):
                    message = "Copying: {}".format(row[column])
                    queue.put(message)
                    print("Copying file: {}".format(src))
                    shutil.copy2(src, dst)
                    paths.at[index, 'Status'] = 'Success'
                else:
                    message = "File: {} exist".format(src)
                    queue.put(message)
                    print("File: {} exist".format(src))
                    paths.at[index, 'Status'] = 'Already Exist'
        except OSError as e:
            # If the error was caused because the source wasn't a directory
            # if e.errno == errno.ENOTDIR:
            #     shutil.copy(row[column], destination)
            print('Directory not copied. Error: %s' % e)
            paths.at[index, 'Status'] = 'Failure'
            paths.at[index, 'Error'] = str(e)


def path_copy(path, dest):
    try:
        copy_tree(path, dest)
    except OSError as e:
        # If the error was caused because the source wasn't a directory
        if e.errno == errno.ENOTDIR:
            shutil.copy(path, dest)
        else:
            print('Directory not copied. Error: %s' % e)
            sys.exit(1)


class Copy(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent, name="frame")

        self.parent = parent
        self.initUI()

    def initUI(self):

        self.parent.title("File Transfer")
        self.pack(fill=BOTH, expand=True)
        self.grid_columnconfigure(4, weight=1)
        self.grid_rowconfigure(3, weight=1)
        self.lbl1 = Label(self, text="Database Type:", anchor=NW, justify=LEFT)
        self.lbl1.grid(row=0, column=0, sticky=E, padx=20, pady=0)
        self.radiovar = tk.IntVar()
        self.labelvar = tk.StringVar()
        self.entries = {}
        self.labels = {}
        self.frame = None
        self.copy_button = None
        self.quit_button = None
        self.initial_parent = self.parent
        for index, text in enumerate(["foxpro", "mssql"]):
            button = tk.Radiobutton(
                self,
                text=text,
                variable=self.radiovar,
                value=index,
                command=self.on_choose,
            )
            button.grid(row=0, column=index + 1, padx=0, pady=5, sticky=tk.W)
        self.on_choose()
        self.labelvar = self.radiovar.get()
        self.pbar = None
        row = tk.Frame(self.initial_parent)
        self.message_box = None
        self.rowconfigure(4, pad=2)
        self.destination = None
        # import pdb
        # pdb.set_trace()
        # self.message_box = Label(self, text="Copy", anchor='w')
        # self.message_box.grid(row=4, column=0, sticky=W + E)

    def make_form(self, fields):
        self.destroy_form()
        today = datetime.date.today()

        mindate = datetime.date(year=1950, month=1, day=1)
        maxdate = today + datetime.timedelta(days=5)
        for field in fields:
            print(field)
            row = tk.Frame(self.initial_parent)
            lab = tk.Label(row, width=22, text=field[0] + ": ", anchor='w')
            ent = tk.Entry(row)
            row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
            lab.pack(side=tk.LEFT)
            ent.pack(side=tk.RIGHT, expand=tk.YES, fill=tk.X)
            if field[1]:
                ent.insert(1, field[1])
            self.entries[field[0]] = ent
            self.labels[field[0]] = lab
        row = tk.Frame(self.initial_parent)
        row.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        lab = tk.Label(row, width=50, text="", anchor='w', fg='blue')
        lab.pack(side=tk.LEFT)
        self.labels['Status'] = lab

    def destroy_form(self):
        for i in range(len(self.parent.children) * 100):
            if i == 0 and self.parent.children.get('!frame'):
                self.parent.children.get('!frame').destroy()
            elif self.parent.children.get('!frame{}'.format(i + 1)):
                self.parent.children.get('!frame{}'.format(i + 1)).destroy()
            if i == 0 and self.parent.children.get('!button'):
                self.parent.children.get('!button').destroy()
            elif self.parent.children.get('!button{}'.format(i + 1)):
                self.parent.children.get('!button{}'.format(i + 1)).destroy()

    def on_choose(self):
        self.destroy_form()
        db_type = self.radiovar.get()
        field = fields_foxpro
        if db_type == 1:
            field = fields_mssql
        self.make_form(field)
        self.buttons()

    def on_get_value(self):
        if self.p1.is_alive():
            self.after(DELAY1, self.on_get_value)
            if not queue.empty():
                # self.message_box['text'] = queue.get(0)
                self.labels['Status']['text'] = queue.get(0)
            return
        else:
            try:
                # self.pbar.stop()
                # self.pbar.destroy()
                # self.labels['Status']['text'] = ''
                destination = self.destination or ''
                paths = pd.read_csv("{}//00_asset_mapping_file.csv".format(destination))
                success = paths[paths['Status'] == 'Success'].count()
                failure = paths[paths['Status'] == 'Failure'].count()
                self.labels['Status'][
                    'text'
                ] = 'Successful attempt: {} Failed attempts: {}'.format(
                    success['Status'], failure['Status']
                )
                self.copy_button.config(state=NORMAL)
            except Empty:
                print("queue is empty")

    def buttons(self):
        self.copy_button = tk.Button(
            self.parent,
            text='Copy',
            fg='blue',
            command=(lambda e=self.entries: self.copy_files(e)),
        )
        self.copy_button.pack(side=tk.LEFT, padx=5, pady=5)
        self.quit_button = tk.Button(
            self.parent, text='Quit', command=self.parent.quit, fg='red'
        )
        self.quit_button.pack(side=tk.LEFT, padx=5, pady=5)

    def copy_files(self, entries):
        # self.pbar = Progressbar(self, mode='indeterminate', length=self.parent.winfo_width())
        # self.pbar.grid(sticky=W + E,  padx=25)
        self.copy_button.config(state=DISABLED)
        db_type = entries['Database Type'].get()
        destination = None
        database_name = None
        username = None
        pwd = None
        table = None
        if db_type == 'mssql':
            db_server = entries['Server Name'].get()
            database_name = entries['Database'].get()
            username = entries['User Name'].get()
            pwd = entries['Password'].get()
            table = entries['Table Name'].get()
        else:
            db_server = entries['Client Media Path(.DBF)'].get()
            destination = entries['Destination Path'].get()
            file_date = entries['File Date (yyyy-mm-dd)'].get()
        self.destination = destination
        column = entries['Column'].get()
        self.p1 = Process(
            target=copy_file,
            args=(
                queue,
                db_type,
                db_server,
                destination,
                column,
                file_date,
                database_name,
                username,
                pwd,
                table,
            ),
        )
        self.p1.start()
        # self.pbar.start(DELAY2)
        # self.frame = Frame(self, height=30, width=10)
        # self.frame.grid(row=4, column=1)
        # self.message_box = Label(self, text="Copy", anchor='w')
        # self.message_box.grid(row=4, column=0, sticky=W + E)
        self.after(DELAY1, self.on_get_value)


def copy_file(
    queue,
    db_type,
    db_server,
    destination,
    column=None,
    file_date=None,
    database_name=None,
    username=None,
    pwd=None,
    table=None,
):
    cursor = connect_db(db_type, db_server, database_name, username, pwd)
    if db_type == 'mssql':
        query = "select * from {}".format(table)
        cursor.execute(query)
        # rows = cursor.fetchall()
        paths = pd.read_sql(query, cursor)
        paths[column] = paths[column].str.rstrip()
        list_of_paths = list(paths[column])
        copy_data(list_of_paths, destination, queue)
    elif db_type == 'foxpro':
        file_path = db_server
        try:
            d = dbf.Table(file_path)
            d.open()
            dbf.export(
                d,
                filename="{}//00_asset_mapping_file.csv".format(destination),
                format='csv',
                header=True,
            )
        except dbf.NotFoundError as e:
            print("File: {} not found".format(file_path))
            exit()
        except dbf.DbfError as e:
            print("File: {} not found".format(file_path))
            exit()
        paths = pd.read_csv("{}//00_asset_mapping_file.csv".format(destination))
        paths.columns = d.field_names
        paths[column] = paths[column].str.rstrip()
        if 'ddate' in paths.columns:
            paths = paths[paths['ddate'] >= file_date]
        try:
            salon_info = dbf.Table(
                '{}//saloninfo.dbf'.format(os.path.dirname(file_path))
            )
            salon_info.open()
            dbf.export(salon_info, filename='salon_info.csv', format='csv', header=True)
            with open('salon_info.csv', 'rb') as f:
                result = chardet.detect(f.read())
            salon = pd.read_csv('salon_info.csv', encoding=result['encoding'])
            salon.columns = salon_info.field_names
            paths['Center Name'] = salon.iloc[0].csalonname
            salon.to_csv("salon_info.csv")
            salon_info.close()
        except dbf.DbfError as e:
            print(
                "File: {} not found".format(
                    '{}//saloninfo.dbf'.format(os.path.dirname(file_path))
                )
            )
            paths['Center Name'] = 'Not Found'
        except FileNotFoundError:
            print("File does not exist")
            paths['Center Name'] = 'Not Found'
        d.close()
        copy_data(paths, column, destination, queue)
        paths.to_csv("{}//00_asset_mapping_file.csv".format(destination))


def main():
    root = Tk()
    # root.geometry("400x350+300+300")
    app = Copy(root)
    root.mainloop()


if __name__ == '__main__':
    if sys.platform.startswith('win'):
        multiprocessing.freeze_support()
    main()
