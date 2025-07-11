from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QItemSelection, QItemSelectionModel, QModelIndex, Qt, QTimer
from PyQt6.QtWidgets import QTableView, QHeaderView

from ...core import (
    ExtendedDialog, ExtendedTableView, Frame, FrameEdit, HBoxLayout, LineEdit, PushButton, Time, TimeEdit, VBoxLayout
)
from ...models import SceningList
from ...utils import qt_silent_call

if TYPE_CHECKING:
    from ...main import MainWindow


__all__ = [
    'SceningListDialog'
]


class SceningListDialog(ExtendedDialog):
    __slots__ = (
        'main', 'scening_list',
        'name_lineedit', 'tableview',
        'start_frame_control', 'end_frame_control',
        'start_time_control', 'end_time_control',
        'label_lineedit',
    )

    def __init__(self, main: MainWindow) -> None:
        super().__init__(main)

        self.main = main
        self.scening_list = SceningList()

        self.setWindowTitle('Scening List View')
        self.setup_ui()

        self.end_frame_control.valueChanged.connect(self.on_end_frame_changed)
        self.end_time_control.valueChanged.connect(self.on_end_time_changed)
        self.label_lineedit.textChanged.connect(self.on_label_changed)
        self.name_lineedit.textChanged.connect(self.on_name_changed)
        self.start_frame_control.valueChanged.connect(self.on_start_frame_changed)
        self.start_time_control.valueChanged.connect(self.on_start_time_changed)
        self.tableview.doubleClicked.connect(self.on_tableview_clicked)
        self.delete_button.clicked.connect(self.on_delete_clicked)

        self.set_qobject_names()

    def setup_ui(self) -> None:
        self.name_lineedit = LineEdit('Scening list name')

        self.tableview = ExtendedTableView()
        self.tableview.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.tableview.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.tableview.setSizeAdjustPolicy(QTableView.SizeAdjustPolicy.AdjustToContents)

        if (header := self.tableview.horizontalHeader()) is not None:
            for col in range(SceningList.COLUMN_COUNT):
                if col == SceningList.LABEL_COLUMN:
                    header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
                else:
                    header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

        self.start_frame_control = FrameEdit()
        self.end_frame_control = FrameEdit()

        self.start_time_control = TimeEdit()
        self.end_time_control = TimeEdit()

        self.label_lineedit = LineEdit(placeholder='Label')

        self.delete_button = PushButton('Delete Selected Scene', enabled=False)
        self.delete_button.setAutoDefault(False)

        VBoxLayout(self, [
            self.name_lineedit, self.tableview
        ]).addLayout(
            HBoxLayout([
                self.start_frame_control,
                self.end_frame_control,
                self.start_time_control,
                self.end_time_control,
                self.label_lineedit,
                self.delete_button
            ])
        )

    def on_current_frame_changed(self, frame: Frame, time: Time) -> None:
        if not self.isVisible():
            return

        selection_model = self.tableview.selectionModel()

        if selection_model is None:
            return

        selection = QItemSelection()

        for i, scene in enumerate(self.scening_list):
            if frame in scene:
                index = self.scening_list.index(i, 0)
                selection.select(index, index)

        selection_model.select(
            selection,
            QItemSelectionModel.SelectionFlag.Rows
            | QItemSelectionModel.SelectionFlag.ClearAndSelect
        )

    def on_current_list_changed(self, scening_list: SceningList) -> None:
        self.scening_list = scening_list

        self.scening_list.rowsMoved.connect(self.on_tableview_rows_moved)

        self.name_lineedit.setText(self.scening_list.name)

        self.tableview.setModel(self.scening_list)
        header = self.tableview.horizontalHeader()

        if header is not None:
            for col in range(SceningList.COLUMN_COUNT):
                if col == SceningList.LABEL_COLUMN:
                    header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
                else:
                    header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

        self.tableview.resizeColumnsToContents()
        selection_model = self.tableview.selectionModel()

        if selection_model is not None:
            selection_model.selectionChanged.connect(self.on_tableview_selection_changed)

        self.label_lineedit.clear()
        self.label_lineedit.clearFocus()
        self.delete_button.setEnabled(False)

    def on_current_output_changed(self, index: int, prev_index: int) -> None:
        self.start_frame_control.setMaximum(self.main.current_output.total_frames - 1)
        self.end_frame_control.setMaximum(self.main.current_output.total_frames - 1)
        self.start_time_control.setMaximum(self.main.current_output.total_time)
        self.end_time_control.setMaximum(self.main.current_output.total_time)

    def on_delete_clicked(self, checked: bool | None = None) -> None:
        selection_model = self.tableview.selectionModel()
        if selection_model is None:
            return
        for model_index in selection_model.selectedRows():
            self.scening_list.remove(model_index.row())
        selection_model.clearSelection()

    def on_end_frame_changed(self, value: Frame | int) -> None:
        selection_model = self.tableview.selectionModel()
        if selection_model is None:
            return

        frame = Frame(value)

        try:
            index = selection_model.selectedRows()[0]
        except IndexError:
            return
        if not index.isValid():
            return
        index = index.siblingAtColumn(SceningList.END_FRAME_COLUMN)
        if not index.isValid():
            return
        self.scening_list.setData(index, frame, Qt.ItemDataRole.UserRole)

    def on_end_time_changed(self, time: Time) -> None:
        selection_model = self.tableview.selectionModel()
        if selection_model is None:
            return
        try:
            index = selection_model.selectedRows()[0]
        except IndexError:
            return
        if not index.isValid():
            return
        index = index.siblingAtColumn(SceningList.END_TIME_COLUMN)
        if not index.isValid():
            return
        self.scening_list.setData(index, time, Qt.ItemDataRole.UserRole)

    def on_label_changed(self, text: str) -> None:
        selection_model = self.tableview.selectionModel()
        if selection_model is None:
            return
        try:
            index = selection_model.selectedRows()[0]
        except IndexError:
            return
        if not index.isValid():
            return
        index = self.scening_list.index(index.row(), SceningList.LABEL_COLUMN)
        if not index.isValid():
            return
        self.scening_list.setData(index, text, Qt.ItemDataRole.UserRole)

    def on_name_changed(self, text: str) -> None:
        assert hasattr(self.main.toolbars, 'scening')

        i = self.main.toolbars.scening.lists.index_of(self.scening_list)
        index = self.main.toolbars.scening.lists.index(i)
        self.main.toolbars.scening.lists.setData(index, text, Qt.ItemDataRole.UserRole)

    def on_start_frame_changed(self, value: Frame | int) -> None:
        frame = Frame(value)
        selection_model = self.tableview.selectionModel()
        if selection_model is None:
            return
        try:
            index = selection_model.selectedRows()[0]
        except IndexError:
            return
        if not index.isValid():
            return
        index = index.siblingAtColumn(SceningList.START_FRAME_COLUMN)
        if not index.isValid():
            return
        self.scening_list.setData(index, frame, Qt.ItemDataRole.UserRole)

    def on_start_time_changed(self, time: Time) -> None:
        selection_model = self.tableview.selectionModel()
        if selection_model is None:
            return
        try:
            index = selection_model.selectedRows()[0]
        except IndexError:
            return
        if not index.isValid():
            return
        index = index.siblingAtColumn(SceningList.START_TIME_COLUMN)
        if not index.isValid():
            return
        self.scening_list.setData(index, time, Qt.ItemDataRole.UserRole)

    def on_tableview_clicked(self, index: QModelIndex) -> None:
        if index.column() in {SceningList.START_FRAME_COLUMN, SceningList.END_FRAME_COLUMN}:
            self.main.switch_frame(Frame(self.scening_list.data(index)))
        if index.column() == SceningList.START_TIME_COLUMN:
            self.main.switch_frame(Frame(self.scening_list.data(index.siblingAtColumn(SceningList.START_FRAME_COLUMN))))
        if index.column() == SceningList.END_TIME_COLUMN:
            self.main.switch_frame(Frame(self.scening_list.data(index.siblingAtColumn(SceningList.END_FRAME_COLUMN))))

    def on_tableview_rows_moved(
        self, parent_index: QModelIndex, start_i: int, end_i: int, dest_index: QModelIndex, dest_i: int
    ) -> None:
        QTimer.singleShot(0, lambda: self.tableview.selectRow(dest_i))

    def on_tableview_selection_changed(self, selected: QItemSelection, deselected: QItemSelection) -> None:
        if len(selected.indexes()) == 0:
            self.delete_button.setEnabled(False)
            self.start_frame_control.setEnabled(False)
            self.end_frame_control.setEnabled(False)
            self.start_time_control.setEnabled(False)
            self.end_time_control.setEnabled(False)
            self.label_lineedit.setEnabled(False)
            return

        index = selected.indexes()[0]
        scene = self.scening_list[index.row()]

        qt_silent_call(self.start_frame_control.setValue, scene.start)
        qt_silent_call(self.end_frame_control.setValue, scene.end)
        qt_silent_call(self.start_time_control.setValue, Time(scene.start))
        qt_silent_call(self.end_time_control.setValue, Time(scene.end))
        qt_silent_call(self.label_lineedit.setText, scene.label)

        self.delete_button.setEnabled(True)
        self.start_frame_control.setEnabled(True)
        self.end_frame_control.setEnabled(True)
        self.start_time_control.setEnabled(True)
        self.end_time_control.setEnabled(True)
        self.label_lineedit.setEnabled(True)
