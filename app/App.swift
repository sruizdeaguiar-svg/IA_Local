import AppKit
import WebKit
import Foundation

@_silgen_name("ia_authorized_gpu") func authorizeGPU(_ path: UnsafePointer<CChar>, _ value: Int32) -> UnsafeMutablePointer<CChar>?

@_silgen_name("ia_authorized_install") func authorizeInstall(_ path: UnsafePointer<CChar>) -> UnsafeMutablePointer<CChar>?

final class AppDelegate: NSObject, NSApplicationDelegate, WKScriptMessageHandler, WKNavigationDelegate, WKUIDelegate {
    var window: NSWindow!
    var web: WKWebView!
    let root:URL = {if let path=Bundle.main.object(forInfoDictionaryKey:"IALocalDataDirectory") as? String {return URL(fileURLWithPath:path)};return FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/IA-Local")}()
    var controlPort:Int {Bundle.main.object(forInfoDictionaryKey:"IALocalPort") as? Int ?? 8040}
    var uiStamp:Date?;var uiTimer:Timer?
    @objc func reloadPanel(){
        let html=root.appendingPathComponent("index.html")
        let fragment=web?.url?.fragment;var parts=URLComponents(url:html,resolvingAgainstBaseURL:false)!;parts.fragment=fragment
        uiStamp=(try? FileManager.default.attributesOfItem(atPath:html.path)[.modificationDate]) as? Date
        web.loadFileURL(parts.url!,allowingReadAccessTo:html)
    }
    func applicationDidFinishLaunching(_ n: Notification) {
        let menu=NSMenu();let app=NSMenuItem();menu.addItem(app);let submenu=NSMenu();submenu.addItem(withTitle:"Recargar panel",action:#selector(reloadPanel),keyEquivalent:"r");submenu.addItem(withTitle:"Salir de IA Local",action:#selector(NSApplication.terminate(_:)),keyEquivalent:"q");app.submenu=submenu;NSApp.mainMenu=menu
        let configuration=WKWebViewConfiguration();configuration.userContentController.add(self,name:"native")
        web=WKWebView(frame:.zero,configuration:configuration);web.navigationDelegate=self;web.uiDelegate=self
        window=NSWindow(contentRect:NSRect(x:0,y:0,width:1280,height:870),styleMask:[.titled,.closable,.miniaturizable,.resizable],backing:.buffered,defer:false)
        window.title="IA Local";window.minSize=NSSize(width:900,height:650);window.contentView=web;window.center();window.makeKeyAndOrderFront(nil);NSApp.activate(ignoringOtherApps:true)
        reloadPanel();uiTimer=Timer.scheduledTimer(withTimeInterval:2,repeats:true){[weak self] _ in
            guard let self=self else{return};let stamp=(try? FileManager.default.attributesOfItem(atPath:self.root.appendingPathComponent("index.html").path)[.modificationDate]) as? Date
            if stamp != self.uiStamp {self.reloadPanel()}
        }
        DispatchQueue.global(qos:.userInitiated).async {
            let task=Process();let bundled=Bundle.main.bundleURL.appendingPathComponent("Contents/Resources/python/bin/python3");task.executableURL=FileManager.default.fileExists(atPath:bundled.path) ? bundled : FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/Strata-Mac/.venv/bin/python");task.arguments=[self.root.appendingPathComponent("supervisor.py").path,"ensure"]
            var env=ProcessInfo.processInfo.environment;env["IA_LOCAL_HOME"]=self.root.path;env["IA_LOCAL_PYTHON"]=task.executableURL!.path;env["IA_LOCAL_PORT"]=String(self.controlPort);task.environment=env
            let pipe=Pipe();task.standardOutput=pipe;task.standardError=pipe
            do {try task.run();_ = pipe.fileHandleForReading.readDataToEndOfFile();task.waitUntilExit()} catch {}
        }
    }
    func applicationShouldTerminateAfterLastWindowClosed(_ s:NSApplication)->Bool { false }
    func applicationShouldHandleReopen(_ s:NSApplication,hasVisibleWindows:Bool)->Bool {window.makeKeyAndOrderFront(nil);return true}
    func reply(_ id:Int,_ value:Any) {
        guard JSONSerialization.isValidJSONObject(value),let bytes=try? JSONSerialization.data(withJSONObject:value),let json=String(data:bytes,encoding:.utf8) else{return}
        DispatchQueue.main.async {self.web.evaluateJavaScript("window.iaReply(\(id),\(json));",completionHandler:nil)}
    }
    func userContentController(_ c:WKUserContentController,didReceive m:WKScriptMessage) {
        guard m.frameInfo.isMainFrame,m.frameInfo.request.url?.isFileURL==true,let b=m.body as? [String:Any],let id=b["id"] as? Int else{return}
        let command=b["command"] as? String ?? "request"
        if command=="export-certificate" {
            let panel=NSSavePanel();panel.nameFieldStringValue="IA-Local-certificado.pem"
            panel.beginSheetModal(for:window){result in
                if result == .OK,let url=panel.url {do{try FileManager.default.copyItem(at:self.root.appendingPathComponent("lan-cert.pem"),to:url);self.reply(id,["ok":true])}catch{self.reply(id,["error":"No se pudo exportar el certificado."])}}
                else{self.reply(id,["cancelled":true])}
            };return
        }
        if command=="open" {
            let lanInfo=(try? Data(contentsOf:root.appendingPathComponent("lan-info.json"))).flatMap{try? JSONSerialization.jsonObject(with:$0)} as? [String:Any] ?? [:]
            let lanHosts=[lanInfo["hostname"] as? String,lanInfo["address"] as? String].compactMap{$0}
            if let path=b["path"] as? String,path=="logs" {NSWorkspace.shared.open(root.appendingPathComponent("logs"));reply(id,["ok":true]);return}
            if let string=b["url"] as? String,let url=URL(string:string),let host=url.host,
                (url.scheme=="http" && ["127.0.0.1","localhost"].contains(host)) || (url.scheme=="https" && (["github.com","opencode.ai","lmstudio.ai","support.apple.com","assets.exolabs.net"].contains(host) || lanHosts.contains(host))) {
                NSWorkspace.shared.open(url);reply(id,["ok":true]);return
            }
            reply(id,["error":"Destino no permitido."]);return
        }
        if command=="open-opencode" {
            DispatchQueue.global(qos:.userInitiated).async {
                let task=Process();task.executableURL=FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent(".opencode/bin/opencode");task.arguments=["pair"]
                var env=ProcessInfo.processInfo.environment;env["PATH"]="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin";task.environment=env
                let pipe=Pipe();task.standardOutput=pipe;task.standardError=Pipe()
                do {
                    try task.run();let bytes=pipe.fileHandleForReading.readDataToEndOfFile();task.waitUntilExit()
                    let text=String(data:bytes,encoding:.utf8) ?? ""
                    let regex=try NSRegularExpression(pattern:"http://(?:127\\.0\\.0\\.1|localhost):[0-9]+/auth/connect/[^\\s]+")
                    guard let match=regex.firstMatch(in:text,range:NSRange(text.startIndex...,in:text)),let range=Range(match.range,in:text),let url=URL(string:String(text[range])) else {self.reply(id,["error":"OpenCode no entregó un enlace local. Comprueba que esté arrancado."]);return}
                    DispatchQueue.main.async {NSWorkspace.shared.open(url);self.reply(id,["ok":true])}
                } catch {self.reply(id,["error":"No se pudo obtener el enlace local de OpenCode."])}
            };return
        }
        if command=="authorize-ssd" {
            let panel=NSOpenPanel();panel.canChooseDirectories=true;panel.canChooseFiles=false;panel.allowsMultipleSelection=false;panel.directoryURL=URL(fileURLWithPath:"/Volumes/Seguridad/models");panel.message="Selecciona la carpeta de modelos del SSD para autorizar su acceso.";panel.prompt="Autorizar"
            panel.beginSheetModal(for:window){result in
                if result == .OK,let url=panel.url {
                    do {let data=try url.bookmarkData(options:[],includingResourceValuesForKeys:nil,relativeTo:nil);try data.write(to:self.root.appendingPathComponent("models-bookmark"));self.reply(id,["ok":true])} catch {self.reply(id,["error":"No se pudo guardar el acceso al SSD."])}
                } else {self.reply(id,["cancelled":true])}
            };return
        }
        if command=="export" {
            let panel=NSSavePanel();panel.nameFieldStringValue="IA-Local-resultados.json"
            panel.beginSheetModal(for:window){result in
                if result == .OK,let url=panel.url,let value=b["data"],let data=try? JSONSerialization.data(withJSONObject:value,options:[.prettyPrinted,.sortedKeys]) {do{try data.write(to:url,options:.atomic);self.reply(id,["ok":true])}catch{self.reply(id,["error":"No se pudo exportar."])}}
                else{self.reply(id,["cancelled":true])}
            };return
        }
        if command=="install-helper" {
            let helper=Bundle.main.bundleURL.appendingPathComponent("Contents/Helpers/ia-privileged-gpu").path
            DispatchQueue.global(qos:.userInitiated).async {
                guard let raw=helper.withCString({authorizeInstall($0)}) else{self.reply(id,["error":"No se pudo autorizar."]);return}
                let output=String(cString:raw);free(raw)
                if let data=output.data(using:.utf8),let object=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any] {self.reply(id,object)}
                else{self.reply(id,["error":"No se confirmó la instalación."])}
            };return
        }
        guard let path=b["path"] as? String,["/status","/health","/action","/export","/native-request","/native-next","/native-result","/native-complete","/security"].contains(path.components(separatedBy:"?")[0]) else{reply(id,["error":"Ruta no permitida."]);return}
        guard let token=try? String(contentsOf:root.appendingPathComponent("token"),encoding:.utf8) else{reply(id,["error":"Iniciando el supervisor local…"]);return}
        var req=URLRequest(url:URL(string:"http://127.0.0.1:"+String(controlPort)+path)!);req.timeoutInterval=15;req.httpMethod=b["method"] as? String ?? "GET";req.setValue("Bearer "+token,forHTTPHeaderField:"Authorization");req.setValue("application/json",forHTTPHeaderField:"Content-Type")
        if let body=b["body"] {req.httpBody=try? JSONSerialization.data(withJSONObject:body)}
        URLSession.shared.dataTask(with:req){data,response,error in
            if let data=data,let json=try? JSONSerialization.jsonObject(with:data) {self.reply(id,json)}else{self.reply(id,["error":"El supervisor local aún no responde."])}
        }.resume()
    }
    func webView(_ webView:WKWebView,runJavaScriptConfirmPanelWithMessage message:String,initiatedByFrame frame:WKFrameInfo,completionHandler:@escaping(Bool)->Void) {
        let alert=NSAlert();alert.messageText="IA Local";alert.informativeText=message;alert.addButton(withTitle:"Continuar");alert.addButton(withTitle:"Cancelar");alert.beginSheetModal(for:window){result in completionHandler(result == .alertFirstButtonReturn)}
    }
    func webView(_ webView:WKWebView,decidePolicyFor navigationAction:WKNavigationAction,decisionHandler:@escaping(WKNavigationActionPolicy)->Void) {decisionHandler(navigationAction.request.url?.isFileURL==true && navigationAction.request.url?.path==root.appendingPathComponent("index.html").path ? .allow:.cancel)}
}
let delegate=AppDelegate();let app=NSApplication.shared;app.setActivationPolicy(.regular);app.delegate=delegate;app.run()
