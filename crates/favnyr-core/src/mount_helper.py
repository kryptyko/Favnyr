import sys
import os

def main():
    if len(sys.argv) < 2:
        sys.exit(1)

    uri = sys.argv[1]

    try:
        import gi
        gi.require_version('Gio', '2.0')
        gi.require_version('Gtk', '3.0')
        gi.require_version('GLib', '2.0')
        from gi.repository import Gio, Gtk, GLib
    except Exception as e:
        sys.stderr.write(f"NO_PYGTK: {e}\n")
        sys.exit(2)

    if not Gtk.init_check()[0]:
        sys.stderr.write("NO_DISPLAY\n")
        sys.exit(2)

    f = Gio.File.new_for_uri(uri)

    # 1. Quick check if already mounted
    try:
        m = f.find_enclosing_mount(None)
        root = m.get_root().get_path()
        if root and os.path.exists(root):
            print(root)
            sys.exit(0)
    except Exception:
        pass

    op = Gtk.MountOperation.new(None)

    def on_ask_password(operation, message, default_user, default_domain, flags):
        dialog = Gtk.Dialog(
            title="Favnyr - Autenticación de Red",
            flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT
        )
        dialog.set_default_size(380, -1)
        dialog.set_position(Gtk.WindowPosition.CENTER)
        dialog.add_button("Cancelar", Gtk.ResponseType.CANCEL)
        connect_btn = dialog.add_button("Conectar", Gtk.ResponseType.OK)
        connect_btn.get_style_context().add_class("suggested-action")
        dialog.set_default_response(Gtk.ResponseType.OK)

        content = dialog.get_content_area()
        content.set_spacing(12)
        content.set_margin_top(15)
        content.set_margin_bottom(15)
        content.set_margin_start(20)
        content.set_margin_end(20)

        lbl = Gtk.Label(label=message)
        lbl.set_line_wrap(True)
        lbl.set_xalign(0.0)
        content.pack_start(lbl, False, False, 0)

        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(8)
        content.pack_start(grid, False, False, 0)

        row = 0
        user_entry = None
        if flags & Gio.AskPasswordFlags.NEED_USERNAME:
            u_lbl = Gtk.Label(label="Usuario:", xalign=1.0)
            user_entry = Gtk.Entry()
            user_entry.set_text(default_user or "")
            grid.attach(u_lbl, 0, row, 1, 1)
            grid.attach(user_entry, 1, row, 1, 1)
            row += 1

        domain_entry = None
        if flags & Gio.AskPasswordFlags.NEED_DOMAIN:
            d_lbl = Gtk.Label(label="Dominio:", xalign=1.0)
            domain_entry = Gtk.Entry()
            domain_entry.set_text(default_domain or "")
            grid.attach(d_lbl, 0, row, 1, 1)
            grid.attach(domain_entry, 1, row, 1, 1)
            row += 1

        pass_entry = Gtk.Entry()
        pass_entry.set_visibility(False)
        pass_entry.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, "dialog-password")
        pass_entry.set_activates_default(True)
        p_lbl = Gtk.Label(label="Contraseña:", xalign=1.0)
        grid.attach(p_lbl, 0, row, 1, 1)
        grid.attach(pass_entry, 1, row, 1, 1)
        row += 1

        save_check = None
        if flags & Gio.AskPasswordFlags.SAVING_SUPPORTED:
            save_check = Gtk.CheckButton(label="Recordar para siempre")
            save_check.set_active(True)
            grid.attach(save_check, 1, row, 1, 1)

        dialog.show_all()
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            if user_entry:
                operation.set_username(user_entry.get_text())
            if domain_entry:
                operation.set_domain(domain_entry.get_text())
            operation.set_password(pass_entry.get_text())
            if save_check and save_check.get_active():
                operation.set_password_save(Gio.PasswordSave.PERMANENTLY)
            else:
                operation.set_password_save(Gio.PasswordSave.NEVER)
            operation.reply(Gio.MountOperationResult.HANDLED)
        else:
            operation.reply(Gio.MountOperationResult.ABORTED)

        dialog.destroy()

    def on_ask_question(operation, message, choices):
        dialog = Gtk.Dialog(
            title="Favnyr - Pregunta del Servidor",
            flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT
        )
        dialog.set_default_size(380, -1)
        dialog.set_position(Gtk.WindowPosition.CENTER)

        for i, choice in enumerate(choices):
            btn = dialog.add_button(choice, 100 + i)
            if i == 0:
                btn.get_style_context().add_class("suggested-action")
                dialog.set_default_response(100 + i)

        content = dialog.get_content_area()
        content.set_spacing(12)
        content.set_margin_top(15)
        content.set_margin_bottom(15)
        content.set_margin_start(20)
        content.set_margin_end(20)

        lbl = Gtk.Label(label=message)
        lbl.set_line_wrap(True)
        lbl.set_xalign(0.0)
        content.pack_start(lbl, False, False, 0)

        dialog.show_all()
        response = dialog.run()
        dialog.destroy()

        if response >= 100:
            choice_index = response - 100
            operation.set_choice(choice_index)
            operation.reply(Gio.MountOperationResult.HANDLED)
        else:
            operation.reply(Gio.MountOperationResult.ABORTED)

    op.connect('ask-password', on_ask_password)
    op.connect('ask-question', on_ask_question)

    result_path = [None]
    error_msg = [None]

    def mount_callback(source, res):
        try:
            source.mount_enclosing_volume_finish(res)
            m = source.find_enclosing_mount(None)
            result_path[0] = m.get_root().get_path()
        except Exception as e:
            try:
                m = source.find_enclosing_mount(None)
                result_path[0] = m.get_root().get_path()
            except Exception:
                error_msg[0] = str(e)
        Gtk.main_quit()

    f.mount_enclosing_volume(Gio.MountMountFlags.NONE, op, None, mount_callback)
    Gtk.main()

    if result_path[0]:
        print(result_path[0])
        sys.exit(0)
    else:
        if error_msg[0]:
            sys.stderr.write(error_msg[0] + "\n")
        sys.exit(1)

if __name__ == '__main__':
    main()
