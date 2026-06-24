import SwiftUI
import AppKit
import UniformTypeIdentifiers

struct ContentView: View {
    @StateObject private var runner = ProcessRunner()
    @StateObject private var runtime = RuntimeManager()

    @State private var engineRoot: URL = ContentView.defaultEngineRoot()
    @State private var renderMode: RenderMode = .single
    @State private var configFile: URL?
    @State private var batchFolder: URL?
    @State private var preview = true
    @State private var force = false
    @State private var dryRun = false
    @State private var stopOnError = false

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            header
            Divider()
            runtimePanel
            Divider()
            controls
            Divider()
            commandPreview
            resultPanel
            terminalOutput
        }
        .padding(20)
        .onAppear { runtime.refresh(engineRoot: engineRoot) }
        .onChange(of: engineRoot) { _ in runtime.refresh(engineRoot: engineRoot) }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("Echoform")
                .font(.largeTitle.bold())
            Text("macOS wrapper for the Python visualizer engine")
                .foregroundStyle(.secondary)
        }
    }


    private var runtimePanel: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Runtime")
                        .font(.headline)
                    Text(runtime.runtimeInfo.message)
                        .foregroundColor(runtime.runtimeInfo.isReady ? Color.secondary : Color.red)
                    if let pythonURL = runtime.runtimeInfo.pythonURL {
                        Text(pythonURL.path)
                            .font(.system(.caption, design: .monospaced))
                            .textSelection(.enabled)
                            .foregroundStyle(.secondary)
                    }
                }

                Spacer()

                Button("Check") {
                    runtime.refresh(engineRoot: engineRoot)
                }
                .disabled(runtime.isPreparing || runner.isRunning)

                Button(runtime.isPreparing ? "Stop Setup" : "Prepare Runtime") {
                    if runtime.isPreparing {
                        runtime.stop()
                    } else {
                        runtime.prepare(engineRoot: engineRoot)
                    }
                }
                .disabled(runner.isRunning)
            }

            if runtime.isPreparing || !runtime.setupOutput.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    HStack {
                        Text("Setup Output")
                            .font(.subheadline.bold())
                        Spacer()
                        Button("Copy Setup Output") {
                            copyToClipboard(runtime.setupOutput)
                        }
                        .disabled(runtime.setupOutput.isEmpty)
                    }
                    ScrollView {
                        Text(runtime.setupOutput.isEmpty ? "No setup started." : runtime.setupOutput)
                            .font(.system(.caption, design: .monospaced))
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .textSelection(.enabled)
                    }
                    .frame(maxHeight: 160)
                    .padding(10)
                    .background(.black.opacity(0.06), in: RoundedRectangle(cornerRadius: 8))
                }
            }
        }
    }

    private var controls: some View {
        VStack(alignment: .leading, spacing: 14) {
            pathRow(title: "Engine root", url: engineRoot) {
                chooseFolder { engineRoot = $0 }
            }

            Picker("Render mode", selection: $renderMode) {
                ForEach(RenderMode.allCases) { mode in
                    Text(mode.rawValue).tag(mode)
                }
            }
            .pickerStyle(.segmented)

            if renderMode == .single {
                pathRow(title: "Config file", url: configFile) {
                    chooseFile(allowedExtensions: ["txt", "config"]) { configFile = $0 }
                }
            } else {
                pathRow(title: "Batch folder", url: batchFolder) {
                    chooseFolder { batchFolder = $0 }
                }
            }

            HStack(spacing: 18) {
                Toggle("Preview", isOn: $preview)
                if renderMode == .batch {
                    Toggle("Force", isOn: $force)
                    Toggle("Dry run", isOn: $dryRun)
                    Toggle("Stop on error", isOn: $stopOnError)
                }
                Spacer()
                Button(runner.isRunning ? "Stop" : "Render") {
                    if runner.isRunning {
                        runner.stop()
                    } else if let configuration = currentConfiguration {
                        runner.run(configuration)
                    }
                }
                .keyboardShortcut(.defaultAction)
                .disabled(!canRender && !runner.isRunning)
            }
        }
    }

    private var commandPreview: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("Command")
                .font(.headline)
            HStack(alignment: .top, spacing: 8) {
                Text(currentConfiguration?.displayCommand ?? "Runtime not ready.")
                    .font(.system(.body, design: .monospaced))
                    .textSelection(.enabled)
                    .frame(maxWidth: .infinity, alignment: .leading)

                Button("Copy") {
                    copyToClipboard(currentConfiguration?.displayCommand ?? "")
                }
            }
            .padding(10)
            .background(.quaternary, in: RoundedRectangle(cornerRadius: 8))
        }
    }

    private var resultPanel: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("Result")
                    .font(.headline)
                Spacer()
                if runner.exitCode == 0 {
                    Text("Completed")
                        .foregroundStyle(.green)
                } else if let exitCode = runner.exitCode {
                    Text("Failed: exit code \(exitCode)")
                        .foregroundStyle(.red)
                } else if runner.isRunning {
                    Text("Rendering…")
                        .foregroundStyle(.secondary)
                }
            }

            if let outputFile = runner.latestOutputFile {
                HStack(spacing: 10) {
                    Text(outputFile.path)
                        .lineLimit(1)
                        .truncationMode(.middle)
                        .textSelection(.enabled)
                        .frame(maxWidth: .infinity, alignment: .leading)

                    Button("Copy Path") {
                        copyToClipboard(outputFile.path)
                    }

                    Button("Open Video") {
                        NSWorkspace.shared.open(outputFile)
                    }
                    .disabled(!FileManager.default.fileExists(atPath: outputFile.path))

                    Button("Reveal in Finder") {
                        NSWorkspace.shared.activateFileViewerSelecting([outputFile])
                    }
                    .disabled(!FileManager.default.fileExists(atPath: outputFile.path))
                }
                .padding(10)
                .background(.quaternary, in: RoundedRectangle(cornerRadius: 8))
            } else {
                Text("Rendered video path will appear here when Echoform reports one.")
                    .foregroundStyle(.secondary)
            }
        }
    }

    private var terminalOutput: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text("Output")
                    .font(.headline)
                Spacer()
                Button("Copy Output") {
                    copyToClipboard(runner.output)
                }
                .disabled(runner.output.isEmpty)
            }
            ScrollViewReader { proxy in
                ScrollView {
                    Text(runner.output.isEmpty ? "No render started." : runner.output)
                        .font(.system(.body, design: .monospaced))
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .textSelection(.enabled)
                        .id("bottom")
                }
                .padding(10)
                .background(.black.opacity(0.06), in: RoundedRectangle(cornerRadius: 8))
                .onChange(of: runner.output) { _ in
                    proxy.scrollTo("bottom", anchor: .bottom)
                }
            }
        }
    }

    private var currentConfiguration: RunnerConfiguration? {
        guard let pythonURL = runtime.runtimeInfo.pythonURL else { return nil }
        return RunnerConfiguration(
            engineRoot: engineRoot,
            pythonURL: pythonURL,
            mode: renderMode,
            configFile: configFile,
            batchFolder: batchFolder,
            preview: preview,
            force: force,
            dryRun: dryRun,
            stopOnError: stopOnError
        )
    }

    private var canRender: Bool {
        guard runtime.runtimeInfo.isReady else { return false }
        switch renderMode {
        case .single:
            return FileManager.default.fileExists(atPath: engineRoot.appendingPathComponent("src/echoform/engine.py").path) && configFile != nil
        case .batch:
            return FileManager.default.fileExists(atPath: engineRoot.appendingPathComponent("src/echoform/queue.py").path) && batchFolder != nil
        }
    }

    private func pathRow(title: String, url: URL?, action: @escaping () -> Void) -> some View {
        HStack {
            Text(title)
                .frame(width: 100, alignment: .leading)
            Text(url?.path ?? "Not selected")
                .lineLimit(1)
                .truncationMode(.middle)
                .foregroundStyle(url == nil ? .secondary : .primary)
                .frame(maxWidth: .infinity, alignment: .leading)
            Button("Choose…", action: action)
        }
    }

    private func chooseFolder(_ completion: (URL) -> Void) {
        let panel = NSOpenPanel()
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.allowsMultipleSelection = false
        panel.directoryURL = engineRoot
        if panel.runModal() == .OK, let url = panel.url {
            completion(url)
        }
    }

    private func chooseFile(allowedExtensions: [String], _ completion: (URL) -> Void) {
        let panel = NSOpenPanel()
        panel.canChooseFiles = true
        panel.canChooseDirectories = false
        panel.allowsMultipleSelection = false
        let contentTypes = allowedExtensions.compactMap { UTType(filenameExtension: $0) }
        if !contentTypes.isEmpty {
            panel.allowedContentTypes = contentTypes
        }
        panel.directoryURL = engineRoot
        if panel.runModal() == .OK, let url = panel.url {
            completion(url)
        }
    }

    private func copyToClipboard(_ text: String) {
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(text, forType: .string)
    }

    private static func defaultEngineRoot() -> URL {
        var url = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
        for _ in 0..<5 {
            if FileManager.default.fileExists(atPath: url.appendingPathComponent("src/echoform/engine.py").path) {
                return url
            }
            url.deleteLastPathComponent()
        }
        return URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
    }
}
