
from gi.repository import Gio
from gi.repository import Gtk

from kuwo import Config
from kuwo import Node
from kuwo.Player import Player


class App:
    def __init__(self):
        self.app = Gtk.Application.new('org.gtk.kuwo', 0)
        self.app.connect('startup', self.on_app_startup)
        self.app.connect('activate', self.on_app_activate)
        self.app.connect('shutdown', self.on_app_shutdown)

        self.conf = Config.load_conf()
        # TODO: check theme is not None
        self.theme = Config.load_theme(self.conf)

    def run(self, argv):
        self.app.run(argv)

    def on_app_startup(self, app):
        self.window = Gtk.ApplicationWindow.new(app)
        self.window.set_default_size(*self.conf['window-size'])
        self.window.set_title('KuWo Player')
        self.window.props.hide_titlebar_when_maximized = True

        self.window.set_icon(self.theme['app-logo'])

        self.window.connect('check-resize', self.on_main_window_resized)
        app.add_window(self.window)
        self.builder = Gtk.Builder()
        for ui in Config.UI_FILES:
            self.builder.add_from_file(ui)
        self.window.add(self.ui('box_main'))
        self.builder.connect_signals(self)
        
        appmenu = self.builder.get_object('appmenu')
        app.set_app_menu(appmenu)
        
        self.add_simple_action('preferences', 
                self.on_action_preferences_activate)
        self.add_simple_action('about', self.on_action_about_activate)
        self.add_simple_action('quit', self.on_action_quit_activate)

    def on_app_activate(self, app):
        # TODO: init others
        self.init_player()
        self.init_nodes()

        self.window.show_all()

    def on_app_shutdown(self, app):
        Config.dump_conf(self.conf)

    def on_main_window_resized(self, window, event=None):
        self.conf['window-size'] = window.get_size()

    def on_action_preferences_activate(self, action, param):
        print('prefereces action')

    def on_action_about_activate(self, action, param):
        print('about action')

    def on_action_quit_activate(self, action, param):
        print('quit actition')
        self.app.quit()


    # Utilities
    def ui(self, widget, container={}):
        if widget in container:
            return container[widget]

        container[widget] = self.builder.get_object(widget)
        return container[widget]

    def add_simple_action(self, name, callback):
        action = Gio.SimpleAction.new(name, None)
        action.connect('activate', callback)
        self.app.add_action(action)


    # Player
    def init_player(self):
        self.player = Player(self)
        self.ui('image_player_logo').set_from_pixbuf(
                self.theme['anonymous'])

    def on_action_player_previous_activate(self, action):
        pass
    def on_action_player_next_activate(self, action):
        pass
    def on_action_player_play_activate(self, action):
        pass
    def on_action_player_pause_activate(self, action):
        pass
    def on_action_player_repeat_activate(self, action):
        pass
    def on_action_player_repeat_one_activate(self, action):
        pass
    def on_action_player_shuffle_activate(self, action):
        pass


    # side nodes
    def init_nodes(self):
        model = self.ui('liststore_nodes')
        model.clear()
        for node in Config.NODES:
            model.append(node)

    def on_treeview_selection_nodes_changed(self, selection):
        print(selection.get_selected())

        model, tree_iter = selection.get_selected()
        path = model.get_path(tree_iter)
        nid = model[path][1]
        index = path.get_indices()[0]
        print(model, tree_iter, path, type(path), index)
        if index == 0:
            print('path is 0')
            toplist = Node.TopList(self, nid)
            toplist.load()


    # Top List
