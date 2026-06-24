import Foundation
import Combine

@MainActor
final class ProcessRunner: ObservableObject {
    @Published private(set) var isRunning = false
    @Published var output = ""
    @Published private(set) var exitCode: Int32?
    @Published private(set) var outputFiles: [URL] = []

    private var process: Process?

    var latestOutputFile: URL? {
        outputFiles.last
    }

    func run(_ config: RunnerConfiguration) {
        guard !isRunning else { return }

        output = ""
        outputFiles = []
        exitCode = nil
        isRunning = true

        let process = Process()
        self.process = process
        process.executableURL = config.pythonURL
        process.arguments = config.launchArguments
        process.currentDirectoryURL = config.engineRoot

        var environment = ProcessInfo.processInfo.environment
        let srcPath = config.engineRoot.appendingPathComponent("src").path
        let existingPythonPath = environment["PYTHONPATH"]
        environment["PYTHONPATH"] = existingPythonPath.map { "\(srcPath):\($0)" } ?? srcPath
        environment["ECHOFORM_HOME"] = config.engineRoot.path
        environment["PYTHONUNBUFFERED"] = "1"
        environment["PYTHONIOENCODING"] = "utf-8"
        environment["PATH"] = [
            config.pythonURL.deletingLastPathComponent().path,
            "/opt/homebrew/bin",
            "/usr/local/bin",
            "/usr/bin",
            "/bin",
            "/usr/sbin",
            "/sbin"
        ].joined(separator: ":")
        process.environment = environment

        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = pipe

        pipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            guard !data.isEmpty, let text = String(data: data, encoding: .utf8) else { return }
            Task { @MainActor in
                self?.appendOutput(text)
            }
        }

        process.terminationHandler = { [weak self] terminatedProcess in
            pipe.fileHandleForReading.readabilityHandler = nil
            Task { @MainActor in
                self?.exitCode = terminatedProcess.terminationStatus
                self?.isRunning = false
                self?.process = nil
                self?.appendOutput("\nProcess finished with exit code \(terminatedProcess.terminationStatus).\n")
            }
        }

        do {
            appendOutput("$ \(config.displayCommand)\n\n")
            try process.run()
        } catch {
            appendOutput("Failed to start Echoform: \(error.localizedDescription)\n")
            self.exitCode = -1
            self.isRunning = false
            self.process = nil
        }
    }

    func stop() {
        process?.terminate()
    }

    private func appendOutput(_ text: String) {
        output += text
        collectOutputFiles(from: text)
    }

    private func collectOutputFiles(from text: String) {
        for rawLine in text.components(separatedBy: .newlines) {
            let line = rawLine.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !line.isEmpty else { continue }

            let candidates = [
                pathAfterPrefix("Created:", in: line),
                pathAfterPrefix("Skipping existing output:", in: line),
                pathAfterPrefix("Would render:", in: line),
                bareVideoPath(in: line)
            ].compactMap { $0 }

            for candidate in candidates {
                let url = URL(fileURLWithPath: candidate)
                guard ["mp4", "mov", "m4v"].contains(url.pathExtension.lowercased()) else { continue }
                if !outputFiles.contains(where: { $0.path == url.path }) {
                    outputFiles.append(url)
                }
            }
        }
    }

    private func pathAfterPrefix(_ prefix: String, in line: String) -> String? {
        guard line.hasPrefix(prefix) else { return nil }
        return String(line.dropFirst(prefix.count)).trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private func bareVideoPath(in line: String) -> String? {
        guard line.hasPrefix("/"), line.lowercased().hasSuffix(".mp4") || line.lowercased().hasSuffix(".mov") || line.lowercased().hasSuffix(".m4v") else {
            return nil
        }
        return line
    }
}
