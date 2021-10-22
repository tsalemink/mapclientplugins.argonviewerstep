from PySide2 import QtCore, QtWidgets

from opencmiss.argon.argonlogger import ArgonLogger

from opencmiss.zincwidgets.materialeditorwidget import MaterialEditorWidget
from opencmiss.zincwidgets.regioneditorwidget import RegionEditorWidget
from opencmiss.zincwidgets.sceneviewereditorwidget import SceneviewerEditorWidget
from opencmiss.zincwidgets.sceneviewerwidget import SceneviewerWidget
from opencmiss.zincwidgets.sceneeditorwidget import SceneEditorWidget
from opencmiss.zincwidgets.spectrumeditorwidget import SpectrumEditorWidget
from opencmiss.zincwidgets.tessellationeditorwidget import TessellationEditorWidget
from opencmiss.zincwidgets.timeeditorwidget import TimeEditorWidget
from opencmiss.zincwidgets.fieldlisteditorwidget import FieldListEditorWidget
from opencmiss.zincwidgets.modelsourceseditorwidget import ModelSourcesEditorWidget, ModelSourcesModel

from mapclientplugins.argonviewerstep.ui.ui_argonviewerwidget import Ui_ArgonViewerWidget


class ArgonViewerWidget(QtWidgets.QMainWindow):

    def __init__(self, model, parent=None):
        super(ArgonViewerWidget, self).__init__(parent)
        self._ui = Ui_ArgonViewerWidget()
        self._ui.setupUi(self)

        self._visualisation_view_state_update_pending = False

        # List of possible views
        self._sceneviewerwidget = SceneviewerWidget(self)
        self._visualisation_view_ready = False

        self._view_states = {self._sceneviewerwidget: ''}

        view_list = [self._sceneviewerwidget]

        self._location = None  # The last location/directory used by the application
        self._current_view = None

        self._previous_backup_document = None

        self._sceneviewerwidget.setContext(model.getContext())
        self._model = model

        self._toolbar = self._ui.toolBar

        self._makeConnections()
        self._setupEditors()
        self._registerEditors()
        self._setupViews(view_list)
        self._addDockWidgets()
        self._onDocumentChanged()

        self._callback = None

    def _regionChange(self, changedRegion, treeChange):
        """
        Notifies sceneviewer if affected by tree change i.e. needs new scene.
        :param changedRegion: The top region changed
        :param treeChange: True if structure of tree, or zinc objects reconstructed
        """
        # following may need changing once sceneviewer can look at sub scenes, since resets to root scene:
        if treeChange and (changedRegion is self._model.getDocument().getRootRegion()):
            zincRootRegion = changedRegion.getZincRegion()
            self._sceneviewerwidget.getSceneviewer().setScene(zincRootRegion.getScene())

    def _onDocumentChanged(self):
        document = self._model.getDocument()
        rootRegion = document.getRootRegion()
        rootRegion.connectRegionChange(self._regionChange)
        zincRootRegion = rootRegion.getZincRegion()

        # need to pass new Zinc context to dialogs and widgets using global modules
        zincContext = document.getZincContext()
        self._sceneviewerwidget.setContext(zincContext)
        self.dockWidgetContentsSpectrumEditor.setSpectrums(document.getSpectrums())
        self.dockWidgetContentsTessellationEditor.setTessellations(document.getTessellations())
        self.dockWidgetContentsMaterialEditor.setMaterials(document.getMaterials())
        self.dockWidgetContentsTimeEditor.setZincContext(zincContext)

        model_sources_model = ModelSourcesModel(document, self._model.getSources())
        self.dockWidgetContentsModelSources.setModelSourcesModel(zincRootRegion, model_sources_model)
        # self.dockWidgetContentsModelSources.set

        # need to pass new root region to the following
        self.dockWidgetContentsRegionEditor.setRootRegion(rootRegion)
        self.dockWidgetContentsSceneEditor.setZincRootRegion(zincRootRegion)

        self.dockWidgetContentsFieldEditor.setFieldmodule(zincRootRegion.getFieldmodule())
        self.dockWidgetContentsFieldEditor.setArgonRegion(rootRegion)
        self.dockWidgetContentsFieldEditor.setTimekeeper(zincContext.getTimekeepermodule().getDefaultTimekeeper())

        if self._visualisation_view_ready:
            self._restoreSceneviewerState()
        else:
            self._visualisation_view_state_update_pending = True

    def setZincContext(self, zincContext):
        raise NotImplementedError()

    def setBackupDocument(self, name):
        self._previous_backup_document = name

    def getDependentEditors(self):
        return self._dock_widgets

    def registerDependentEditor(self, editor):
        """
        Add the given editor to the list of dependent editors for
        this view.
        """
        self._dock_widgets.append(editor)

    def _makeConnections(self):
        self._ui.pushButtonDone.clicked.connect(self._doneButtonClicked)
        self._sceneviewerwidget.graphicsInitialized.connect(self._visualisationViewReady)
        # self._model.documentChanged.connect(self._onDocumentChanged)        

    def _addDockWidgets(self):
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.dockWidgetModelSources)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.dockWidgetTimeEditor)
        self.tabifyDockWidget(self.dockWidgetModelSources, self.dockWidgetTessellationEditor)
        self.tabifyDockWidget(self.dockWidgetTessellationEditor, self.dockWidgetSpectrumEditor)
        self.tabifyDockWidget(self.dockWidgetSpectrumEditor, self.dockWidgetSceneEditor)
        self.tabifyDockWidget(self.dockWidgetSceneEditor, self.dockWidgetSceneviewerEditor)
        self.tabifyDockWidget(self.dockWidgetSceneviewerEditor, self.dockWidgetFieldEditor)
        self.tabifyDockWidget(self.dockWidgetFieldEditor, self.dockWidgetRegionEditor)
        self.tabifyDockWidget(self.dockWidgetRegionEditor, self.dockWidgetMaterialEditor)

    def _setupEditors(self):

        self.dockWidgetMaterialEditor = QtWidgets.QDockWidget(self)
        self.dockWidgetMaterialEditor.setWindowTitle('Material Editor')
        self.dockWidgetMaterialEditor.setObjectName("dockWidgetMaterialEditor")
        self.dockWidgetContentsMaterialEditor = MaterialEditorWidget()
        self.dockWidgetContentsMaterialEditor.setObjectName("dockWidgetContentsMaterialEditor")
        self.dockWidgetMaterialEditor.setWidget(self.dockWidgetContentsMaterialEditor)
        self.dockWidgetMaterialEditor.setHidden(True)

        self.dockWidgetModelSources = QtWidgets.QDockWidget(self)
        self.dockWidgetModelSources.setWindowTitle('Model Sources')
        self.dockWidgetModelSources.setObjectName("dockWidgetModelSources")
        self.dockWidgetContentsModelSources = ModelSourcesEditorWidget()
        self.dockWidgetContentsModelSources.setObjectName("dockWidgetContentsModelSources")
        self.dockWidgetContentsModelSources.setEnableAddingModelSources(False)
        self.dockWidgetModelSources.setWidget(self.dockWidgetContentsModelSources)
        self.dockWidgetModelSources.setHidden(False)

        self.dockWidgetRegionEditor = QtWidgets.QDockWidget(self)
        self.dockWidgetRegionEditor.setWindowTitle('Region Editor')
        self.dockWidgetRegionEditor.setObjectName("dockWidgetRegionEditor")
        self.dockWidgetContentsRegionEditor = RegionEditorWidget()
        self.dockWidgetContentsRegionEditor.setObjectName("dockWidgetContentsRegionEditor")
        self.dockWidgetRegionEditor.setWidget(self.dockWidgetContentsRegionEditor)
        self.dockWidgetRegionEditor.setHidden(True)

        self.dockWidgetSceneEditor = QtWidgets.QDockWidget(self)
        self.dockWidgetSceneEditor.setWindowTitle('Scene Editor')
        self.dockWidgetSceneEditor.setObjectName("dockWidgetSceneEditor")
        self.dockWidgetContentsSceneEditor = SceneEditorWidget()
        self.dockWidgetContentsSceneEditor.setObjectName("dockWidgetContentsSceneEditor")
        self.dockWidgetSceneEditor.setWidget(self.dockWidgetContentsSceneEditor)
        self.dockWidgetSceneEditor.setHidden(True)
        
        self.dockWidgetSceneviewerEditor = QtWidgets.QDockWidget(self)
        self.dockWidgetSceneviewerEditor.setWindowTitle('Sceneviewer Editor')
        self.dockWidgetSceneviewerEditor.setObjectName("dockWidgetSceneviewerEditor")
        self.dockWidgetContentsSceneviewerEditor = SceneviewerEditorWidget(self.dockWidgetSceneviewerEditor)
        self.dockWidgetContentsSceneviewerEditor.setObjectName("dockWidgetContentsSceneviewerEditor")
        self.dockWidgetSceneviewerEditor.setWidget(self.dockWidgetContentsSceneviewerEditor)
        self.dockWidgetSceneviewerEditor.setHidden(True)
        self.dockWidgetSceneviewerEditor.visibilityChanged.connect(self.dockWidgetContentsSceneviewerEditor.setEnableUpdates)

        self.dockWidgetSpectrumEditor = QtWidgets.QDockWidget(self)
        self.dockWidgetSpectrumEditor.setWindowTitle('Spectrum Editor')
        self.dockWidgetSpectrumEditor.setObjectName("dockWidgetSpectrumEditor")
        self.dockWidgetContentsSpectrumEditor = SpectrumEditorWidget(self.dockWidgetSpectrumEditor)
        self.dockWidgetContentsSpectrumEditor.setObjectName("dockWidgetContentsSpectrumEditor")
        self.dockWidgetSpectrumEditor.setWidget(self.dockWidgetContentsSpectrumEditor)
        self.dockWidgetSpectrumEditor.setHidden(True)

        self.dockWidgetTessellationEditor = QtWidgets.QDockWidget(self)
        self.dockWidgetTessellationEditor.setWindowTitle('Tessellation Editor')
        self.dockWidgetTessellationEditor.setObjectName("dockWidgetTessellationEditor")
        self.dockWidgetContentsTessellationEditor = TessellationEditorWidget()
        self.dockWidgetContentsTessellationEditor.setObjectName("dockWidgetContentsTessellationEditor")
        self.dockWidgetTessellationEditor.setWidget(self.dockWidgetContentsTessellationEditor)
        self.dockWidgetTessellationEditor.setHidden(True)

        self.dockWidgetTimeEditor = QtWidgets.QDockWidget(self)
        self.dockWidgetTimeEditor.setWindowTitle('Time Editor')
        self.dockWidgetTimeEditor.setObjectName("dockWidgetTimeEditor")
        self.dockWidgetContentsTimeEditor = TimeEditorWidget()
        self.dockWidgetContentsTimeEditor.setObjectName("dockWidgetContentsTimeEditor")
        self.dockWidgetTimeEditor.setWidget(self.dockWidgetContentsTimeEditor)
        self.dockWidgetTimeEditor.setHidden(True)
        
        self.dockWidgetFieldEditor = QtWidgets.QDockWidget(self)
        self.dockWidgetFieldEditor.setWindowTitle('Field Editor')
        self.dockWidgetFieldEditor.setObjectName("dockWidgetFieldEditor")
        self.dockWidgetContentsFieldEditor = FieldListEditorWidget()
        self.dockWidgetContentsFieldEditor.setObjectName("dockWidgetContentsFieldEditor")
        self.dockWidgetFieldEditor.setWidget(self.dockWidgetContentsFieldEditor)
        self.dockWidgetFieldEditor.setHidden(True)

    def _registerEditors(self):
        self._registerEditor(self.dockWidgetMaterialEditor)
        self._registerEditor(self.dockWidgetRegionEditor)
        self._registerEditor(self.dockWidgetSceneEditor)
        self._registerEditor(self.dockWidgetSceneviewerEditor)
        self._registerEditor(self.dockWidgetSpectrumEditor)
        self._registerEditor(self.dockWidgetTessellationEditor)
        self._registerEditor(self.dockWidgetTimeEditor)
        self._registerEditor(self.dockWidgetFieldEditor)
        self._registerEditor(self.dockWidgetModelSources)

        #self._toolbar.addSeparator()

    def _registerEditor(self, editor):
        toggle_action = editor.toggleViewAction()
        toggle_action.triggered.connect(self._view_dock_widget)
        self._toolbar.addAction(toggle_action)
        # view.registerDependentEditor(editor)

    def _view_dock_widget(self, show):
        """
        If we are showing the dock widget we will make it current i.e. make sure it is visible if tabbed.
        """
        if show:
            sender_text = self.sender().text()
            for tab_bar in self.findChildren(QtWidgets.QTabBar):
                for index in range(tab_bar.count()):
                    tab_text = tab_bar.tabText(index)
                    if tab_text == sender_text:
                        tab_bar.setCurrentIndex(index)
                        return

    def _getEditorAction(self, action_name):
        action = None
        actions = self._toolbar.actions()
        existing_actions = [a for a in actions if a.text() == action_name]
        if existing_actions:
            action = existing_actions[0]
        return action

    def _setupViews(self, views):
        zincContext = self._model.getContext()
        for v in views:
            self._ui.viewStackedWidget.addWidget(v)
            v.setContext(zincContext)

    def _visualisationViewReady(self):
        self._visualisation_view_ready = True
        if self._visualisation_view_state_update_pending:
            self._restoreSceneviewerState()

    def _restoreSceneviewerState(self):
        document = self._model.getDocument()
        sceneviewer_state = document.getSceneviewer().serialize()
        self._model.setSceneviewerState(self._sceneviewerwidget.getSceneviewer(), sceneviewer_state)
        self.dockWidgetContentsSceneviewerEditor.setSceneviewer(self._sceneviewerwidget.getSceneviewer())
        self._visualisation_view_state_update_pending = False

    def registerDoneExecution(self, callback):
        self._callback = callback

    def _doneButtonClicked(self):
        with open(self._previous_backup_document, 'w') as f:
            document = self._model.getDocument()
            document.getSceneviewer().updateParameters(self._sceneviewerwidget.getSceneviewer())
            f.write(document.serialize())

        ArgonLogger.closeLogger()
        self._callback()