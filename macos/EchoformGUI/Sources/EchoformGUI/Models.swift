import Foundation

enum RenderMode: String, CaseIterable, Identifiable {
    case single = "Single Song"
    case batch = "Batch Folder"

    var id: String { rawValue }
}

enum RuntimeKind: String {
    case bundled = "Bundled Runtime"
    case managed = "Managed Runtime"
    case missing = "Missing Runtime"
}

struct RuntimeInfo {
    var kind: RuntimeKind
    var pythonURL: URL?
    var message: String

    var isReady: Bool { pythonURL != nil }
}

struct RunnerConfiguration {
    var engineRoot: URL
    var pythonURL: URL
    var mode: RenderMode
    var configFile: URL?
    var batchFolder: URL?
    var preview: Bool
    var force: Bool
    var dryRun: Bool
    var stopOnError: Bool

    var launchArguments: [String] {
        var args: [String] = []

        switch mode {
        case .single:
            args += ["-u", "-m", "echoform.engine"]
            if let configFile {
                args += ["--config", configFile.path]
            }
            if preview { args.append("--preview") }
        case .batch:
            args += ["-u", "-m", "echoform.queue"]
            if let batchFolder {
                args += ["--folder", batchFolder.path]
            }
            if preview { args.append("--preview") }
            if force { args.append("--force") }
            if dryRun { args.append("--dry-run") }
            if stopOnError { args.append("--stop-on-error") }
        }

        return args
    }

    var displayCommand: String {
        ([pythonURL.path] + launchArguments).map { part in
            part.contains(" ") ? "\"\(part)\"" : part
        }.joined(separator: " ")
    }
}
