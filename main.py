# main.py
import sys
from PyQt5.QtWidgets import QApplication
from auth import AuthDialog
from main_window import MainWindow
from database import Database

if __name__ == "__main__":
    app = QApplication(sys.argv)
    db = Database()

    while True:
        auth_dialog = AuthDialog(db)
        if auth_dialog.exec_() == AuthDialog.Accepted:
            main_window = MainWindow(db, auth_dialog.profile_id, auth_dialog.login_input.text())
            main_window.logout_signal.connect(lambda: None)
            main_window.show()
            app.exec_()
        else:
            break

    db.close()
    sys.exit()