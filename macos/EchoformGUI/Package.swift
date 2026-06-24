// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "EchoformGUI",
    platforms: [
        .macOS(.v13)
    ],
    products: [
        .executable(name: "EchoformGUI", targets: ["EchoformGUI"])
    ],
    targets: [
        .executableTarget(
            name: "EchoformGUI",
            resources: [
                .copy("Resources")
            ]
        )
    ]
)
