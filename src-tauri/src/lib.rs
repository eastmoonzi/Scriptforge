use tauri::Manager;

#[tauri::command]
fn get_data_dir(app: tauri::AppHandle) -> String {
    app.path()
        .app_data_dir()
        .unwrap_or_default()
        .to_string_lossy()
        .to_string()
}

#[tauri::command]
fn open_file_native(app: tauri::AppHandle) -> Option<String> {
    use tauri_plugin_dialog::DialogExt;
    let file = app
        .dialog()
        .file()
        .add_filter("Fountain", &["fountain", "txt"])
        .blocking_pick_file();
    match file {
        Some(path) => {
            let p = path.as_path()?;
            std::fs::read_to_string(p).ok()
        }
        None => None,
    }
}

#[tauri::command]
fn save_file_native(
    app: tauri::AppHandle,
    content: String,
    default_name: String,
) -> Option<String> {
    use tauri_plugin_dialog::DialogExt;
    let file = app
        .dialog()
        .file()
        .set_file_name(&default_name)
        .add_filter("Fountain", &["fountain"])
        .blocking_save_file();
    match file {
        Some(path) => {
            let p = path.as_path()?;
            std::fs::write(p, &content).ok()?;
            Some(p.to_string_lossy().to_string())
        }
        None => None,
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .invoke_handler(tauri::generate_handler![
            get_data_dir,
            open_file_native,
            save_file_native,
        ])
        .setup(|app| {
            // Spawn the Python sidecar backend
            let data_dir = app
                .path()
                .app_data_dir()
                .unwrap_or_default()
                .to_string_lossy()
                .to_string();

            // Ensure data directory exists
            let _ = std::fs::create_dir_all(&data_dir);

            use tauri_plugin_shell::ShellExt;
            let sidecar = app
                .shell()
                .sidecar("binaries/scriptforge-server")
                .expect("failed to create sidecar command")
                .args(["--port", "18080", "--data-dir", &data_dir]);

            match sidecar.spawn() {
                Ok((mut rx, child)) => {
                    // Log sidecar output for debugging
                    tauri::async_runtime::spawn(async move {
                        use tauri_plugin_shell::process::CommandEvent;
                        while let Some(event) = rx.recv().await {
                            match event {
                                CommandEvent::Stdout(line) => {
                                    eprintln!("[sidecar stdout] {}", String::from_utf8_lossy(&line));
                                }
                                CommandEvent::Stderr(line) => {
                                    eprintln!("[sidecar stderr] {}", String::from_utf8_lossy(&line));
                                }
                                CommandEvent::Terminated(payload) => {
                                    eprintln!("[sidecar] terminated: {:?}", payload);
                                    break;
                                }
                                _ => {}
                            }
                        }
                    });

                    // Store child handle so we can kill it on exit
                    app.manage(SidecarChild(std::sync::Mutex::new(Some(child))));
                }
                Err(e) => {
                    // In dev mode the sidecar binary may not exist — backend runs separately
                    eprintln!("[sidecar] failed to spawn (ok in dev mode): {e}");
                    app.manage(SidecarChild(std::sync::Mutex::new(None)));
                }
            }

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                // Kill sidecar on window close
                if let Some(state) = window.try_state::<SidecarChild>() {
                    if let Ok(mut guard) = state.0.lock() {
                        if let Some(child) = guard.take() {
                            let _ = child.kill();
                        }
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running Scriptforge");
}

struct SidecarChild(std::sync::Mutex<Option<tauri_plugin_shell::process::CommandChild>>);
