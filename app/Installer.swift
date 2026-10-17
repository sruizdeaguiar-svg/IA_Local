import AppKit
import Foundation

// Offline installer UI. Extraction and copying run as the logged-in user.
final class Installer:NSObject,NSApplicationDelegate {
    var window:NSWindow!;var apps=NSTextField();var data=NSTextField();var status=NSTextField(labelWithString:"");var install=NSButton();var desktop=NSButton(checkboxWithTitle:"Crear acceso en el escritorio / Desktop shortcut",target:nil,action:nil);var finished:URL?
    func applicationDidFinishLaunching(_ notification:Notification){
        let menu=NSMenu();let main=NSMenuItem();menu.addItem(main);let sub=NSMenu();sub.addItem(withTitle:"Salir / Quit",action:#selector(NSApplication.terminate(_:)),keyEquivalent:"q");main.submenu=sub;NSApp.mainMenu=menu
        window=NSWindow(contentRect:NSRect(x:0,y:0,width:700,height:490),styleMask:[.titled,.closable,.miniaturizable],backing:.buffered,defer:false);window.title="Instalar IA Local / Install IA Local"
        let stack=NSStackView();stack.orientation = .vertical;stack.alignment = .leading;stack.spacing=14;stack.translatesAutoresizingMaskIntoConstraints=false;window.contentView!.addSubview(stack)
        NSLayoutConstraint.activate([stack.leadingAnchor.constraint(equalTo:window.contentView!.leadingAnchor,constant:26),stack.trailingAnchor.constraint(equalTo:window.contentView!.trailingAnchor,constant:-26),stack.topAnchor.constraint(equalTo:window.contentView!.topAnchor,constant:26)])
        let title=NSTextField(labelWithString:"IA Local · instalación limpia / clean setup");title.font = .boldSystemFont(ofSize:21);stack.addArrangedSubview(title)
        let intro=NSTextField(wrappingLabelWithString:"Conserva la funcionalidad y empieza sin configuración personal. / Full functionality, no personal configuration.\nApple Silicon · macOS 14 o posterior. Runtime Python incluido. No descarga modelos ni instala servidores.");stack.addArrangedSubview(intro)
        let home=FileManager.default.homeDirectoryForCurrentUser;apps.stringValue=home.appendingPathComponent("Applications").path;data.stringValue=home.appendingPathComponent("Library/Application Support/IA-Local").path
        for (label,field,selector) in [("Carpeta de aplicaciones / Application folder",apps,#selector(chooseApps)),("Carpeta de datos privada / Private data folder",data,#selector(chooseData))]{stack.addArrangedSubview(NSTextField(labelWithString:label));let row=NSStackView();row.orientation = .horizontal;row.spacing=8;field.widthAnchor.constraint(equalToConstant:540).isActive=true;row.addArrangedSubview(field);let choose=NSButton(title:"Elegir…",target:self,action:selector);row.addArrangedSubview(choose);stack.addArrangedSubview(row)}
        desktop.state = .on;stack.addArrangedSubview(desktop)
        let notice=NSTextField(wrappingLabelWithString:"No sustituye instalaciones ni carpetas con datos. Solo una instancia puede usar el puerto 8040. El ayudante GPU y el acceso LAN se activan después, desde la aplicación. / Existing installations are never overwritten; GPU helper and LAN are configured later.");notice.font = .systemFont(ofSize:12);stack.addArrangedSubview(notice)
        install=NSButton(title:"Instalar / Install",target:self,action:#selector(performInstall));install.bezelStyle = .rounded;stack.addArrangedSubview(install);status=NSTextField(wrappingLabelWithString:"Usa las carpetas de tu usuario o elige otras ubicaciones. / Use user defaults or choose other locations.");stack.addArrangedSubview(status)
        window.center();window.makeKeyAndOrderFront(nil);NSApp.activate(ignoringOtherApps:true)
    }
    func choose(_ field:NSTextField){let panel=NSOpenPanel();panel.canChooseDirectories=true;panel.canChooseFiles=false;panel.canCreateDirectories=true;panel.allowsMultipleSelection=false;panel.beginSheetModal(for:window){response in if response == .OK,let url=panel.url{field.stringValue=url.path}}}
    @objc func chooseApps(){choose(apps)}
    @objc func chooseData(){choose(data)}
    @objc func performInstall(){
        install.isEnabled=false;let appFolder=apps.stringValue,dataFolder=data.stringValue,wantsDesktop=desktop.state == .on;status.stringValue="Instalando sin modificar tus servicios… / Installing without changing services…"
        DispatchQueue.global(qos:.userInitiated).async {
            let fm=FileManager.default;let stage=fm.temporaryDirectory.appendingPathComponent("ia-local-installer-"+UUID().uuidString)
            defer{try? fm.removeItem(at:stage)}
            do{
                try fm.createDirectory(at:stage,withIntermediateDirectories:true)
                guard let archive=Bundle.main.url(forResource:"payload",withExtension:"zip") else{throw NSError(domain:"Falta payload.zip",code:1)}
                let unzip=Process();unzip.executableURL=URL(fileURLWithPath:"/usr/bin/ditto");unzip.arguments=["-x","-k",archive.path,stage.path];try unzip.run();unzip.waitUntilExit();if unzip.terminationStatus != 0{throw NSError(domain:"No se pudo extraer el paquete",code:2)}
                let payload=stage.appendingPathComponent("IA Local.app"),task=Process(),pipe=Pipe();task.executableURL=payload.appendingPathComponent("Contents/Resources/python/bin/python3");task.arguments=[payload.appendingPathComponent("Contents/Resources/backend/install_clean.py").path,"--payload-app",payload.path,"--applications",appFolder,"--data",dataFolder]+(wantsDesktop ? ["--desktop"]:[]);task.standardOutput=pipe;task.standardError=Pipe();try task.run();let bytes=pipe.fileHandleForReading.readDataToEndOfFile();task.waitUntilExit()
                let result=(try? JSONSerialization.jsonObject(with:bytes)) as? [String:Any] ?? [:]
                DispatchQueue.main.async {self.install.isEnabled=true;if task.terminationStatus==0{self.finished=URL(fileURLWithPath:(result["app"] as? String) ?? appFolder);self.status.stringValue="Instalación completada / Installation complete.\n"+((result["app"] as? String) ?? "");self.install.title="Mostrar aplicación / Show application";self.install.action=#selector(self.showInstalled)}else{self.status.stringValue=(result["error"] as? String) ?? "La instalación no se completó / Installation failed."}}
            }catch{DispatchQueue.main.async{self.install.isEnabled=true;self.status.stringValue=error.localizedDescription}}
        }
    }
    @objc func showInstalled(){if let url=finished{NSWorkspace.shared.activateFileViewerSelecting([url])}}
    func applicationShouldTerminateAfterLastWindowClosed(_ app:NSApplication)->Bool{true}
}
let delegate=Installer();let app=NSApplication.shared;app.setActivationPolicy(.regular);app.delegate=delegate;app.run()
