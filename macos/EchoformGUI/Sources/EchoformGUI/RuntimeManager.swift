import Foundation
import Combine

@MainActor
final class RuntimeManager: ObservableObject {
    @Published private(set) var runtimeInfo = RuntimeInfo(kind: .missing, pythonURL: nil, message: "Runtime not checked.")
    @Published private(set) var isPreparing = false
    @Published var setupOutput = ""

    private var process: Process?

    func refresh(engineRoot: URL) {
        runtimeInfo = detectRuntime(engineRoot: engineRoot)
    }

    func prepare(engineRoot: URL) {
        guard !isPreparing else { return }
        setupOutput = ""
        isPreparing = true

        Task {
            await runPreparation(engineRoot: engineRoot)
        }
    }

    func stop() {
        process?.terminate()
    }

    private func runPreparation(engineRoot: URL) async {
        let runtimeRoot = Self.managedRuntimeRoot(engineRoot: engineRoot)
        let venvRoot = runtimeRoot.appendingPathComponent("venv")
        let python = venvRoot.appendingPathComponent("bin/python")
        let pip = venvRoot.appendingPathComponent("bin/pip")
        let requirements = engineRoot.appendingPathComponent("requirements.txt")

        do {
            try FileManager.default.createDirectory(at: runtimeRoot, withIntermediateDirectories: true)

            if !FileManager.default.fileExists(atPath: python.path) {
                append("Creating Echoform runtime...\n")
                try await runProcess(
                    executable: URL(fileURLWithPath: "/usr/bin/env"),
                    arguments: ["python3", "-m", "venv", venvRoot.path],
                    currentDirectory: engineRoot
                )
            } else {
                append("Using existing Echoform runtime: \(venvRoot.path)\n")
            }

            append("Upgrading pip...\n")
            try await runProcess(
                executable: python,
                arguments: ["-m", "pip", "install", "--upgrade", "pip"],
                currentDirectory: engineRoot
            )

            append("Installing renderer dependencies...\n")
            try await runProcess(
                executable: pip,
                arguments: ["install", "-r", requirements.path],
                currentDirectory: engineRoot
            )

            append("Validating Python packages...\n")
            try await runProcess(
                executable: python,
                arguments: ["-c", "import numpy, PIL, tqdm; print('Python dependencies OK')"],
                currentDirectory: engineRoot
            )

            append("Validating FFmpeg...\n")
            try await runProcess(
                executable: URL(fileURLWithPath: "/usr/bin/env"),
                arguments: ["ffmpeg", "-version"],
                currentDirectory: engineRoot
            )

            runtimeInfo = detectRuntime(engineRoot: engineRoot)
            append("Runtime ready.\n")
        } catch {
            runtimeInfo = RuntimeInfo(kind: .missing, pythonURL: nil, message: "Runtime setup failed: \(error.localizedDescription)")
            append("Runtime setup failed: \(error.localizedDescription)\n")
        }

        isPreparing = false
        process = nil
    }

    private func detectRuntime(engineRoot: URL) -> RuntimeInfo {
        if let bundled = Self.bundledPythonURL(), FileManager.default.fileExists(atPath: bundled.path) {
            return RuntimeInfo(kind: .bundled, pythonURL: bundled, message: "Using bundled Python runtime.")
        }

        let managed = Self.managedRuntimeRoot(engineRoot: engineRoot).appendingPathComponent("venv/bin/python")
        if FileManager.default.fileExists(atPath: managed.path) {
            return RuntimeInfo(kind: .managed, pythonURL: managed, message: "Using app-managed Echoform runtime.")
        }

        return RuntimeInfo(kind: .missing, pythonURL: nil, message: "Runtime missing. Click Prepare Runtime to create it.")
    }

    private static func bundledPythonURL() -> URL? {
        guard let resources = Bundle.main.resourceURL else { return nil }
        let candidates = [
            resources.appendingPathComponent("Runtime/bin/python3"),
            resources.appendingPathComponent("Runtime/bin/python")
        ]
        return candidates.first { FileManager.default.fileExists(atPath: $0.path) }
    }

    private static func managedRuntimeRoot(engineRoot: URL) -> URL {
        engineRoot.appendingPathComponent(".echoform-runtime")
    }

    private func runProcess(executable: URL, arguments: [String], currentDirectory: URL) async throws {
        try await withCheckedThrowingContinuation { continuation in
            let process = Process()
            self.process = process
            process.executableURL = executable
            process.arguments = arguments
            process.currentDirectoryURL = currentDirectory

            var environment = ProcessInfo.processInfo.environment
            environment["ECHOFORM_HOME"] = currentDirectory.path
            environment["PATH"] = [
                currentDirectory.appendingPathComponent(".echoform-runtime/venv/bin").path,
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
                Task { @MainActor in self?.append(text) }
            }

            process.terminationHandler = { [weak self] terminated in
                pipe.fileHandleForReading.readabilityHandler = nil
                Task { @MainActor in
                    self?.append("\n$ exit \(terminated.terminationStatus)\n")
                    if terminated.terminationStatus == 0 {
                        continuation.resume()
                    } else {
                        continuation.resume(throwing: RuntimeError.processFailed(terminated.terminationStatus))
                    }
                }
            }

            do {
                append("$ " + ([executable.path] + arguments).map { $0.contains(" ") ? "\"\($0)\"" : $0 }.joined(separator: " ") + "\n")
                try process.run()
            } catch {
                continuation.resume(throwing: error)
            }
        }
    }

    private func append(_ text: String) {
        setupOutput += text
    }
}

enum RuntimeError: LocalizedError {
    case processFailed(Int32)

    var errorDescription: String? {
        switch self {
        case .processFailed(let code):
            return "Process failed with exit code \(code)."
        }
    }
}
